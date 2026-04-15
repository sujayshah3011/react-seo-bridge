"""
server.py - FastAPI prerender server.
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from playwright.async_api import Browser, async_playwright

from rsb.prerender.cache import SnapshotCache
from rsb.prerender.renderer import RenderError, render_page


@dataclass
class AppState:
    browser: Browser
    cache: SnapshotCache
    render_count: int = 0
    cache_hit_count: int = 0
    error_count: int = 0
    start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache_dir = Path(os.environ.get("RSB_CACHE_DIR", "/tmp/rsb-cache"))
    ttl = int(os.environ.get("RSB_CACHE_TTL", str(60 * 60 * 24)))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )
        app.state.rsb = AppState(
            browser=browser,
            cache=SnapshotCache(cache_dir=cache_dir, ttl_seconds=ttl),
            start_time=time.time(),
        )
        yield
        await browser.close()


app = FastAPI(
    title="react-seo-bridge Prerender Server",
    description="Renders React CSR pages for search engine crawlers",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/render", response_class=HTMLResponse)
async def render_endpoint(
    request: Request,
    url: str = Query(..., description="Full URL to render"),
    force: bool = Query(False, description="Skip cache and force a fresh render"),
) -> HTMLResponse:
    state: AppState = request.app.state.rsb

    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    if not force:
        cached_html = await state.cache.get(url)
        if cached_html is not None:
            state.cache_hit_count += 1
            return HTMLResponse(
                content=cached_html,
                headers={"X-RSB-Cache": "HIT", "X-RSB-Prerendered": "true"},
            )

    try:
        state.render_count += 1
        html = await render_page(state.browser, url)
        await state.cache.set(url, html)
    except RenderError as exc:
        state.error_count += 1
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return HTMLResponse(
        content=html,
        headers={"X-RSB-Cache": "MISS", "X-RSB-Prerendered": "true"},
    )


@app.delete("/cache")
async def invalidate_url(request: Request, url: str = Query(..., description="URL to invalidate")) -> JSONResponse:
    state: AppState = request.app.state.rsb
    deleted = await state.cache.invalidate(url)
    return JSONResponse({"url": url, "deleted": deleted})


@app.delete("/cache/all")
async def invalidate_all(request: Request) -> JSONResponse:
    state: AppState = request.app.state.rsb
    deleted_entries = await state.cache.invalidate_all()
    return JSONResponse({"deleted_entries": deleted_entries})


@app.get("/health")
async def health(request: Request) -> JSONResponse:
    state: AppState = request.app.state.rsb
    if not state.browser.is_connected():
        raise HTTPException(status_code=503, detail="Browser not connected")
    return JSONResponse({"status": "ok", "browser": "connected"})


@app.get("/metrics")
async def metrics(request: Request) -> JSONResponse:
    state: AppState = request.app.state.rsb
    total = state.render_count + state.cache_hit_count
    hit_rate = (state.cache_hit_count / total * 100) if total else 0.0
    return JSONResponse(
        {
            "uptime_seconds": round(time.time() - state.start_time),
            "render_count": state.render_count,
            "cache_hit_count": state.cache_hit_count,
            "cache_hit_rate_pct": round(hit_rate, 1),
            "error_count": state.error_count,
            "cache": state.cache.stats(),
        }
    )


def run_server() -> None:
    """Entry point for the rsb-server console script."""

    import uvicorn

    host = os.environ.get("RSB_HOST", "0.0.0.0")
    port = int(os.environ.get("RSB_PORT", "3000"))
    uvicorn.run("rsb.prerender.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()
