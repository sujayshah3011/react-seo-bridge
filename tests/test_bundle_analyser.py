"""Tests for bundle_analyser.py"""

from rsb.analyser.bundle_analyser import analyse_bundle
from rsb.analyser.project_scanner import scan_project
from rsb.schemas import RenderingType


def test_detects_cra_framework(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    bundle = analyse_bundle(files)
    assert bundle.framework == "cra"


def test_detects_csr_rendering(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    bundle = analyse_bundle(files)
    assert bundle.rendering_type == RenderingType.CSR


def test_detects_react_router_version(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    bundle = analyse_bundle(files)
    assert bundle.react_router_version == "6"


def test_detects_helmet_async(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    bundle = analyse_bundle(files)
    assert bundle.has_helmet_async is True


def test_detects_react_query(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    bundle = analyse_bundle(files)
    assert bundle.has_react_query is True
