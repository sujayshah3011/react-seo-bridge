"""
cloudflare_worker.py - Generates Cloudflare Worker routing files.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.prerender.bot_agents import build_js_regex


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_cloudflare_files(
    prerender_url: str,
    output_dir: Path,
    worker_name: str = "rsb-prerender-router",
) -> dict[str, Path]:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "prerender_url": prerender_url.rstrip("/"),
        "bot_regex": build_js_regex(),
        "worker_name": worker_name,
    }
    written: dict[str, Path] = {}

    for template_name, output_name in (
        ("cloudflare_worker.js.j2", "worker.js"),
        ("wrangler_toml.j2", "wrangler.toml"),
    ):
        template = environment.get_template(template_name)
        output_path = output_dir / output_name
        output_path.write_text(template.render(**context), encoding="utf-8")
        written[output_name] = output_path

    return written
