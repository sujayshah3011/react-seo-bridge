"""Tests for project_scanner.py"""

import json

import pytest

from rsb.analyser.project_scanner import ProjectScanError, scan_project


def test_scan_valid_cra_project(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    assert files.root == cra_basic_path.resolve()
    assert len(files.all_source_files) > 0
    assert all(f.suffix in {".js", ".jsx", ".ts", ".tsx"} for f in files.all_source_files)


def test_scan_finds_entry_candidates(cra_basic_path) -> None:
    files = scan_project(cra_basic_path)
    router_names = {file_path.name for file_path in files.router_candidates}
    assert "App.jsx" in router_names


def test_scan_excludes_node_modules(tmp_path) -> None:
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({"dependencies": {"react": "^18"}}), encoding="utf-8")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "App.jsx").write_text("export default function App() {}", encoding="utf-8")

    react_dir = tmp_path / "node_modules" / "react"
    react_dir.mkdir(parents=True)
    (react_dir / "index.js").write_text("module.exports = {};", encoding="utf-8")

    files = scan_project(tmp_path)
    assert not any("node_modules" in str(file_path) for file_path in files.all_source_files)


def test_scan_raises_on_missing_path() -> None:
    with pytest.raises(ProjectScanError, match="does not exist"):
        scan_project("/nonexistent/path/that/does/not/exist")


def test_scan_raises_on_non_react_project(tmp_path) -> None:
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({"dependencies": {"express": "^4"}}), encoding="utf-8")
    with pytest.raises(ProjectScanError, match="react"):
        scan_project(tmp_path)
