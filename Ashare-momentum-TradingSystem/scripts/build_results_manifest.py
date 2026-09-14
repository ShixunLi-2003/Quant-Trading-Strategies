from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def classify(path: Path) -> str:
    name = path.name.lower()
    if "minute_momentum" in name or "factor_" in name:
        return "factor_research"
    if "strict" in name or "rolling" in name:
        return "robustness"
    if "scheduled" in name or "exit_time" in name:
        return "execution"
    if "model" in name or "forest" in name or "neural" in name:
        return "model_comparison"
    if "etf" in name:
        return "risk_overlay"
    if "tuning" in name:
        return "parameter_selection"
    return "summary"


def main() -> None:
    rows = []
    for path in sorted(RESULTS.rglob("*")):
        if not path.is_file() or path.name.startswith("README") or path.name == "manifest.csv":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "category": classify(path),
                "bytes": path.stat().st_size,
                "sha256": digest,
            }
        )
    pd.DataFrame(rows).to_csv(RESULTS / "manifest.csv", index=False)


if __name__ == "__main__":
    main()

