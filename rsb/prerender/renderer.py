"""
renderer.py - Playwright-based page renderer.
"""

from __future__ import annotations

import re

from playwright.async_api import Browser, Page, Route


_STRIP_SCRIPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"<script[^>]+(?:google-analytics|gtag|googletagmanager)[^>]*>.*?</script>",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"<script[^>]+(?:segment\.com|mixpanel|hotjar|clarity\.ms)[^>]*>.*?</script>",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(
        r"<script[^>]+(?:intercom|drift|crisp)[^>]*>.*?</script>",
        re.DOTALL | re.IGNORECASE,
    ),
    re.compile(r"//# sourceMappingURL=\S+", re.MULTILINE),
]
_BLOCKED_RESOURCE_TYPES = {"image", "font", "media"}
_BLOCKED_URL_SUBSTRINGS = (
    "google-analytics",
    "googletagmanager",
    "gtag",
    "segment.com",
    "mixpanel",
    "hotjar",
    "clarity.ms",
    "intercom",
    "drift",
    "crisp",
)

NAVIGATION_TIMEOUT = 15_000
NETWORK_IDLE_TIMEOUT = 5_000


class RenderError(Exception):
    """Raised when a page cannot be rendered."""


async def render_page(browser: Browser, url: str) -> str:
    """Render a URL to crawler-friendly HTML using an existing browser instance."""

    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (compatible; RSBPrerender/1.0; "
            "+https://github.com/sujayshah3011/react-seo-bridge)"
        ),
        java_script_enabled=True,
        bypass_csp=False,
    )
    page: Page = await context.new_page()

    try:
        await page.route("**/*", _route_request)

        response = await page.goto(url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT)
        if response is None:
            raise RenderError(f"No response received for {url}")
        if response.status >= 400:
            raise RenderError(f"HTTP {response.status} for {url}")

        try:
            await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        except Exception:
            pass

        html = await page.content()
        return _clean_html(html)
    except RenderError:
        raise
    except Exception as exc:
        raise RenderError(f"Render failed for {url}: {exc}") from exc
    finally:
        await context.close()


async def _route_request(route: Route) -> None:
    request = route.request
    request_url = request.url.lower()
    if request.resource_type in _BLOCKED_RESOURCE_TYPES or any(
        token in request_url for token in _BLOCKED_URL_SUBSTRINGS
    ):
        await route.abort()
        return
    await route.continue_()


def _clean_html(html: str) -> str:
    for pattern in _STRIP_SCRIPT_PATTERNS:
        html = pattern.sub("", html)

    if "<head>" in html:
        return html.replace("<head>", "<head>\n<!-- X-RSB-Prerendered: true -->", 1)
    return f"<!-- X-RSB-Prerendered: true -->\n{html}"
