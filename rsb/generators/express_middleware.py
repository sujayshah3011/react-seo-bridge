"""
express_middleware.py - Generates an Express.js middleware snippet.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.prerender.bot_agents import build_js_regex


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_express_middleware(prerender_url: str, output_dir: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = environment.get_template("express_middleware.js.j2")
    output_path = output_dir / "rsb-express-middleware.js"
    output_path.write_text(
        template.render(
            prerender_url=prerender_url.rstrip("/"),
            bot_regex=build_js_regex(),
        ),
        encoding="utf-8",
    )
    return output_path
