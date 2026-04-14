"""Tests for cwv_estimator.py"""

from rsb.analyser.cwv_estimator import estimate_cwv
from rsb.analyser.project_scanner import scan_project
from rsb.analyser.route_mapper import map_routes
from rsb.schemas import CWVRisk


def test_cwv_estimate_returns_result(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    routes = map_routes(files)
    cwv = estimate_cwv(files, routes)
    assert cwv.lcp_risk in {CWVRisk.HIGH, CWVRisk.MEDIUM, CWVRisk.LOW, CWVRisk.UNKNOWN}
    assert isinstance(cwv.estimated_js_imports_per_route, float)


def test_cwv_detects_images_without_dims(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    routes = map_routes(files)
    cwv = estimate_cwv(files, routes)
    assert cwv.images_without_dimensions >= 1
