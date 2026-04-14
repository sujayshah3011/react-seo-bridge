"""
project_scanner.py - Validates a React project and discovers all source files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


EXCLUDE_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".next",
    "coverage",
    "__tests__",
    ".cache",
    "public",
    "out",
}

JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


@dataclass
class ProjectFiles:
    root: Path
    package_json: Path
    all_source_files: list[Path] = field(default_factory=list)
    entry_candidates: list[Path] = field(default_factory=list)
    router_candidates: list[Path] = field(default_factory=list)
    config_files: list[Path] = field(default_factory=list)


class ProjectScanError(Exception):
    """Raised when a project cannot be scanned as a supported React app."""


def scan_project(project_path: str | Path) -> ProjectFiles:
    """
    Scan a React project directory and return organised file lists.

    Raises ProjectScanError with a descriptive message if:
    - The path does not exist
    - No package.json is found
    - package.json does not list react as a dependency
    """

    root = Path(project_path).resolve()

    if not root.exists():
        raise ProjectScanError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise ProjectScanError(f"Path is not a directory: {root}")

    pkg_json_path = root / "package.json"
    if not pkg_json_path.exists():
        raise ProjectScanError(
            f"No package.json found in {root}. Is this the root of a React project?"
        )

    try:
        pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectScanError(f"package.json is not valid JSON: {exc}") from exc

    all_deps: dict[str, str] = {}
    all_deps.update(pkg_data.get("dependencies", {}))
    all_deps.update(pkg_data.get("devDependencies", {}))

    if "react" not in all_deps:
        raise ProjectScanError(
            "package.json does not list 'react' as a dependency. "
            "This tool only supports React projects."
        )

    src_dir = root / "src"
    search_root = src_dir if src_dir.exists() else root

    all_source_files: list[Path] = []
    for file_path in search_root.rglob("*"):
        if not file_path.is_file():
            continue

        relative_parts = set(file_path.relative_to(root).parts)
        if relative_parts & EXCLUDE_DIRS:
            continue

        name = file_path.name
        if any(token in name for token in (".test.", ".spec.", ".stories.")):
            continue

        if file_path.suffix.lower() in JS_EXTENSIONS:
            all_source_files.append(file_path)

    entry_names = {
        "index.js",
        "index.jsx",
        "index.ts",
        "index.tsx",
        "main.js",
        "main.jsx",
        "main.ts",
        "main.tsx",
    }
    entry_candidates = [file_path for file_path in all_source_files if file_path.name in entry_names]

    router_names = {
        "App.jsx",
        "App.tsx",
        "App.js",
        "App.ts",
        "routes.jsx",
        "routes.tsx",
        "Router.jsx",
        "Router.tsx",
        "AppRouter.jsx",
        "AppRouter.tsx",
    }
    router_candidates = [
        file_path for file_path in all_source_files if file_path.name in router_names
    ]

    config_files: list[Path] = []
    for name_pattern in (
        "vite.config.js",
        "vite.config.ts",
        "webpack.config.js",
        "webpack.config.ts",
        "craco.config.js",
        "next.config.js",
        "next.config.ts",
    ):
        config_path = root / name_pattern
        if config_path.exists():
            config_files.append(config_path)

    return ProjectFiles(
        root=root,
        package_json=pkg_json_path,
        all_source_files=sorted(all_source_files),
        entry_candidates=sorted(entry_candidates),
        router_candidates=sorted(router_candidates),
        config_files=sorted(config_files),
    )
