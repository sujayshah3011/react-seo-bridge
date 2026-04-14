"""
ast_parser.py - tree-sitter wrapper for parsing JS/JSX/TS/TSX source files.

Uses the tree-sitter 0.25.x API with pre-compiled language wheels.
Languages are cached at module level for performance.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser


_JS_LANGUAGE = Language(tsjavascript.language())
_TS_LANGUAGE = Language(tstypescript.language_typescript())
_TSX_LANGUAGE = Language(tstypescript.language_tsx())


def _get_language(file_path: Path) -> Language:
    ext = file_path.suffix.lower()
    if ext == ".tsx":
        return _TSX_LANGUAGE
    if ext == ".ts":
        return _TS_LANGUAGE
    return _JS_LANGUAGE


def parse_file(file_path: Path) -> Node | None:
    """
    Parse a JS/JSX/TS/TSX file and return the root AST node.
    Returns None if the file cannot be read or parsed.
    """

    try:
        source = file_path.read_bytes()
    except OSError:
        return None

    try:
        parser = Parser(_get_language(file_path))
        tree = parser.parse(source)
    except Exception:
        return None
    return tree.root_node


def find_nodes_by_type(root: Node, node_type: str) -> list[Node]:
    """
    Recursively find all AST nodes of a given type under root.
    Example: find_nodes_by_type(root, "call_expression")
    """

    results: list[Node] = []
    _walk(root, node_type, results)
    return results


def _walk(node: Node, target_type: str, results: list[Node]) -> None:
    if node.type == target_type:
        results.append(node)
    for child in node.children:
        _walk(child, target_type, results)


def get_node_text(node: Node, source: bytes) -> str:
    """Extract the raw source text for a given AST node."""

    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def find_imports(root: Node, source: bytes) -> list[dict[str, object]]:
    """
    Return all import declarations as a list of dictionaries:
    [{"source": "react-router-dom", "specifiers": ["Route"], "line": 3}]
    """

    imports: list[dict[str, object]] = []
    for node_type in ("import_statement", "import_declaration"):
        for node in find_nodes_by_type(root, node_type):
            source_node = _find_child_by_type(node, "string")
            if source_node is None:
                continue

            raw_source = get_node_text(source_node, source).strip("'\"`")
            specifiers = _extract_import_specifiers(node, source)
            imports.append(
                {
                    "source": raw_source,
                    "specifiers": specifiers,
                    "line": node.start_point[0] + 1,
                }
            )
    return imports


def _find_child_by_type(node: Node, child_type: str) -> Node | None:
    for child in node.children:
        if child.type == child_type:
            return child
    return None


def _extract_import_specifiers(import_node: Node, source: bytes) -> list[str]:
    specs: list[str] = []
    for child in import_node.children:
        if child.type not in {"import_clause", "named_imports"}:
            continue
        for sub in child.children:
            if sub.type == "identifier":
                text = get_node_text(sub, source).strip()
                if text:
                    specs.append(text)
            elif sub.type == "import_specifier":
                identifier = _find_child_by_type(sub, "identifier")
                if identifier is not None:
                    text = get_node_text(identifier, source).strip()
                    if text:
                        specs.append(text)
    return specs
