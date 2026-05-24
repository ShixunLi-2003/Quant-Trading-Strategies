"""Resolve repository-level file paths while keeping `Code/` as a self-contained package."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_folder_by_root(root: str | Path, *paths: str | Path, auto_create: bool = True) -> str:
    """Return an absolute directory path under a specified root."""
    full_path = Path(root).joinpath(*map(str, paths))
    if auto_create:
        full_path.mkdir(parents=True, exist_ok=True)
    return str(full_path)


def get_folder_path(*paths: str | Path, auto_create: bool = True, path_type: bool = False):
    """Return an absolute directory path under the repository root."""
    folder = Path(get_folder_by_root(PROJECT_ROOT, *paths, auto_create=auto_create))
    return folder if path_type else str(folder)


def get_file_path(*paths: str | Path, auto_create: bool = True, as_path_type: bool = False):
    """Return an absolute file path under the repository root."""
    parent = Path(get_folder_path(*paths[:-1], auto_create=auto_create, path_type=True))
    file_path = parent / str(paths[-1])
    return file_path if as_path_type else str(file_path)
