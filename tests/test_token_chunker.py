"""Tests for token_chunker.py"""

from rsb.scaffold.token_chunker import chunk_files


def test_single_chunk_for_small_project(cra_basic_path) -> None:
    files = list((cra_basic_path / "src").rglob("*.jsx"))
    chunks = chunk_files(files, target_chars=1_000_000)
    assert len(chunks) == 1
    assert chunks[0].part_number == 1
    assert chunks[0].total_parts == 1


def test_multi_chunk_for_large_project(tmp_path) -> None:
    for index in range(5):
        file_path = tmp_path / f"component{index}.jsx"
        file_path.write_text("x" * 10_000, encoding="utf-8")

    chunks = chunk_files(list(tmp_path.glob("*.jsx")), target_chars=25_000)
    assert len(chunks) >= 2
    assert all(chunk.total_parts == len(chunks) for chunk in chunks)


def test_all_files_present_in_chunks(cra_basic_path) -> None:
    files = list((cra_basic_path / "src").rglob("*.jsx"))
    chunks = chunk_files(files, target_chars=10_000)
    all_files_in_chunks = set()
    for chunk in chunks:
        all_files_in_chunks.update(chunk.files)
    assert set(files) == all_files_in_chunks
