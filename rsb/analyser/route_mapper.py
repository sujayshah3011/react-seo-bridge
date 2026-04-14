"""
route_mapper.py - Extracts route definitions from React Router v5/v6 configs.
"""

from __future__ import annotations

import re
from pathlib import Path

from rsb.analyser.ast_parser import find_nodes_by_type, get_node_text, parse_file
from rsb.analyser.project_scanner import JS_EXTENSIONS, ProjectFiles
from rsb.schemas import DataFetchPattern, RouteInfo


_ROUTE_PATH_RE = re.compile(r"""path\s*[=:]\s*["']([^"']+)["']""")
_LAZY_ASSIGN_RE = re.compile(
    r"""(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)\s*=\s*(?:React\.)?lazy\s*\(\s*\(\s*\)\s*=>\s*import\(\s*["']([^"']+)["']\s*\)\s*\)""",
    re.MULTILINE,
)
_IMPORT_RE = re.compile(
    r"""import\s+(?P<clause>[\w\s{},*]+?)\s+from\s+["'](?P<source>[^"']+)["']""",
    re.MULTILINE,
)
_USE_EFFECT_FETCH_RE = re.compile(r"""useEffect\s*\([^)]*=>[\s\S]*?fetch\s*\(""")
_FETCH_PATTERNS: tuple[tuple[str, DataFetchPattern], ...] = (
    ("useQuery", DataFetchPattern.REACT_QUERY),
    ("useMutation", DataFetchPattern.REACT_QUERY),
    ("useSWR", DataFetchPattern.SWR),
    ("useBaseQuery", DataFetchPattern.RTK_QUERY),
)


def map_routes(project_files: ProjectFiles) -> list[RouteInfo]:
    """
    Scan the project and return all discovered routes.
    Deduplicates by path string.
    """

    routes: list[RouteInfo] = []
    seen_paths: set[str] = set()

    files_to_scan = list(project_files.router_candidates)
    files_to_scan.extend(
        file_path
        for file_path in project_files.all_source_files
        if file_path not in files_to_scan
    )

    for file_path in files_to_scan:
        try:
            file_routes = _extract_routes_from_file(file_path)
        except Exception:
            continue

        for route in file_routes:
            if route.path in seen_paths:
                continue
            seen_paths.add(route.path)
            routes.append(route)

    if not routes:
        routes.append(RouteInfo(path="/*", is_dynamic=True, component_file=None))

    return routes


def _extract_routes_from_file(file_path: Path) -> list[RouteInfo]:
    source_bytes = file_path.read_bytes()
    source_text = source_bytes.decode("utf-8", errors="replace")
    import_map = _build_import_map(file_path, source_text)
    lazy_map = _build_lazy_map(file_path, source_text)

    routes: list[RouteInfo] = []
    root = parse_file(file_path)
    if root is not None:
        routes.extend(
            _find_jsx_routes(root, source_bytes, source_text, file_path, import_map, lazy_map)
        )
        routes.extend(_find_router_config_routes(source_text, file_path, import_map, lazy_map))

    if not routes:
        routes.extend(_regex_fallback(source_text, file_path))

    return routes


def _find_jsx_routes(
    root,
    source_bytes: bytes,
    source_text: str,
    file_path: Path,
    import_map: dict[str, Path],
    lazy_map: dict[str, Path],
) -> list[RouteInfo]:
    routes: list[RouteInfo] = []

    jsx_nodes = find_nodes_by_type(root, "jsx_opening_element") + find_nodes_by_type(
        root, "jsx_self_closing_element"
    )
    for jsx_elem in jsx_nodes:
        element_name = _get_jsx_element_name(jsx_elem, source_bytes)
        if element_name != "Route":
            continue

        path_value = _extract_jsx_attr(jsx_elem, "path", source_bytes)
        if not path_value or not path_value.startswith("/"):
            continue

        component_value = _extract_jsx_attr(jsx_elem, "component", source_bytes)
        element_value = _extract_jsx_attr(jsx_elem, "element", source_bytes)
        component_ref = _extract_component_ref(component_value or element_value or "")
        resolved_component = _resolve_component_file(component_ref, import_map, lazy_map)
        is_lazy = bool(component_ref and component_ref in lazy_map) or _check_if_lazy(
            component_ref, source_text
        )

        routes.append(
            RouteInfo(
                path=path_value,
                component_file=str(resolved_component) if resolved_component else str(file_path),
                is_dynamic=":" in path_value or "*" in path_value,
                is_lazy=is_lazy,
                data_fetch_pattern=_detect_data_fetch_pattern(resolved_component),
                line_number=jsx_elem.start_point[0] + 1,
            )
        )

    return routes


def _find_router_config_routes(
    source_text: str,
    file_path: Path,
    import_map: dict[str, Path],
    lazy_map: dict[str, Path],
) -> list[RouteInfo]:
    routes: list[RouteInfo] = []
    if not any(name in source_text for name in ("createBrowserRouter", "createHashRouter", "useRoutes")):
        return routes

    config_route_re = re.compile(
        r"""path\s*:\s*["'](?P<path>[^"']+)["'][\s\S]{0,200}?(?:element\s*:\s*<(?P<element>[A-Z][A-Za-z0-9_]*)|component\s*:\s*(?P<component>[A-Z][A-Za-z0-9_]*))""",
        re.MULTILINE,
    )

    for match in config_route_re.finditer(source_text):
        path_value = match.group("path")
        if not path_value.startswith("/"):
            continue

        component_ref = match.group("element") or match.group("component")
        resolved_component = _resolve_component_file(component_ref, import_map, lazy_map)
        line_number = source_text.count("\n", 0, match.start()) + 1

        routes.append(
            RouteInfo(
                path=path_value,
                component_file=str(resolved_component) if resolved_component else str(file_path),
                is_dynamic=":" in path_value or "*" in path_value,
                is_lazy=bool(component_ref and component_ref in lazy_map),
                data_fetch_pattern=_detect_data_fetch_pattern(resolved_component),
                line_number=line_number,
            )
        )

    return routes


def _regex_fallback(source_text: str, file_path: Path) -> list[RouteInfo]:
    routes: list[RouteInfo] = []
    for match in _ROUTE_PATH_RE.finditer(source_text):
        path_value = match.group(1)
        if not path_value.startswith("/"):
            continue
        routes.append(
            RouteInfo(
                path=path_value,
                component_file=str(file_path),
                is_dynamic=":" in path_value or "*" in path_value,
                line_number=source_text.count("\n", 0, match.start()) + 1,
            )
        )
    return routes


def _extract_jsx_attr(jsx_elem, attr_name: str, source_bytes: bytes) -> str | None:
    for child in jsx_elem.children:
        if child.type != "jsx_attribute":
            continue
        name_node = child.child(0)
        if name_node is None:
            continue
        if get_node_text(name_node, source_bytes) != attr_name:
            continue
        value_node = child.child_by_field_name("value")
        if value_node is None and child.child_count > 0:
            value_node = child.children[-1]
        if value_node is None:
            return None
        return get_node_text(value_node, source_bytes).strip().strip("{}").strip("'\"`")
    return None


def _get_jsx_element_name(jsx_elem, source_bytes: bytes) -> str | None:
    name_node = jsx_elem.child_by_field_name("name")
    if name_node is not None:
        return get_node_text(name_node, source_bytes)

    for child in jsx_elem.children:
        if child.type in {"identifier", "nested_identifier", "member_expression"}:
            return get_node_text(child, source_bytes)
    return None


def _extract_component_ref(raw_value: str) -> str | None:
    if not raw_value:
        return None

    jsx_match = re.search(r"""<\s*([A-Z][A-Za-z0-9_]*)""", raw_value)
    if jsx_match:
        return jsx_match.group(1)

    ident_match = re.search(r"""\b([A-Z][A-Za-z0-9_]*)\b""", raw_value)
    if ident_match:
        return ident_match.group(1)
    return None


def _check_if_lazy(component_ref: str | None, source_text: str) -> bool:
    if component_ref:
        lazy_pattern = re.compile(
            rf"""(?:const|let|var)\s+{re.escape(component_ref)}\s*=\s*(?:React\.)?lazy\s*\("""
        )
        return bool(lazy_pattern.search(source_text))
    return "React.lazy(" in source_text or "lazy(() => import(" in source_text


def _build_import_map(file_path: Path, source_text: str) -> dict[str, Path]:
    imports: dict[str, Path] = {}
    for match in _IMPORT_RE.finditer(source_text):
        import_source = match.group("source")
        if not import_source.startswith("."):
            continue

        resolved = _resolve_relative_import(file_path, import_source)
        if resolved is None:
            continue

        clause = match.group("clause").strip()
        for specifier in _extract_imported_identifiers(clause):
            imports[specifier] = resolved
    return imports


def _build_lazy_map(file_path: Path, source_text: str) -> dict[str, Path]:
    lazy_map: dict[str, Path] = {}
    for match in _LAZY_ASSIGN_RE.finditer(source_text):
        component_name = match.group(1)
        import_source = match.group(2)
        resolved = _resolve_relative_import(file_path, import_source)
        if resolved is not None:
            lazy_map[component_name] = resolved
    return lazy_map


def _extract_imported_identifiers(clause: str) -> list[str]:
    identifiers: list[str] = []

    clause = clause.strip()
    if clause.startswith("* as "):
        return [clause.split()[-1]]

    if "{" in clause and "}" in clause:
        before_named, _, remainder = clause.partition("{")
        default_name = before_named.rstrip(", ").strip()
        if default_name:
            identifiers.append(default_name)

        named_section = remainder.split("}", 1)[0]
        for part in named_section.split(","):
            name = part.strip()
            if not name:
                continue
            if " as " in name:
                name = name.split(" as ", 1)[1].strip()
            identifiers.append(name)
        return identifiers

    if clause:
        identifiers.append(clause.split(",", 1)[0].strip())
    return [identifier for identifier in identifiers if identifier]


def _resolve_relative_import(file_path: Path, import_source: str) -> Path | None:
    candidate = (file_path.parent / import_source).resolve()
    if candidate.is_file() and candidate.suffix.lower() in JS_EXTENSIONS:
        return candidate

    for extension in sorted(JS_EXTENSIONS):
        with_ext = candidate.with_suffix(extension)
        if with_ext.exists():
            return with_ext

    if candidate.is_dir():
        for extension in sorted(JS_EXTENSIONS):
            index_file = candidate / f"index{extension}"
            if index_file.exists():
                return index_file
    return None


def _resolve_component_file(
    component_ref: str | None,
    import_map: dict[str, Path],
    lazy_map: dict[str, Path],
) -> Path | None:
    if component_ref is None:
        return None
    return lazy_map.get(component_ref) or import_map.get(component_ref)


def _detect_data_fetch_pattern(component_file: Path | None) -> DataFetchPattern:
    if component_file is None:
        return DataFetchPattern.NONE

    try:
        source_text = component_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return DataFetchPattern.NONE

    for token, pattern in _FETCH_PATTERNS:
        if token in source_text:
            return pattern

    if _USE_EFFECT_FETCH_RE.search(source_text):
        return DataFetchPattern.USE_EFFECT

    return DataFetchPattern.NONE
