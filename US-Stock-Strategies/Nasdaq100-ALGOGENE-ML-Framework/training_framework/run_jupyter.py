"""ALGOGENE Jupyter entrypoint: probe, debug, or train the frozen model bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from AlgoAPI.AlgoAPIUtil import getHistoricalBar

from contracts import TrainingConfig
from core import (atomic_json, build_panel, environment_probe, sha256_path,
                  summarize_predictions, train_walk_forward)
from fundamentals import load_point_in_time_fundamentals


ROOT = Path(__file__).resolve().parent
DEFAULT_CLOUD_ROOT = Path("/lib/nasdaq100_dl_runs")
DEFAULT_CACHE_ROOT = Path("/lib/nasdaq100_dl_cache")


def read_symbols(path):
    return [line.strip().upper() for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--pool", default=str(ROOT / "nasdaq100_symbols.txt"))
    parser.add_argument("--cloud-root", default=str(DEFAULT_CLOUD_ROOT))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE_ROOT))
    parser.add_argument("--fundamentals", default="",
                        help="optional point-in-time CSV/CSV.GZ/Parquet override")
    parser.add_argument("--mode", choices=("probe", "debug", "train"), default="",
                        help="override config mode without editing the file")
    args = parser.parse_args(argv)

    config = TrainingConfig.load(args.config)
    if args.mode:
        config.payload["mode"] = args.mode
    if config.payload.get("job_name", "auto") == "auto":
        model_label = config.payload.get("model_name", "custom")
        identity = {
            "model": model_label,
            "model_params": config.payload.get("model_params", {}),
            "dataset_columns": config.payload.get("dataset_columns", ["*"]),
        }
        suffix = hashlib.sha256(json.dumps(
            identity, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()[:10]
        config.payload["job_name"] = "nasdaq100_{}_{}".format(model_label, suffix)
    cloud_root = Path(args.cloud_root)
    output = cloud_root / config.job_name
    output.mkdir(parents=True, exist_ok=True)
    probe = environment_probe(getHistoricalBar)
    atomic_json(output / "environment.json", probe)
    print(json.dumps(probe, ensure_ascii=False, indent=2), flush=True)
    if config.mode == "probe":
        print("PROBE_COMPLETE", output, flush=True)
        return 0

    fundamental_config = dict(config.payload.get("fundamentals", {}))
    fundamentals = None
    fundamental_source = args.fundamentals or fundamental_config.get("path", "")
    if fundamental_config.get("enabled", False):
        try:
            fundamentals = load_point_in_time_fundamentals(
                fundamental_source,
                availability_lag_hours=float(
                    fundamental_config.get("availability_lag_hours", 24)),
            )
            print("FUNDAMENTALS_LOADED", fundamental_source, "rows", len(fundamentals),
                  flush=True)
        except FileNotFoundError:
            if fundamental_config.get("required", False):
                raise
            fundamental_config["enabled"] = False
            print("FUNDAMENTALS_DISABLED missing optional file", fundamental_source,
                  flush=True)
    config.payload["fundamentals"] = fundamental_config

    symbols = read_symbols(args.pool)
    platform_limit = int(config.payload.get("platform_subscription_limit", 100))
    if len(symbols) > platform_limit:
        raise ValueError("universe has {} symbols; platform limit is {}".format(
            len(symbols), platform_limit))
    if len(symbols) != len(set(symbols)):
        raise ValueError("universe contains duplicate symbols")
    if config.mode == "debug":
        symbols = symbols[:int(config.debug_symbols)]
        requested_end = datetime.fromisoformat(config.end)
        config.payload["start"] = max(
            datetime.fromisoformat(config.start),
            requested_end - timedelta(days=int(config.debug_calendar_days)),
        ).date().isoformat()

    status_path = output / "status.json"
    atomic_json(status_path, {"state": "building_dataset", "symbols": len(symbols),
                              "started_at_utc": datetime.utcnow().isoformat() + "Z"})
    try:
        panel, feature_columns = build_panel(
            getHistoricalBar, symbols, config, args.cache_root,
            progress=lambda message: print(message, flush=True),
            fundamentals=fundamentals,
            fundamental_config=fundamental_config,
        )
        panel.to_csv(output / "training_panel.csv.gz", index=False, compression="gzip")
        fundamentals_file = None
        if fundamental_config.get("enabled", False) and fundamentals is not None:
            fundamentals_file = "fundamentals_pti.csv.gz"
            fundamentals.to_csv(output / fundamentals_file, index=False,
                                compression="gzip", date_format="%Y-%m-%d")
        atomic_json(status_path, {"state": "training", "rows": len(panel),
                                  "features": len(feature_columns)})
        predictions, windows, model_path = train_walk_forward(
            panel, feature_columns, config, output)
        manifest = {
            "format_version": 3,
            "job_name": config.job_name,
            "created_at_utc": datetime.utcnow().isoformat() + "Z",
            "mode": config.mode,
            "data_start": config.start,
            "data_end": config.end,
            "interval": config.interval,
            "timezone": config.timezone,
            "regular_session_only": bool(config.regular_session_only),
            "label_definition": "signal at D close; enter D+1 first minute; exit D+2 first minute",
            "jupyter_execution_model": "whole-share equal-budget platform-like simulator",
            "universe_size": len(symbols),
            "universe_file": "nasdaq100_symbols.txt",
            "universe_policy": config.payload.get("universe_policy"),
            "survivorship_warning": "Current 2026-09-29 Nasdaq-100 snapshot is not point-in-time for 2020 history.",
            "model_entrypoint": config.model_entrypoint,
            "model_file": model_path.name,
            "model_sha256": sha256_path(model_path),
            "feature_schema": "feature_schema.json",
            "feature_schema_sha256": sha256_path(output / "feature_schema.json"),
            "factor_code_sha256": sha256_path(ROOT / "core.py"),
            "online_code_sha256": sha256_path(ROOT / "online.py"),
            "fundamentals_code_sha256": sha256_path(ROOT / "fundamentals.py"),
            "golden_sample": "golden_sample.npz",
            "fundamentals_file": fundamentals_file,
            "fundamentals_sha256": (
                sha256_path(output / fundamentals_file) if fundamentals_file else None),
            "windows": len(windows),
            "metrics": summarize_predictions(predictions, config),
            "config": config.payload,
        }
        atomic_json(output / "manifest.json", manifest)
        shutil.copy2(args.pool, output / "nasdaq100_symbols.txt")
        atomic_json(cloud_root / "latest.json", {
            "job_name": config.job_name,
            "bundle": config.job_name,
            "manifest": str(output / "manifest.json"),
            "completed_at_utc": datetime.utcnow().isoformat() + "Z",
        })
        atomic_json(status_path, {"state": "complete", "manifest": str(output / "manifest.json"),
                                  "metrics": manifest["metrics"]})
        print("TRAINING_COMPLETE", output, flush=True)
        return 0
    except Exception as exc:
        atomic_json(status_path, {"state": "failed", "error": type(exc).__name__ + ": " + str(exc),
                                  "failed_at_utc": datetime.utcnow().isoformat() + "Z"})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
