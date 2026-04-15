"""
token_chunker.py - Splits large codebases into LLM-safe chunks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_CHUNK_TARGET_CHARS = 320_000

_PRIORITY_NAMES = {
    "index.jsx": 100,
    "index.tsx": 100,
    "index.js": 100,
    "main.jsx": 100,
    "main.tsx": 100,
    "App.jsx": 95,
    "App.tsx": 95,
    "App.js": 95,
    "routes.jsx": 90,
    "routes.tsx": 90,
    "Router.jsx": 90,
    "Home.jsx": 80,
    "Home.tsx": 80,
    "About.jsx": 70,
    "About.tsx": 70,
    "Product.jsx": 70,
    "Product.tsx": 70,
}


@dataclass
class Chunk:
    part_number: int
    total_parts: int
    files: list[Path] = field(default_factory=list)
    estimated_chars: int = 0


def chunk_files(files: list[Path], target_chars: int = DEFAULT_CHUNK_TARGET_CHARS) -> list[Chunk]:
    """Split source files into chunks sized for large-context migration prompts."""

    def priority(file_path: Path) -> tuple[int, str]:
        return (_PRIORITY_NAMES.get(file_path.name, 50), str(file_path))

    sorted_files = sorted(files, key=priority, reverse=True)
    file_sizes: dict[Path, int] = {}
    for file_path in sorted_files:
        try:
            file_sizes[file_path] = len(file_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            file_sizes[file_path] = 0

    total_chars = sum(file_sizes.values())
    if total_chars <= target_chars:
        return [Chunk(part_number=1, total_parts=1, files=sorted_files, estimated_chars=total_chars)]

    chunks: list[Chunk] = []
    current_files: list[Path] = []
    current_chars = 0

    for file_path in sorted_files:
        file_size = file_sizes[file_path]
        if current_files and current_chars + file_size > target_chars:
            chunks.append(
                Chunk(
                    part_number=len(chunks) + 1,
                    total_parts=0,
                    files=current_files,
                    estimated_chars=current_chars,
                )
            )
            current_files = [file_path]
            current_chars = file_size
        else:
            current_files.append(file_path)
            current_chars += file_size

    if current_files:
        chunks.append(
            Chunk(
                part_number=len(chunks) + 1,
                total_parts=0,
                files=current_files,
                estimated_chars=current_chars,
            )
        )

    total_parts = len(chunks)
    for chunk in chunks:
        chunk.total_parts = total_parts

    return chunks
