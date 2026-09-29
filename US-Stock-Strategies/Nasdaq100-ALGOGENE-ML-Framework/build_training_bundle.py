"""Build the folder and ZIP that teammates upload to ALGOGENE /lib."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "training_framework"
DIST = ROOT / "dist" / "algogene_nasdaq100_dl"
PACKAGE = DIST / "nasdaq100_dl"


def main():
    expected_parent = (ROOT / "dist").resolve()
    if DIST.exists():
        if DIST.resolve().parent != expected_parent:
            raise RuntimeError("refusing to replace unexpected path")
        shutil.rmtree(DIST)
    PACKAGE.mkdir(parents=True)
    ignored = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "outputs")
    for item in SOURCE.iterdir():
        if item.name in {"__pycache__", "tests", "outputs"}:
            continue
        destination = PACKAGE / item.name
        if item.is_dir():
            shutil.copytree(item, destination, ignore=ignored)
        else:
            shutil.copy2(item, destination)
    shutil.copy2(ROOT / "nasdaq100_symbols.txt", PACKAGE / "nasdaq100_symbols.txt")
    shutil.copy2(ROOT / "nasdaq100_metadata.json", PACKAGE / "nasdaq100_metadata.json")
    shutil.copy2(ROOT / "nasdaq100_missing_local_data.txt",
                 PACKAGE / "nasdaq100_missing_local_data.txt")
    shutil.copy2(PACKAGE / "config.example.json", PACKAGE / "config.json")
    shutil.copy2(PACKAGE / "algogene_submission.py", DIST / "algogene_submission.py")
    shutil.copy2(SOURCE / "README.md", DIST / "README.md")
    archive = shutil.make_archive(str(DIST), "zip", root_dir=DIST.parent, base_dir=DIST.name)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
