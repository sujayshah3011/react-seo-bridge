"""Shared pytest fixtures for react-seo-bridge tests."""

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def cra_basic_path() -> Path:
    return FIXTURES_DIR / "cra_basic"


@pytest.fixture
def vite_path() -> Path:
    return FIXTURES_DIR / "vite_with_router"
