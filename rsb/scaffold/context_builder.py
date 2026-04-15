"""
context_builder.py - Assembles the complete LLM context bundle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from rsb.analyser.project_scanner import ProjectFiles
from rsb.schemas import AuditResult
from rsb.scaffold.component_classifier import ComponentType, ClassificationResult, classify_component
from rsb.scaffold.token_chunker import Chunk, chunk_files


TEMPLATES_DIR = Path(__file__).parent / "prompt_templates"


def build_bundle(
    audit_result: AuditResult,
    project_files: ProjectFiles,
    output_dir: Path,
    target_framework: str = "nextjs14",
) -> list[Path]:
    """Build one or more scaffold bundle files from the audit result and source tree."""

    output_dir.mkdir(parents=True, exist_ok=True)
    environment = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    classifications: dict[str, ClassificationResult] = {}
    for file_path in project_files.all_source_files:
        classifications[str(file_path)] = classify_component(file_path)

    client_components = [
        path for path, classification in classifications.items() if classification.component_type == ComponentType.CLIENT
    ]
    server_components = [
        path for path, classification in classifications.items() if classification.component_type == ComponentType.SERVER
    ]

    route_rows: list[dict[str, Any]] = []
    for route in audit_result.routes:
        classification = classifications.get(route.component_file or "")
        route_rows.append(
            {
                "path": route.path,
                "component_name": Path(route.component_file).name if route.component_file else "unknown",
                "is_dynamic": route.is_dynamic,
                "client_hooks": classification.client_hooks_found if classification else [],
                "data_fetching": route.data_fetch_pattern.value,
            }
        )

    chunks = chunk_files(project_files.all_source_files)
    written_paths: list[Path] = []

    for chunk in chunks:
        source_files: list[dict[str, Any]] = []
        for file_path in chunk.files:
            source_files.append(
                {
                    "path": str(file_path),
                    "name": file_path.name,
                    "text": file_path.read_text(encoding="utf-8", errors="replace"),
                    "classification": classifications.get(str(file_path)),
                }
            )

        bundle_content = _render_bundle(
            env=environment,
            audit_result=audit_result,
            chunk=chunk,
            route_rows=route_rows,
            classifications=classifications,
            client_components=client_components,
            server_components=server_components,
            source_files=source_files,
            target_framework=target_framework,
        )

        if len(chunks) == 1:
            output_path = output_dir / "rsb-scaffold-bundle.md"
        else:
            output_path = output_dir / f"rsb-scaffold-bundle-part{chunk.part_number}.md"

        output_path.write_text(bundle_content, encoding="utf-8")
        written_paths.append(output_path)

    return written_paths


def _render_bundle(
    env: Environment,
    audit_result: AuditResult,
    chunk: Chunk,
    route_rows: list[dict[str, Any]],
    classifications: dict[str, ClassificationResult],
    client_components: list[str],
    server_components: list[str],
    source_files: list[dict[str, Any]],
    target_framework: str,
) -> str:
    system_instructions = env.get_template("system_instructions.md.j2").render(
        target_framework=target_framework,
        total_parts=chunk.total_parts,
        part_number=chunk.part_number,
    )
    project_context = env.get_template("project_context.md.j2").render(
        r=audit_result,
        route_rows=route_rows,
        client_components=client_components,
        server_components=server_components,
        classifications=classifications,
    )
    source_section = env.get_template("source_files.md.j2").render(
        chunk=chunk,
        source_files=source_files,
    )
    return f"{system_instructions}\n\n---\n\n{project_context}\n\n---\n\n{source_section}"
