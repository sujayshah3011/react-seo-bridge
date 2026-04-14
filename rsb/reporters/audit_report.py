"""
audit_report.py - Assembles AuditResult, generates issues, writes output files.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from rsb.schemas import (
    AuditIssue,
    AuditResult,
    BundleInfo,
    CWVEstimate,
    CWVRisk,
    MetadataInfo,
    MetaStrategy,
    RenderingType,
    RouteInfo,
    Severity,
)


TEMPLATES_DIR = Path(__file__).parent / "templates"


def build_audit_result(
    project_path: str,
    bundle: BundleInfo,
    routes: list[RouteInfo],
    metadata_findings: list[MetadataInfo],
    cwv: CWVEstimate,
) -> AuditResult:
    """Assemble all analysis results into a validated AuditResult."""

    project_root = Path(project_path).resolve()
    issues = _generate_issues(project_root, bundle, routes, metadata_findings, cwv)
    project_name = project_root.name

    critical = sum(1 for issue in issues if issue.severity == Severity.CRITICAL)
    high = sum(1 for issue in issues if issue.severity == Severity.HIGH)
    medium = sum(1 for issue in issues if issue.severity == Severity.MEDIUM)
    low = sum(1 for issue in issues if issue.severity == Severity.LOW)

    score = _compute_score(bundle, routes, metadata_findings, critical, high, medium)

    return AuditResult(
        project_path=str(project_root),
        project_name=project_name,
        analysed_at=datetime.now(timezone.utc).isoformat(),
        bundle=bundle,
        routes=routes,
        metadata_findings=metadata_findings,
        cwv=cwv,
        issues=issues,
        total_routes=len(routes),
        dynamic_routes=sum(1 for route in routes if route.is_dynamic),
        lazy_routes=sum(1 for route in routes if route.is_lazy),
        routes_with_client_metadata=_count_client_metadata_routes(routes, metadata_findings),
        critical_count=critical,
        high_count=high,
        medium_count=medium,
        low_count=low,
        seo_score=score,
    )


def write_json_report(result: AuditResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "rsb-audit.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def write_markdown_report(result: AuditResult, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("audit.md.j2")
    rendered = template.render(r=result)
    output_path = output_dir / "rsb-audit.md"
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def _generate_issues(
    project_root: Path,
    bundle: BundleInfo,
    routes: list[RouteInfo],
    metadata_findings: list[MetadataInfo],
    cwv: CWVEstimate,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    if bundle.rendering_type == RenderingType.CSR:
        issues.append(
            AuditIssue(
                severity=Severity.CRITICAL,
                category="rendering",
                title="Client-Side Rendering detected - content invisible to crawlers on Wave 1",
                description=(
                    f"This project uses {bundle.framework.upper()} with default client-side "
                    "rendering. Googlebot receives a near-empty HTML shell on the first fetch. "
                    "Your content only appears after JavaScript execution in Wave 2, "
                    "which can lag hours to days. AI crawlers (GPTBot, ClaudeBot, "
                    "PerplexityBot) do not execute JavaScript at all - they see nothing."
                ),
                recommendation=(
                    "Migrate to Next.js (SSR/SSG) for full pre-rendering, "
                    "or add a dynamic rendering layer (react-seo-bridge Mode A) "
                    "as an immediate stopgap. "
                    "Reference: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"
                ),
                docs_url="https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
            )
        )

    if not metadata_findings:
        issues.append(
            AuditIssue(
                severity=Severity.CRITICAL,
                category="metadata",
                title="No meta title or description management detected",
                description=(
                    "No react-helmet, react-helmet-async, or document.title usage was found. "
                    "Every page on this site likely shows the same default title from index.html. "
                    "Google uses page titles and descriptions as primary ranking signals."
                ),
                recommendation=(
                    "Install react-helmet-async and add a <Helmet> block to every page component "
                    "with a unique <title> and <meta name='description'>. "
                    "For Next.js migration, use the Metadata API instead."
                ),
            )
        )

    helmet_only = [
        finding
        for finding in metadata_findings
        if finding.strategy in (MetaStrategy.HELMET, MetaStrategy.HELMET_ASYNC)
    ]
    if helmet_only and bundle.rendering_type == RenderingType.CSR:
        issues.append(
            AuditIssue(
                severity=Severity.HIGH,
                category="metadata",
                title="Metadata managed via react-helmet on a CSR app - invisible to most bots",
                description=(
                    f"Found {len(helmet_only)} component(s) using react-helmet. "
                    "Since this is a CSR app, all meta tags are injected client-side after JS runs. "
                    "Social crawlers (Twitter, LinkedIn, Slack, Discord), AI crawlers, "
                    "and link preview generators read raw HTML only - they see no title or description."
                ),
                affected_files=[finding.file_path for finding in helmet_only[:5]],
                recommendation=(
                    "Either migrate to SSR/SSG (Next.js Metadata API renders meta tags server-side), "
                    "or implement a prerender layer that injects meta tags into the static HTML snapshot."
                ),
            )
        )

    dynamic_routes = [route for route in routes if route.is_dynamic]
    if dynamic_routes:
        issues.append(
            AuditIssue(
                severity=Severity.HIGH,
                category="routing",
                title=f"{len(dynamic_routes)} dynamic route(s) cannot be auto-sitemapped",
                description=(
                    f"Routes with :param segments ({', '.join(route.path for route in dynamic_routes[:3])}) "
                    "require a list of all valid IDs/slugs to be included in sitemap.xml. "
                    "Without a sitemap entry, Google discovers these pages only by following links - "
                    "which may never happen for deep product/article pages."
                ),
                affected_routes=[route.path for route in dynamic_routes],
                recommendation=(
                    "Generate a dynamic sitemap at build time using your CMS or database. "
                    "For react-seo-bridge Mode A, use the --ids-file flag to supply slug lists."
                ),
            )
        )

    if not _has_public_asset(project_root, "sitemap.xml"):
        issues.append(
            AuditIssue(
                severity=Severity.HIGH,
                category="crawlability",
                title="No sitemap.xml found",
                description=(
                    "Google relies on sitemap.xml for efficient page discovery. "
                    "Without it, Googlebot can only find pages by following links. "
                    "Deeply nested pages or pages not linked from navigation may never be indexed."
                ),
                recommendation=(
                    "Generate a sitemap.xml listing all static routes. "
                    "Submit it in Google Search Console. "
                    "For CRA/Vite: use 'react-router-sitemap-helper' or a build script. "
                    "react-seo-bridge will generate this automatically in Mode A."
                ),
            )
        )

    if not any(finding.sets_og_tags for finding in metadata_findings):
        issues.append(
            AuditIssue(
                severity=Severity.MEDIUM,
                category="metadata",
                title="No Open Graph (og:) meta tags detected",
                description=(
                    "Open Graph tags control how your pages appear when shared on Twitter, "
                    "LinkedIn, Slack, Discord, and iMessage. Without og:title, og:description, "
                    "and og:image, links to your site will render as plain bare URLs."
                ),
                recommendation=(
                    "Add og:title, og:description, og:image, and og:url to every page's Helmet block. "
                    "og:image should be an absolute URL to a 1200x630px image."
                ),
            )
        )

    if not any(finding.sets_canonical for finding in metadata_findings):
        issues.append(
            AuditIssue(
                severity=Severity.MEDIUM,
                category="metadata",
                title="No canonical link tags detected",
                description=(
                    "Without canonical tags, Google must guess which URL is the authoritative "
                    "version of a page. This is especially problematic for React Router apps where "
                    "query strings (/?sort=price, /?page=2) can create duplicate-content issues."
                ),
                recommendation=(
                    "Add <link rel='canonical' href='...'> to every page via Helmet. "
                    "The canonical URL should always be the clean, parameter-free version of the page."
                ),
            )
        )

    if cwv.lcp_risk == CWVRisk.HIGH:
        issues.append(
            AuditIssue(
                severity=Severity.MEDIUM,
                category="cwv",
                title="Largest Contentful Paint (LCP) risk: Large JavaScript bundle estimated",
                description=(
                    f"Estimated {cwv.estimated_js_imports_per_route:.1f} JS imports per route. "
                    "Large bundles delay LCP - the time until the main content appears. "
                    "Google uses LCP as a ranking factor via Core Web Vitals."
                ),
                recommendation=(
                    "Implement route-based code splitting with React.lazy(). "
                    "Use vite-bundle-visualizer (Vite) or source-map-explorer (CRA) "
                    "to identify the largest dependencies."
                ),
            )
        )

    if cwv.images_without_dimensions > 0:
        issues.append(
            AuditIssue(
                severity=Severity.MEDIUM,
                category="cwv",
                title=(
                    "Cumulative Layout Shift (CLS) risk: "
                    f"{cwv.images_without_dimensions} image(s) without dimensions"
                ),
                description=(
                    "Images without explicit width/height cause layout shift as they load. "
                    "Google penalises high CLS scores in rankings."
                ),
                recommendation=(
                    "Add width and height attributes to every <img> tag. "
                    "Also set CSS: img { height: auto } to maintain aspect ratio."
                ),
            )
        )

    if not _has_public_asset(project_root, "robots.txt"):
        issues.append(
            AuditIssue(
                severity=Severity.LOW,
                category="crawlability",
                title="No robots.txt found",
                description=(
                    "Without robots.txt, Google will crawl all directories including "
                    "build artifacts, source maps, and admin routes. "
                    "This wastes crawl budget and can expose internal paths."
                ),
                recommendation=(
                    "Create public/robots.txt with at minimum:\n"
                    "User-agent: *\nAllow: /\nSitemap: https://yoursite.com/sitemap.xml"
                ),
            )
        )

    return issues


def _compute_score(
    bundle: BundleInfo,
    routes: list[RouteInfo],
    metadata_findings: list[MetadataInfo],
    critical: int,
    high: int,
    medium: int,
) -> int:
    """
    SEO score formula:
    - Start at 100
    - Deduct 40 if rendering_type == CSR
    - Deduct 15 if no routes found
    - Deduct 10 if metadata is entirely client-side on a CSR app
    - Deduct 5 per critical issue (max 20)
    - Deduct 3 per high issue (max 15)
    - Deduct 1 per medium issue (max 10)
    - Minimum score: 0
    """

    score = 100

    if bundle.rendering_type == RenderingType.CSR:
        score -= 40

    if not routes or (len(routes) == 1 and routes[0].path == "/*"):
        score -= 15

    if metadata_findings and bundle.rendering_type == RenderingType.CSR:
        score -= 10

    score -= min(critical * 5, 20)
    score -= min(high * 3, 15)
    score -= min(medium, 10)

    return max(0, score)


def _count_client_metadata_routes(
    routes: list[RouteInfo],
    metadata_findings: list[MetadataInfo],
) -> int:
    client_metadata_files = {
        finding.file_path
        for finding in metadata_findings
        if finding.strategy
        in (MetaStrategy.HELMET, MetaStrategy.HELMET_ASYNC, MetaStrategy.DOCUMENT_TITLE)
    }
    count = 0
    for route in routes:
        if route.component_file and route.component_file in client_metadata_files:
            count += 1
    return count


def _has_public_asset(project_root: Path, filename: str) -> bool:
    return any(
        (candidate / filename).exists()
        for candidate in (project_root / "public", project_root)
    )
