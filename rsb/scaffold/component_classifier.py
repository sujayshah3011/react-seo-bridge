"""
component_classifier.py - Classifies React components as Client or Server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from rsb.analyser.ast_parser import find_nodes_by_type, get_node_text, parse_file


class ComponentType(str, Enum):
    SERVER = "server"
    CLIENT = "client"
    UNKNOWN = "unknown"


CLIENT_HOOKS = {
    "useState",
    "useReducer",
    "useContext",
    "useRef",
    "useCallback",
    "useMemo",
    "useEffect",
    "useLayoutEffect",
    "useImperativeHandle",
    "useDeferredValue",
    "useTransition",
    "useNavigate",
    "useLocation",
    "useParams",
    "useSearchParams",
    "useHistory",
    "useRouteMatch",
    "useQuery",
    "useMutation",
    "useSWR",
    "useSelector",
    "useDispatch",
    "useForm",
    "useAnimation",
    "useMotionValue",
}
CLIENT_GLOBALS = {
    "window",
    "document",
    "localStorage",
    "sessionStorage",
    "navigator",
    "location",
    "history",
    "alert",
    "confirm",
    "requestAnimationFrame",
    "cancelAnimationFrame",
    "IntersectionObserver",
    "ResizeObserver",
    "MutationObserver",
}
CLIENT_EVENT_PATTERN = re.compile(r"on[A-Z][a-zA-Z]+\s*=")


@dataclass
class ClassificationResult:
    file_path: str
    component_type: ComponentType
    reasons: list[str] = field(default_factory=list)
    client_hooks_found: list[str] = field(default_factory=list)
    has_data_fetching: bool = False
    data_fetch_pattern: str = "none"
    migration_notes: list[str] = field(default_factory=list)


def classify_component(file_path: Path) -> ClassificationResult:
    result = ClassificationResult(file_path=str(file_path), component_type=ComponentType.UNKNOWN)

    try:
        source_bytes = file_path.read_bytes()
        source_text = source_bytes.decode("utf-8", errors="replace")
    except OSError:
        return result

    reasons: list[str] = []
    client_hooks: list[str] = []
    root = parse_file(file_path)

    if root is not None:
        for call_node in find_nodes_by_type(root, "call_expression"):
            function_node = call_node.child_by_field_name("function")
            if function_node is None:
                continue

            raw_name = get_node_text(function_node, source_bytes)
            function_name = raw_name.split(".")[-1]
            if function_name in CLIENT_HOOKS and function_name not in client_hooks:
                client_hooks.append(function_name)
                reasons.append(f"Uses {function_name}()")

    for global_name in sorted(CLIENT_GLOBALS):
        if re.search(rf"\b{re.escape(global_name)}\b", source_text):
            reasons.append(f"Accesses browser global: {global_name}")

    if CLIENT_EVENT_PATTERN.search(source_text):
        reasons.append("Has JSX event handlers (onClick, onChange, etc.)")

    if "useQuery" in source_text or "useMutation" in source_text:
        result.has_data_fetching = True
        result.data_fetch_pattern = "react_query"
        if "useQuery" not in client_hooks and "useQuery" in source_text:
            client_hooks.append("useQuery")
        result.migration_notes.append(
            "useQuery/useMutation can often become server-side fetch() calls in an async "
            "Server Component when the data is not user-specific."
        )
    elif "useSWR" in source_text:
        result.has_data_fetching = True
        result.data_fetch_pattern = "swr"
        if "useSWR" not in client_hooks:
            client_hooks.append("useSWR")
        result.migration_notes.append(
            "useSWR can usually become a top-level await fetch() in a Server Component for public data."
        )
    elif re.search(r"useEffect\s*\([\s\S]*?fetch\s*\(", source_text):
        result.has_data_fetching = True
        result.data_fetch_pattern = "useEffect_fetch"
        result.migration_notes.append(
            "useEffect + fetch() can often move into an async Server Component with direct await fetch()."
        )

    result.client_hooks_found = client_hooks

    if reasons:
        result.component_type = ComponentType.CLIENT
        result.reasons = reasons
        if "useEffect" in client_hooks and result.has_data_fetching:
            result.migration_notes.append(
                "Consider splitting this into a Server Component data wrapper and a smaller Client Component "
                "for interactivity."
            )
    else:
        result.component_type = ComponentType.SERVER
        result.reasons = ["No client-only hooks, globals, or event handlers detected"]
        if result.has_data_fetching:
            result.migration_notes.append(
                "This looks like a candidate for a pure async Server Component in Next.js App Router."
            )

    return result
