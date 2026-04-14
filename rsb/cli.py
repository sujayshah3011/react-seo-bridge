"""
cli.py - Typer CLI for react-seo-bridge.

Commands:
  rsb audit <project_path>    Run Mode C: static SEO audit
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

    from rsb.analyser.bundle_analyser import analyse_bundle
    from rsb.analyser.cwv_estimator import estimate_cwv
    from rsb.analyser.metadata_detector import detect_metadata
    from rsb.analyser.project_scanner import ProjectScanError, scan_project
    from rsb.analyser.route_mapper import map_routes
    from rsb.reporters.audit_report import (
        build_audit_result,
        write_json_report,
        write_markdown_report,
    )

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
            project_files = scan_project(project_path)
        except ProjectScanError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        progress.update(
            task_id, description=f"Found {len(project_files.all_source_files)} source files"
        )
        progress.update(task_id, description="Analysing package.json...")
        bundle = analyse_bundle(project_files)

        progress.update(task_id, description="Mapping routes...")
        routes = map_routes(project_files)

        progress.update(task_id, description="Detecting metadata patterns...")
        metadata_findings = detect_metadata(project_files)

        progress.update(task_id, description="Estimating Core Web Vitals risks...")
        cwv = estimate_cwv(project_files, routes)

        progress.update(task_id, description="Building audit report...")
        result = build_audit_result(
            project_path=str(Path(project_path).resolve()),
            bundle=bundle,
            routes=routes,
            metadata_findings=metadata_findings,
            cwv=cwv,
        )

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
