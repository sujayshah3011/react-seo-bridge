"""
cwv_estimator.py - Heuristic Core Web Vitals risk estimation.

No browser, no Lighthouse - pure static analysis.
These are risk indicators, not measurements.
"""

from __future__ import annotations

import re

from rsb.analyser.project_scanner import ProjectFiles
from rsb.schemas import CWVEstimate, CWVRisk, RouteInfo


_IMG_WITHOUT_DIMS_RE = re.compile(
    r"""<img(?![^>]*(?:width|height))[^>]*>""",
    re.IGNORECASE | re.DOTALL,
)
_THIRD_PARTY_SCRIPT_RE = re.compile(
    r"""<script[^>]+src=["']https?://""",
    re.IGNORECASE,
)
_IMPORT_RE = re.compile(
    r"""^\s*(?:import\b|(?:const|let|var)\s+.+?=\s*require\s*\()""",
    re.MULTILINE,
)


def estimate_cwv(project_files: ProjectFiles, routes: list[RouteInfo]) -> CWVEstimate:
    """Estimate Core Web Vitals risks from static analysis."""

    notes: list[str] = []
    total_imports = 0
    images_without_dimensions = 0
    third_party_scripts = 0

    for file_path in project_files.all_source_files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total_imports += len(_IMPORT_RE.findall(text))
        images_without_dimensions += len(_IMG_WITHOUT_DIMS_RE.findall(text))

    for html_name in ("index.html", "public/index.html"):
        html_path = project_files.root / html_name
        if not html_path.exists():
            continue
        try:
            html_text = html_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        third_party_scripts += len(_THIRD_PARTY_SCRIPT_RE.findall(html_text))

    total_routes = max(len(routes), 1)
    lazy_routes = sum(1 for route in routes if route.is_lazy)
    estimated_imports_per_route = total_imports / total_routes
    large_bundle_risk = estimated_imports_per_route > 10 or len(project_files.all_source_files) > 100

    # LCP HIGH when static analysis suggests large route payloads:
    # - more than 10 imports per route on average, or
    # - a large codebase that likely produces a large bundle.
    if large_bundle_risk:
        lcp_risk = CWVRisk.HIGH
        notes.append(
            f"LCP HIGH: estimated {estimated_imports_per_route:.1f} imports per route suggest "
            "heavy JavaScript before content can render."
        )
    elif estimated_imports_per_route > 6:
        lcp_risk = CWVRisk.MEDIUM
        notes.append(
            f"LCP MEDIUM: estimated {estimated_imports_per_route:.1f} imports per route. "
            "Review route-level code splitting."
        )
    else:
        lcp_risk = CWVRisk.LOW

    # CLS HIGH when more than 3 images are missing explicit dimensions.
    if images_without_dimensions > 3:
        cls_risk = CWVRisk.HIGH
        notes.append(
            f"CLS HIGH: {images_without_dimensions} <img> tags found without width/height."
        )
    elif images_without_dimensions > 0:
        cls_risk = CWVRisk.MEDIUM
        notes.append(
            f"CLS MEDIUM: {images_without_dimensions} <img> tag(s) without width/height."
        )
    else:
        cls_risk = CWVRisk.LOW

    # FID/INP HIGH when more than half the routes are lazy-loaded, because first navigation
    # to each route requires fetching another chunk before interaction can complete.
    lazy_ratio = lazy_routes / total_routes
    if lazy_ratio > 0.5:
        fid_risk = CWVRisk.HIGH
        notes.append(
            f"INP HIGH: {lazy_routes}/{total_routes} routes are lazy-loaded. "
            "Prefetch critical routes or trim route-level chunk sizes."
        )
    elif lazy_ratio > 0.0:
        fid_risk = CWVRisk.MEDIUM
        notes.append(
            f"INP MEDIUM: {lazy_routes}/{total_routes} routes are lazy-loaded."
        )
    else:
        fid_risk = CWVRisk.LOW

    if third_party_scripts > 0:
        notes.append(
            f"PERF NOTE: {third_party_scripts} third-party script(s) detected in index.html."
        )

    return CWVEstimate(
        lcp_risk=lcp_risk,
        cls_risk=cls_risk,
        fid_risk=fid_risk,
        estimated_js_imports_per_route=round(estimated_imports_per_route, 1),
        images_without_dimensions=images_without_dimensions,
        lazy_loaded_routes=lazy_routes,
        third_party_scripts=third_party_scripts,
        large_bundle_risk=large_bundle_risk,
        notes=notes,
    )
