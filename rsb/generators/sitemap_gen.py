"""
sitemap_gen.py - Generates sitemap.xml from audit routes.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.schemas import RouteInfo


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


def generate_sitemap(base_url: str, routes: list[RouteInfo], output_dir: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    static_routes = [route for route in routes if not route.is_dynamic]
    dynamic_routes = [route for route in routes if route.is_dynamic]
    template = environment.get_template("sitemap.xml.j2")

    output_path = output_dir / "sitemap.xml"
    output_path.write_text(
        template.render(
            base_url=base_url.rstrip("/"),
            static_routes=static_routes,
            dynamic_routes=dynamic_routes,
        ),
        encoding="utf-8",
    )
    return output_path
