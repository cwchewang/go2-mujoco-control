"""Explicit, source-locked dependency installation; never launches a simulation."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads(Path(__file__).with_name("sources.lock.json").read_text())


def run(*args):
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)


def fetch(url, path, sha256=None, git_blob=None):
    def valid(p):
        data = p.read_bytes()
        return (not sha256 or hashlib.sha256(data).hexdigest() == sha256) and (
            not git_blob
            or hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data
            ).hexdigest()
            == git_blob
        )

    if path.exists() and valid(path):
        return
    temporary = path.with_suffix(path.suffix + ".download")
    with (
        urllib.request.urlopen(url, timeout=300) as response,
        temporary.open("wb") as stream,
    ):
        while block := response.read(1024 * 1024):
            stream.write(block)
    if not valid(temporary):
        raise ValueError("download identity mismatch: " + url)
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--install",
        action="store_true",
        help="explicit network/dependency installation",
    )
    p.add_argument(
        "--build",
        action="store_true",
        help="build the offline MJPC admission executable",
    )
    args = p.parse_args()
    import fcntl

    # Serialize source/dependency mutations as well as compilation against runs.
    lock = open("/tmp/go2_mujoco_experiment.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    base = ROOT / ".substrate"
    if args.install:
        base.mkdir(exist_ok=True)
        env = base / "venv"
        if not (env / "bin/python").exists():
            run(sys.executable, "-m", "venv", env)
        run(env / "bin/python", "-m", "pip", "install", "numpy==2.2.6", "mujoco==3.3.6")
        run(
            env / "bin/python",
            "-m",
            "pip",
            "install",
            "--index-url",
            "https://download.pytorch.org/whl/cpu",
            "torch==2.6.0",
        )
        source = base / "mjpc"
        if not source.exists():
            run(
                "git", "clone", "--filter=blob:none", LOCK["mjpc"]["repository"], source
            )
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=source):
            raise ValueError("dependency checkout is dirty")
        run("git", "-C", source, "fetch", "origin", LOCK["mjpc"]["commit"])
        run("git", "-C", source, "checkout", "--detach", LOCK["mjpc"]["commit"])
        rl = base / "rl"
        rl.mkdir(exist_ok=True)
        item = LOCK["rl"]
        fetch(
            "https://raw.githubusercontent.com/wty-yy/go2_rl_gym/"
            + item["commit"]
            + "/"
            + item["checkpoint"],
            rl / "policy.pt",
            item["sha256"],
            item["git_blob_sha1"],
        )
    if args.build:
        run(
            "cmake",
            "-S",
            "tools/substrate/native",
            "-B",
            base / "headless-build",
            "-G",
            "Ninja",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DMJPC_SOURCE_DIR=" + str(base / "mjpc"),
        )
        run(
            "cmake",
            "--build",
            base / "headless-build",
            "--target",
            "go2_mjpc_admit",
            "-j",
            "4",
        )
    if not args.install and not args.build:
        p.print_help()


if __name__ == "__main__":
    main()
