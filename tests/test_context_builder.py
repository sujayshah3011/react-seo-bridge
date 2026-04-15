"""Tests for context_builder.py"""

from rsb.analyser.bundle_analyser import analyse_bundle
from rsb.analyser.cwv_estimator import estimate_cwv
from rsb.analyser.metadata_detector import detect_metadata
from rsb.analyser.project_scanner import scan_project
from rsb.analyser.route_mapper import map_routes
from rsb.reporters.audit_report import build_audit_result
from rsb.scaffold.context_builder import build_bundle


def test_bundle_is_created(cra_basic_path, tmp_path) -> None:
    project_files = scan_project(cra_basic_path)
    bundle_info = analyse_bundle(project_files)
    routes = map_routes(project_files)
    metadata_findings = detect_metadata(project_files)
    cwv = estimate_cwv(project_files, routes)
    audit_result = build_audit_result(
        project_path=str(cra_basic_path),
        bundle=bundle_info,
        routes=routes,
        metadata_findings=metadata_findings,
        cwv=cwv,
    )

    bundle_paths = build_bundle(
        audit_result=audit_result,
        project_files=project_files,
        output_dir=tmp_path / "scaffold",
    )

    assert len(bundle_paths) >= 1
    content = bundle_paths[0].read_text(encoding="utf-8")
    assert "App Router" in content
    assert "use client" in content
    assert "Server Component" in content
    assert "/about" in content or "/" in content
    assert "App.jsx" in content or "Home.jsx" in content


def test_bundle_contains_client_classification(cra_basic_path, tmp_path) -> None:
    project_files = scan_project(cra_basic_path)
    bundle_info = analyse_bundle(project_files)
    routes = map_routes(project_files)
    metadata_findings = detect_metadata(project_files)
    cwv = estimate_cwv(project_files, routes)
    audit_result = build_audit_result(
        project_path=str(cra_basic_path),
        bundle=bundle_info,
        routes=routes,
        metadata_findings=metadata_findings,
        cwv=cwv,
    )

    bundle_paths = build_bundle(
        audit_result=audit_result,
        project_files=project_files,
        output_dir=tmp_path / "scaffold",
    )

    content = bundle_paths[0].read_text(encoding="utf-8")
    assert "CLIENT" in content
