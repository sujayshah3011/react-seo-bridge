"""Tests for generator modules."""

from rsb.generators.cloudflare_worker import generate_cloudflare_files
from rsb.generators.robots_gen import generate_robots
from rsb.generators.sitemap_gen import generate_sitemap
from rsb.generators.vercel_config import generate_vercel_files
from rsb.schemas import RouteInfo


def test_vercel_files_generated(tmp_path) -> None:
    files = generate_vercel_files("https://rsb.fly.dev", tmp_path)
    assert "middleware.js" in files
    assert "vercel.json" in files
    middleware = files["middleware.js"].read_text(encoding="utf-8")
    assert "RSB_PRERENDER_URL" in middleware
    assert "googlebot" in middleware.lower()
    assert "gptbot" in middleware.lower()
    assert "next/server" in middleware


def test_cloudflare_files_generated(tmp_path) -> None:
    files = generate_cloudflare_files("https://rsb.fly.dev", tmp_path)
    assert "worker.js" in files
    assert "wrangler.toml" in files
    worker = files["worker.js"].read_text(encoding="utf-8")
    assert "export default" in worker
    assert "addEventListener" not in worker


def test_sitemap_skips_dynamic_routes(tmp_path) -> None:
    routes = [
        RouteInfo(path="/", is_dynamic=False),
        RouteInfo(path="/about", is_dynamic=False),
        RouteInfo(path="/product/:id", is_dynamic=True),
    ]
    sitemap_path = generate_sitemap("https://mysite.com", routes, tmp_path)
    content = sitemap_path.read_text(encoding="utf-8")
    assert "/about" in content
    assert "product/:id" not in content.replace("<!--", "X").replace("-->", "X")


def test_robots_contains_sitemap(tmp_path) -> None:
    robots_path = generate_robots("https://mysite.com", tmp_path)
    content = robots_path.read_text(encoding="utf-8")
    assert "sitemap.xml" in content.lower()
    assert "https://mysite.com" in content
