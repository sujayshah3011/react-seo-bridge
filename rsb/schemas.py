"""
All Pydantic v2 data models for react-seo-bridge.
Imported by every other module - never define schemas elsewhere.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class RenderingType(str, Enum):
    CSR = "csr"
    SSR = "ssr"
    SSG = "ssg"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DataFetchPattern(str, Enum):
    USE_EFFECT = "useEffect_fetch"
    REACT_QUERY = "react_query"
    SWR = "swr"
    RTK_QUERY = "rtk_query"
    NONE = "none"


class MetaStrategy(str, Enum):
    HELMET = "react_helmet"
    HELMET_ASYNC = "react_helmet_async"
    DOCUMENT_TITLE = "document_title_direct"
    NONE = "none"


class CWVRisk(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RouteInfo(BaseModel):
    """A single route discovered from React Router config."""

    path: str = Field(description="Route path, e.g. '/product/:id'")
    component_file: str | None = Field(
        default=None,
        description="Resolved absolute path to the component file",
    )
    is_dynamic: bool = Field(
        default=False,
        description="True if path contains :param or * wildcard",
    )
    is_lazy: bool = Field(
        default=False,
        description="True if component is wrapped in React.lazy()",
    )
    data_fetch_pattern: DataFetchPattern = Field(default=DataFetchPattern.NONE)
    line_number: int | None = Field(
        default=None,
        description="Line number where route is defined",
    )


class MetadataInfo(BaseModel):
    """Metadata handling analysis for a single component file."""

    file_path: str
    strategy: MetaStrategy = Field(default=MetaStrategy.NONE)
    sets_title: bool = False
    sets_description: bool = False
    sets_og_tags: bool = False
    sets_canonical: bool = False
    title_is_dynamic: bool = Field(
        default=False,
        description="True if title depends on props/state (computed at runtime)",
    )
    line_numbers: list[int] = Field(default_factory=list)


class BundleInfo(BaseModel):
    """Information derived from package.json and build config files."""

    framework: str = Field(description="'cra' | 'vite' | 'webpack' | 'unknown'")
    react_version: str | None = None
    react_router_version: str | None = None
    has_ssr_setup: bool = False
    has_ssg_setup: bool = False
    has_helmet: bool = False
    has_helmet_async: bool = False
    has_react_query: bool = False
    has_swr: bool = False
    has_existing_prerender: bool = False
    entry_point: str | None = None
    build_output_dir: str | None = None
    total_dependencies: int = 0
    rendering_type: RenderingType = RenderingType.UNKNOWN


class CWVEstimate(BaseModel):
    """Heuristic Core Web Vitals risk estimates (no browser required)."""

    lcp_risk: CWVRisk = CWVRisk.UNKNOWN
    cls_risk: CWVRisk = CWVRisk.UNKNOWN
    fid_risk: CWVRisk = CWVRisk.UNKNOWN
    estimated_js_imports_per_route: float = 0.0
    images_without_dimensions: int = 0
    lazy_loaded_routes: int = 0
    third_party_scripts: int = 0
    large_bundle_risk: bool = False
    notes: list[str] = Field(default_factory=list)


class AuditIssue(BaseModel):
    """A single SEO issue found during analysis."""

    severity: Severity
    category: str = Field(
        description="Category: 'rendering'|'metadata'|'routing'|'cwv'|'crawlability'"
    )
    title: str
    description: str
    affected_files: list[str] = Field(default_factory=list)
    affected_routes: list[str] = Field(default_factory=list)
    recommendation: str
    docs_url: str | None = None


class AuditResult(BaseModel):
    """The complete audit result - serialisable to JSON and Markdown."""

    rsb_version: str = "0.1.0"
    project_path: str
    project_name: str
    analysed_at: str
    bundle: BundleInfo
    routes: list[RouteInfo] = Field(default_factory=list)
    metadata_findings: list[MetadataInfo] = Field(default_factory=list)
    cwv: CWVEstimate
    issues: list[AuditIssue] = Field(default_factory=list)
    total_routes: int = 0
    dynamic_routes: int = 0
    lazy_routes: int = 0
    routes_with_client_metadata: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    seo_score: int = Field(
        default=0,
        description="0-100 score. 0 = critical CSR issues. 100 = fully pre-rendered.",
    )
