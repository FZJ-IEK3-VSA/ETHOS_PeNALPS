"""Execute all storage test case generate.ipynb notebooks.

Usage:
    python test/generate/storage/generate_all.py
"""

import subprocess
import sys
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent


def generate_all() -> None:
    notebooks = sorted(_BASE_DIR.glob("*/generate.ipynb"))
    if not notebooks:
        print("No generate.ipynb notebooks found.")
        sys.exit(1)

    failed: list[Path] = []
    for notebook in notebooks:
        group_name = notebook.parent.name
        print(f"Running {group_name}/generate.ipynb ... ", end="", flush=True)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "jupyter",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                str(notebook),
                "--output",
                str(notebook),
            ],
            capture_output=True,
            text=True,
            cwd=str(notebook.parent),
        )
        if result.returncode != 0:
            print("FAILED")
            print(result.stderr)
            failed.append(notebook)
        else:
            print("ok")

    print(f"\n{len(notebooks) - len(failed)}/{len(notebooks)} notebooks succeeded.")
    if failed:
        print("Failed notebooks:")
        for nb in failed:
            print(f"  {nb}")
        sys.exit(1)


if __name__ == "__main__":
    generate_all()
