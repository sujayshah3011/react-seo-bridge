"""
cli.py - Typer CLI for react-seo-bridge.

Commands:
  rsb audit <project_path>    Run Mode C: static SEO audit
  rsb inject <project_path>   Generate Mode A dynamic rendering files
  rsb serve                   Run the Mode A prerender server
  rsb scaffold <project_path> Build Mode B migration context bundle
  rsb version                 Show version
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


if TYPE_CHECKING:
    from rsb.schemas import AuditResult


app = typer.Typer(
    name="rsb",
    help="react-seo-bridge - Static SEO auditor for React CSR applications.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def _build_audit_result(project_path: str):
    """Run the Mode C analysis pipeline and return project files plus audit result."""

    from rsb.analyser.bundle_analyser import analyse_bundle
    from rsb.analyser.cwv_estimator import estimate_cwv
    from rsb.analyser.metadata_detector import detect_metadata
    from rsb.analyser.project_scanner import ProjectScanError, scan_project
    from rsb.analyser.route_mapper import map_routes
    from rsb.reporters.audit_report import build_audit_result

    try:
        project_files = scan_project(project_path)
    except ProjectScanError:
        raise

    bundle = analyse_bundle(project_files)
    routes = map_routes(project_files)
    metadata_findings = detect_metadata(project_files)
    cwv = estimate_cwv(project_files, routes)
    audit_result = build_audit_result(
        project_path=str(Path(project_path).resolve()),
        bundle=bundle,
        routes=routes,
        metadata_findings=metadata_findings,
        cwv=cwv,
    )
    return project_files, audit_result


@app.command()
def audit(
    project_path: str = typer.Argument(
        ...,
        help="Path to the React project root (must contain package.json)",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Directory to write rsb-audit.json and rsb-audit.md. "
            "Defaults to <project_path>/rsb-output/"
        ),
    ),
    json_only: bool = typer.Option(
        False,
        "--json-only",
        help="Only write the JSON report, skip Markdown.",
    ),
    no_output: bool = typer.Option(
        False,
        "--no-output",
        help="Print summary to terminal only, do not write files.",
    ),
) -> None:
    """
    Run a static SEO audit on a React project.

    Analyses the codebase without executing Node.js or making network requests.
    Produces rsb-audit.json and rsb-audit.md in the output directory.
    """

    from rsb.reporters.audit_report import (
        write_json_report,
        write_markdown_report,
    )
    from rsb.analyser.project_scanner import ProjectScanError

    console.print(
        Panel.fit(
            "[bold]react-seo-bridge[/bold] - SEO Audit",
            subtitle="Mode C: Static Analysis",
            border_style="blue",
        )
    )

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task_id = progress.add_task("Scanning project files...", total=None)
        try:
            project_files, result = _build_audit_result(project_path)
        except ProjectScanError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        progress.update(
            task_id, description=f"Found {len(project_files.all_source_files)} source files"
        )
        progress.update(task_id, description="Building audit report...")

    _print_summary(result)

    if not no_output:
        target_dir = Path(output_dir) if output_dir else Path(project_path) / "rsb-output"
        json_path = write_json_report(result, target_dir)
        console.print(f"\nJSON report: [cyan]{json_path}[/cyan]")

        if not json_only:
            markdown_path = write_markdown_report(result, target_dir)
            console.print(f"Markdown report: [cyan]{markdown_path}[/cyan]")

    if result.critical_count > 0:
        raise typer.Exit(code=2)


@app.command()
def inject(
    project_path: str = typer.Argument(..., help="Path to React project root"),
    target: str = typer.Option(
        "vercel",
        "--target",
        "-t",
        help="Deploy target: vercel | cloudflare | nginx | express",
    ),
    prerender_url: str = typer.Option(
        ...,
        "--prerender-url",
        "-p",
        help="URL where your rsb prerender server is running, e.g. https://rsb.fly.dev",
    ),
    base_url: str = typer.Option(
        ...,
        "--base-url",
        "-b",
        help="Your site's base URL, e.g. https://mysite.com",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory. Defaults to <project_path>/rsb-output/inject/",
    ),
) -> None:
    """
    Mode A: Generate dynamic rendering config files for a React app.
    """

    from rsb.analyser.project_scanner import ProjectScanError, scan_project
    from rsb.analyser.route_mapper import map_routes
    from rsb.generators.cloudflare_worker import generate_cloudflare_files
    from rsb.generators.express_middleware import generate_express_middleware
    from rsb.generators.nginx_config import generate_nginx_snippet
    from rsb.generators.robots_gen import generate_robots
    from rsb.generators.sitemap_gen import generate_sitemap
    from rsb.generators.vercel_config import generate_vercel_files

    valid_targets = {"vercel", "cloudflare", "nginx", "express"}
    if target not in valid_targets:
        console.print(
            f"[red]Invalid target '{target}'. Choose from: {', '.join(sorted(valid_targets))}[/red]"
        )
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold]react-seo-bridge[/bold] - Inject Mode A\nTarget: [cyan]{target}[/cyan]",
            border_style="green",
        )
    )

    out_dir = Path(output_dir) if output_dir else Path(project_path) / "rsb-output" / "inject"

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task_id = progress.add_task("Scanning project...", total=None)
        try:
            project_files = scan_project(project_path)
        except ProjectScanError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        progress.update(task_id, description="Mapping routes for sitemap...")
        routes = map_routes(project_files)

    written_files: list[Path] = []
    if target == "vercel":
        written_files.extend(generate_vercel_files(prerender_url, out_dir).values())
    elif target == "cloudflare":
        written_files.extend(generate_cloudflare_files(prerender_url, out_dir).values())
    elif target == "nginx":
        written_files.append(generate_nginx_snippet(prerender_url, out_dir))
    else:
        written_files.append(generate_express_middleware(prerender_url, out_dir))

    written_files.append(generate_sitemap(base_url, routes, out_dir))
    written_files.append(generate_robots(base_url, out_dir))

    console.print(f"\nGenerated {len(written_files)} file(s) in [cyan]{out_dir}[/cyan]:\n")
    for file_path in written_files:
        console.print(f"  - {file_path.name}")

    console.print(
        f"""
[bold]Next steps:[/bold]
  1. Review the generated files in [cyan]{out_dir}[/cyan]
  2. Start the prerender server locally with [cyan]rsb serve --port 3000[/cyan]
  3. Or build the Docker image with [cyan]Dockerfile.prerender[/cyan]
  4. Set [cyan]RSB_PRERENDER_URL={prerender_url}[/cyan] in your deploy environment
  5. Copy [cyan]sitemap.xml[/cyan] and [cyan]robots.txt[/cyan] into your public asset folder
  6. Verify bot routing with [dim]curl -A "Googlebot" https://yoursite.com/[/dim]
"""
    )


@app.command()
def serve(
    port: int = typer.Option(3000, "--port", help="Port to run prerender server on"),
    cache_dir: str = typer.Option("/tmp/rsb-cache", "--cache-dir"),
    cache_ttl: int = typer.Option(86400, "--cache-ttl", help="Cache TTL in seconds"),
) -> None:
    """Start the RSB prerender server locally for development and testing."""

    import os
    from rsb.prerender.server import run_server

    os.environ["RSB_PORT"] = str(port)
    os.environ["RSB_CACHE_DIR"] = cache_dir
    os.environ["RSB_CACHE_TTL"] = str(cache_ttl)

    console.print(
        Panel.fit(
            f"[bold]RSB Prerender Server[/bold]\n"
            f"Port: [cyan]{port}[/cyan]  Cache: [cyan]{cache_dir}[/cyan]  TTL: [cyan]{cache_ttl}s[/cyan]",
            border_style="blue",
        )
    )
    console.print("[dim]Install Playwright browsers first if needed:[/dim]")
    console.print("[dim]  playwright install chromium[/dim]\n")
    run_server()


@app.command()
def scaffold(
    project_path: str = typer.Argument(..., help="Path to React project root"),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory. Defaults to <project_path>/rsb-output/scaffold/",
    ),
    target: str = typer.Option(
        "nextjs14",
        "--target",
        "-t",
        help="Migration target framework. Currently: nextjs14",
    ),
    no_audit: bool = typer.Option(
        False,
        "--no-audit",
        help="Skip running audit; use existing rsb-audit.json if present",
    ),
) -> None:
    """
    Mode B: Generate an LLM context bundle for a Next.js migration.
    """

    from rsb.analyser.project_scanner import ProjectScanError, scan_project
    from rsb.scaffold.context_builder import build_bundle
    from rsb.schemas import AuditResult

    if target != "nextjs14":
        console.print("[red]Only nextjs14 is currently supported for scaffold output.[/red]")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            "[bold]react-seo-bridge[/bold] - Scaffold Mode B",
            subtitle="Building LLM migration bundle",
            border_style="cyan",
        )
    )

    out_dir = Path(output_dir) if output_dir else Path(project_path) / "rsb-output" / "scaffold"
    audit_path = Path(project_path) / "rsb-output" / "rsb-audit.json"

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task_id = progress.add_task("Scanning project...", total=None)
        try:
            project_files = scan_project(project_path)
        except ProjectScanError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        if no_audit:
            progress.update(task_id, description="Loading existing audit result...")
            if not audit_path.exists():
                console.print(
                    f"[red]Expected existing audit report at {audit_path}, but it was not found.[/red]"
                )
                raise typer.Exit(code=1)
            audit_result = AuditResult.model_validate_json(audit_path.read_text(encoding="utf-8"))
        else:
            progress.update(task_id, description="Running SEO audit...")
            _, audit_result = _build_audit_result(project_path)

        progress.update(task_id, description="Building scaffold bundle...")
        bundle_paths = build_bundle(
            audit_result=audit_result,
            project_files=project_files,
            output_dir=out_dir,
            target_framework=target,
        )

    estimated_tokens = sum(len(path.read_text(encoding="utf-8")) // 4 for path in bundle_paths)

    console.print(
        f"""
Migration bundle ready!

  Files analysed:   [cyan]{len(project_files.all_source_files)}[/cyan]
  Routes found:     [cyan]{len(audit_result.routes)}[/cyan]
  Bundle chunks:    [cyan]{len(bundle_paths)}[/cyan]
  Estimated tokens: [cyan]{estimated_tokens:,}[/cyan]

[bold]Bundle location:[/bold]
"""
    )
    for bundle_path in bundle_paths:
        console.print(f"  [cyan]{bundle_path}[/cyan]")

    console.print(
        f"""
[bold]How to use:[/bold]
  1. Open [cyan]{bundle_paths[0]}[/cyan]
  2. Copy the entire file contents
  3. Paste into Claude at claude.ai or any large-context LLM
  4. The embedded instructions will guide the model to produce a full migration
"""
    )

    if audit_result.critical_count > 0:
        console.print(
            f"[yellow]Note:[/yellow] {audit_result.critical_count} critical SEO issue(s) were found. "
            "The scaffold bundle instructs the LLM to fix them during migration."
        )


def _print_summary(result: AuditResult) -> None:
    """Print a Rich summary table to the terminal."""

    score = result.seo_score
    colour = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    console.print(
        Panel(
            f"[bold {colour}]{score}/100[/bold {colour}]",
            title="SEO Score",
            border_style=colour,
            width=30,
        )
    )

    table = Table(title="Issues Found", show_header=True, header_style="bold")
    table.add_column("Severity", style="bold", width=12)
    table.add_column("Title")
    table.add_column("Category", width=14)

    severity_colours = {
        "critical": "red",
        "high": "bright_red",
        "medium": "yellow",
        "low": "blue",
        "info": "dim",
    }

    for issue in result.issues:
        colour = severity_colours.get(issue.severity.value, "white")
        table.add_row(
            f"[{colour}]{issue.severity.value.upper()}[/{colour}]",
            issue.title,
            issue.category,
        )

    console.print(table)
    console.print(
        f"\n[dim]Routes:[/dim] {result.total_routes} total "
        f"({result.dynamic_routes} dynamic, {result.lazy_routes} lazy)"
    )
    console.print(
        f"[dim]Framework:[/dim] {result.bundle.framework} "
        f"| [dim]Rendering:[/dim] {result.bundle.rendering_type.value}"
    )


@app.command()
def version() -> None:
    """Show react-seo-bridge version."""

    from rsb import __version__

    console.print(f"react-seo-bridge v{__version__}")


if __name__ == "__main__":
    app()
