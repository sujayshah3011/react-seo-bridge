"""
nginx_config.py - Generates an nginx snippet for dynamic rendering.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.prerender.bot_agents import KNOWN_BOT_UA_SUBSTRINGS


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_nginx_snippet(prerender_url: str, output_dir: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = environment.get_template("nginx_snippet.conf.j2")
    output_path = output_dir / "rsb-nginx-snippet.conf"
    output_path.write_text(
        template.render(
            prerender_url=prerender_url.rstrip("/"),
            bot_strings=KNOWN_BOT_UA_SUBSTRINGS,
        ),
        encoding="utf-8",
    )
    return output_path
