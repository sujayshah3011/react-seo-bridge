"""Tests for route_mapper.py"""

from rsb.analyser.project_scanner import scan_project
from rsb.analyser.route_mapper import map_routes


def test_maps_static_routes(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    routes = map_routes(files)
    paths = [route.path for route in routes]
    assert "/" in paths
    assert "/about" in paths


def test_detects_dynamic_routes(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    routes = map_routes(files)
    dynamic_routes = [route for route in routes if route.is_dynamic]
    assert len(dynamic_routes) >= 1
    assert any(":id" in route.path for route in dynamic_routes)


def test_detects_lazy_routes(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    routes = map_routes(files)
    lazy_routes = [route for route in routes if route.is_lazy]
    assert len(lazy_routes) >= 1
