"""List selectable model plugins and whether their optional runtime exists."""

from pathlib import Path


def main():
    root = Path(__file__).resolve().parent / "models"
    excluded = {"__init__", "model_template"}
    for path in sorted(root.glob("*.py")):
        if path.stem in excluded:
            continue
        requirement = "torch" if path.stem.startswith("torch_") else "sklearn"
        try:
            __import__(requirement)
            status = "available"
        except Exception:
            status = "missing dependency: " + requirement
        print("{}: {}".format(path.stem, status))


if __name__ == "__main__":
    main()
