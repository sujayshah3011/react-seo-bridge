"""
metadata_detector.py - Detects how and where meta tags are set in a React app.
"""

from __future__ import annotations

import re
from pathlib import Path

from rsb.analyser.ast_parser import find_imports, parse_file
from rsb.analyser.project_scanner import ProjectFiles
from rsb.schemas import MetaStrategy, MetadataInfo


_HELMET_BLOCK_RE = re.compile(r"""<Helmet\b[^>]*>(.*?)</Helmet>""", re.DOTALL)
_TITLE_RE = re.compile(r"""<title\b[^>]*>(.*?)</title>""", re.DOTALL | re.IGNORECASE)
_DESCRIPTION_RE = re.compile(
    r"""<meta\b[^>]+name=["']description["'][^>]*>""",
    re.IGNORECASE,
)
_OG_META_RE = re.compile(r"""og:(title|description|image|url)""", re.IGNORECASE)
_CANONICAL_RE = re.compile(r"""rel=["']canonical["']""", re.IGNORECASE)
_DOCUMENT_TITLE_ASSIGN_RE = re.compile(r"""document\.title\s*=\s*(.+)""")
_DYNAMIC_VALUE_RE = re.compile(r"""\{[^}]+\}|\bprops\b|\bstate\b|\bdata\b|\?.*:""")


def detect_metadata(project_files: ProjectFiles) -> list[MetadataInfo]:
    """
    Scan all source files for metadata management patterns.
    Returns one MetadataInfo per file that has any metadata handling.
    """

    findings: list[MetadataInfo] = []
    for file_path in project_files.all_source_files:
        try:
            info = _analyse_file(file_path)
        except Exception:
            continue
        if info is not None:
            findings.append(info)
    return findings


def _analyse_file(file_path: Path) -> MetadataInfo | None:
    source_bytes = file_path.read_bytes()
    source_text = source_bytes.decode("utf-8", errors="replace")

    if not any(
        keyword in source_text
        for keyword in (
            "Helmet",
            "document.title",
            "<title",
            "og:",
            "canonical",
            "meta name",
            "meta property",
        )
    ):
        return None

    strategy = MetaStrategy.NONE
    sets_title = False
    sets_description = False
    sets_og_tags = False
    sets_canonical = False
    title_is_dynamic = False
    line_numbers: list[int] = []

    root = parse_file(file_path)
    if root is not None:
        for imported in find_imports(root, source_bytes):
            source_name = imported.get("source")
            if source_name == "react-helmet-async":
                strategy = MetaStrategy.HELMET_ASYNC
                line_numbers.append(int(imported["line"]))
            elif source_name == "react-helmet" and strategy == MetaStrategy.NONE:
                strategy = MetaStrategy.HELMET
                line_numbers.append(int(imported["line"]))

    for match in _HELMET_BLOCK_RE.finditer(source_text):
        content = match.group(1)
        line_numbers.append(source_text.count("\n", 0, match.start()) + 1)

        title_match = _TITLE_RE.search(content)
        if title_match:
            sets_title = True
            if _DYNAMIC_VALUE_RE.search(title_match.group(1)):
                title_is_dynamic = True

        if _DESCRIPTION_RE.search(content):
            sets_description = True
        if _OG_META_RE.search(content):
            sets_og_tags = True
        if _CANONICAL_RE.search(content):
            sets_canonical = True

    for line_number, line in enumerate(source_text.splitlines(), 1):
        if "document.title" not in line:
            continue
        line_numbers.append(line_number)
        sets_title = True
        if strategy == MetaStrategy.NONE:
            strategy = MetaStrategy.DOCUMENT_TITLE
        assignment_match = _DOCUMENT_TITLE_ASSIGN_RE.search(line)
        if assignment_match is not None:
            assigned_value = assignment_match.group(1).strip()
            if not re.fullmatch(r"""["'][^"']*["'];?""", assigned_value):
                title_is_dynamic = True

    for match in _TITLE_RE.finditer(source_text):
        line_numbers.append(source_text.count("\n", 0, match.start()) + 1)
        sets_title = True
        if _DYNAMIC_VALUE_RE.search(match.group(1)):
            title_is_dynamic = True

    if _DESCRIPTION_RE.search(source_text):
        sets_description = True
    if _OG_META_RE.search(source_text):
        sets_og_tags = True
    if _CANONICAL_RE.search(source_text):
        sets_canonical = True

    if not any((strategy != MetaStrategy.NONE, sets_title, sets_description, sets_og_tags, sets_canonical)):
        return None

    return MetadataInfo(
        file_path=str(file_path),
        strategy=strategy,
        sets_title=sets_title,
        sets_description=sets_description,
        sets_og_tags=sets_og_tags,
        sets_canonical=sets_canonical,
        title_is_dynamic=title_is_dynamic,
        line_numbers=sorted(set(line_numbers)),
    )
