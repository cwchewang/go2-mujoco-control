"""Materialize the pinned public deployment assets without replacing local files."""

import hashlib
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

from .integrity import digest, strict_json

ROOT = Path(__file__).resolve().parents[2]


def main():
    locked = strict_json((ROOT / "tools/substrate/rl_reference.lock.json").read_text())
    directory = ROOT / ".substrate/upstream-go2-30e74dc5"
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in locked["files"].items():
        dest = (directory / name).resolve()
        if not dest.is_relative_to(directory.resolve()):
            raise ValueError("reference path escapes destination")
        if dest.exists():
            if digest(dest) != expected:
                raise ValueError("existing reference differs: " + name)
            continue
        url = f"https://raw.githubusercontent.com/{locked['repository']}/{locked['commit']}/{name}"
        with urlopen(url, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("download hash mismatch: " + name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dest.parent) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            # Atomic no-replace publication, including a concurrent downloader.
            os.link(temporary.name, dest)
    print(f"Verified {len(locked['files'])} source files at {locked['commit']}")


if __name__ == "__main__":
    main()
