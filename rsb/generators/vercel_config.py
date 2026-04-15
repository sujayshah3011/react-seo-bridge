"""
vercel_config.py - Generates Vercel middleware.js and vercel.json.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.prerender.bot_agents import build_js_regex


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_vercel_files(prerender_url: str, output_dir: Path) -> dict[str, Path]:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "prerender_url": prerender_url.rstrip("/"),
        "bot_regex": build_js_regex(),
    }
    written: dict[str, Path] = {}

    for template_name, output_name in (
        ("vercel_middleware.js.j2", "middleware.js"),
        ("vercel_json.j2", "vercel.json"),
    ):
        template = environment.get_template(template_name)
        output_path = output_dir / output_name
        output_path.write_text(template.render(**context), encoding="utf-8")
        written[output_name] = output_path

    return written
