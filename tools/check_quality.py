"""Read-only checks of tracked source. Never import runners or scan raw output.

Use --style with the separate pinned development environment. Default mode is
standard-library-only, so native qualification needs no extra runtime packages.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import subprocess
import sys

from tools.check_repo_hygiene import FORBIDDEN_TRACKED_PREFIXES, tracked_files

ROOT = Path(__file__).resolve().parents[1]
FROZEN_PREFIXES = (
    "docs/upstream/",
    "docs/research/evidence/",
    "docs/validation/",
    "example/cpp/experiments/",
)
MAINTAINED_PYTHON_PREFIXES = ("tools/", "example/cpp/tools/")


def source_paths(root):
    """Select syntax inputs by Git identity, not recursive filesystem discovery."""
    return [
        name
        for name in tracked_files(root)
        if not name.startswith(FROZEN_PREFIXES + FORBIDDEN_TRACKED_PREFIXES)
        and (Path(name).suffix in (".py", ".sh") or Path(name).name == "go2sim")
    ]


def check_syntax(root, names):
    errors = []
    for name in names:
        path = root / name
        if path.suffix == ".py":
            try:
                # Parsing compiles nothing to disk and executes no top-level code.
                ast.parse(path.read_bytes(), filename=name)
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f"{name}: {exc}")
        else:
            result = subprocess.run(
                ["bash", "-n", str(path)], capture_output=True, text=True, timeout=30
            )
            if result.returncode:
                errors.append(f"{name}: {result.stderr.strip()}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--style",
        action="store_true",
        help="also enforce pinned Ruff lint and formatting",
    )
    args = parser.parse_args()
    names = source_paths(ROOT)
    errors = check_syntax(ROOT, names)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    subprocess.run(
        [sys.executable, "tools/check_repo_hygiene.py"], cwd=ROOT, check=True
    )
    if args.style:
        maintained = [
            name
            for name in names
            if name.endswith(".py") and name.startswith(MAINTAINED_PYTHON_PREFIXES)
        ]
        for argv in (["check"], ["format", "--check"]):
            subprocess.run(
                [sys.executable, "-m", "ruff", *argv, *maintained], cwd=ROOT, check=True
            )
    print(
        f"Quality checks passed for {len(names)} tracked source files; raw evidence and dependencies excluded."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
