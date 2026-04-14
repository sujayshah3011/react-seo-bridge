"""Tests for metadata_detector.py"""

from rsb.analyser.metadata_detector import detect_metadata
from rsb.analyser.project_scanner import scan_project
from rsb.schemas import MetaStrategy


def test_detects_helmet_usage(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    findings = detect_metadata(files)
    assert len(findings) > 0
    strategies = {finding.strategy for finding in findings}
    assert MetaStrategy.HELMET_ASYNC in strategies


def test_detects_og_tags(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    findings = detect_metadata(files)
    og_files = [finding for finding in findings if finding.sets_og_tags]
    assert len(og_files) >= 1


def test_detects_dynamic_title(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    findings = detect_metadata(files)
    dynamic_title_files = [finding for finding in findings if finding.title_is_dynamic]
    assert len(dynamic_title_files) >= 1
