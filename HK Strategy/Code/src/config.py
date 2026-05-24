from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    data.setdefault("_meta", {})
    data["_meta"]["config_path"] = str(config_path)
    data["_meta"]["base_dir"] = str(config_path.parent)
    return data


def resolve_path(base_dir: str | Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path(base_dir) / path).resolve()
    return path


def load_project_and_job_config(job_config_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    job_config = load_json_config(job_config_path)
    project_ref = job_config.get("project_config", "../project.json")
    project_path = resolve_path(job_config["_meta"]["base_dir"], project_ref)
    project_config = load_json_config(project_path)
    return project_config, job_config


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def to_serializable(data: Any) -> Any:
    if isinstance(data, dict):
        return {str(key): to_serializable(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [to_serializable(item) for item in data]
    if hasattr(data, "item"):
        try:
            return data.item()
        except Exception:
            return str(data)
    return data


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(to_serializable(data), file, ensure_ascii=False, indent=2)
    return output_path
