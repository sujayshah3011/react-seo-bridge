"""react-seo-bridge: Static SEO auditor for React CSR applications."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any


__version__ = "0.1.0"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT_PATH = _PROJECT_ROOT / "pyproject.toml"


def _load_pyproject() -> dict[str, Any]:
    with _PYPROJECT_PATH.open("rb") as handle:
        return tomllib.load(handle)


def _project_name() -> str:
    data = _load_pyproject()
    return str(data["project"]["name"])


def _entry_points_text() -> str:
    data = _load_pyproject()
    project = data.get("project", {})
    sections: list[tuple[str, dict[str, str]]] = []

    scripts = project.get("scripts", {})
    if scripts:
        sections.append(("console_scripts", {str(k): str(v) for k, v in scripts.items()}))

    gui_scripts = project.get("gui-scripts", {})
    if gui_scripts:
        sections.append(("gui_scripts", {str(k): str(v) for k, v in gui_scripts.items()}))

    entry_points = project.get("entry-points", {})
    for group, entries in entry_points.items():
        sections.append((str(group), {str(k): str(v) for k, v in dict(entries).items()}))

    lines: list[str] = []
    for index, (group, entries) in enumerate(sections):
        if index:
            lines.append("")
        lines.append(f"[{group}]")
        for name, target in entries.items():
            lines.append(f"{name} = {target}")
    return "\n".join(lines) + ("\n" if lines else "")


def _ensure_source_egg_info() -> Path:
    project_name = _project_name()
    safe_name = re.sub(r"[^A-Za-z0-9.]+", "-", project_name)
    egg_info_name = safe_name.replace("-", "_") + ".egg-info"
    egg_info_dir = _PROJECT_ROOT / egg_info_name
    egg_info_dir.mkdir(exist_ok=True)

    entry_points_path = egg_info_dir / "entry_points.txt"
    if not entry_points_path.exists():
        entry_points_path.write_text(_entry_points_text(), encoding="utf-8")

    return egg_info_dir


def get_requires_for_build_wheel(config_settings: dict[str, Any] | None = None) -> list[str]:
    from setuptools.build_meta import get_requires_for_build_wheel as _impl

    return _impl(config_settings)


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from setuptools.build_meta import build_wheel as _impl

    return _impl(wheel_directory, config_settings, metadata_directory)


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    from setuptools.build_meta import prepare_metadata_for_build_wheel as _impl

    return _impl(metadata_directory, config_settings)


def build_sdist(
    sdist_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    from setuptools.build_meta import build_sdist as _impl

    return _impl(sdist_directory, config_settings)


def get_requires_for_build_editable(
    config_settings: dict[str, Any] | None = None,
) -> list[str]:
    from setuptools.build_meta import get_requires_for_build_editable as _impl

    _ensure_source_egg_info()
    return _impl(config_settings)


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict[str, Any] | None = None,
) -> str:
    from setuptools.build_meta import prepare_metadata_for_build_editable as _impl

    _ensure_source_egg_info()
    return _impl(metadata_directory, config_settings)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    from setuptools.build_meta import build_editable as _impl

    _ensure_source_egg_info()
    return _impl(wheel_directory, config_settings, metadata_directory)
