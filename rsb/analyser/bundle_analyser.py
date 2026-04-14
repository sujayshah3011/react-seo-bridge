"""
bundle_analyser.py - Analyses package.json and build configs to determine
framework, rendering type, and installed SEO-relevant packages.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from rsb.analyser.project_scanner import ProjectFiles
from rsb.schemas import BundleInfo, RenderingType


_SEMVER_MAJOR_RE = re.compile(r"""[\^~]?(\d+)\.""")


def _major_version(version_str: str) -> str | None:
    """Extract a major version number from a semver string like '^6.0.0'."""

    match = _SEMVER_MAJOR_RE.match(version_str.lstrip(" \t"))
    return match.group(1) if match else None


def analyse_bundle(project_files: ProjectFiles) -> BundleInfo:
    """Analyse package.json and build configs. Never raises - returns defaults on error."""

    try:
        raw = json.loads(project_files.package_json.read_text(encoding="utf-8"))
    except Exception:
        return BundleInfo(framework="unknown")

    deps: dict[str, str] = {}
    deps.update(raw.get("dependencies", {}))
    deps.update(raw.get("devDependencies", {}))

    framework = "unknown"
    rendering_type = RenderingType.CSR

    if "next" in deps:
        framework = "nextjs"
        rendering_type = RenderingType.SSR
    elif "@craco/craco" in deps or _is_cra(project_files.root):
        framework = "cra"
    elif "vite" in deps:
        framework = "vite"
    elif "webpack" in deps or "webpack-cli" in deps:
        framework = "webpack"

    react_router_version = None
    if "react-router-dom" in deps:
        react_router_version = _major_version(deps["react-router-dom"])
    elif "react-router" in deps:
        react_router_version = _major_version(deps["react-router"])

    react_version = _major_version(deps.get("react", ""))

    has_ssr = any(
        dependency in deps
        for dependency in (
            "next",
            "@remix-run/react",
            "gatsby",
            "astro",
            "express",
            "fastify",
            "@hapi/hapi",
        )
    )
    has_ssg = any(
        dependency in deps
        for dependency in (
            "gatsby",
            "astro",
            "@11ty/eleventy",
            "nuxt",
        )
    )
    if has_ssr:
        rendering_type = RenderingType.SSR
    if has_ssg:
        rendering_type = RenderingType.SSG

    has_helmet = "react-helmet" in deps
    has_helmet_async = "react-helmet-async" in deps
    has_react_query = any(
        dependency in deps for dependency in ("@tanstack/react-query", "react-query")
    )
    has_swr = "swr" in deps
    has_existing_prerender = any(
        dependency in deps
        for dependency in (
            "prerender",
            "react-snap",
            "react-snap-shot",
            "rendertron",
            "puppeteer",
        )
    )

    build_output_dir = _detect_build_output(project_files)
    entry_point = str(project_files.entry_candidates[0]) if project_files.entry_candidates else None

    return BundleInfo(
        framework=framework,
        react_version=react_version,
        react_router_version=react_router_version,
        has_ssr_setup=has_ssr,
        has_ssg_setup=has_ssg,
        has_helmet=has_helmet,
        has_helmet_async=has_helmet_async,
        has_react_query=has_react_query,
        has_swr=has_swr,
        has_existing_prerender=has_existing_prerender,
        entry_point=entry_point,
        build_output_dir=build_output_dir,
        total_dependencies=len(deps),
        rendering_type=rendering_type,
    )


def _is_cra(root: Path) -> bool:
    """Detect Create React App by presence of react-scripts in scripts."""

    package_json = root / "package.json"
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except Exception:
        return False

    scripts = data.get("scripts", {})
    return any("react-scripts" in str(value) for value in scripts.values())


def _detect_build_output(project_files: ProjectFiles) -> str | None:
    """Detect build output directory from config files."""

    for config_file in project_files.config_files:
        try:
            text = config_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = re.search(r"""outDir\s*:\s*["']([^"']+)["']""", text)
        if match:
            return match.group(1)

    if (project_files.root / "build").exists():
        return "build"
    if (project_files.root / "dist").exists():
        return "dist"
    return None
