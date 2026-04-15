"""
robots_gen.py - Generates robots.txt with a sitemap reference.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_robots(base_url: str, output_dir: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = environment.get_template("robots.txt.j2")
    output_path = output_dir / "robots.txt"
    output_path.write_text(
        template.render(base_url=base_url.rstrip("/")),
        encoding="utf-8",
    )
    return output_path
