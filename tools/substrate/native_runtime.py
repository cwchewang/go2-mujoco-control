"""Sealed native execution inputs; build paths are provenance, never runtime inputs."""

from pathlib import Path
import os
import re
import shutil
import subprocess
from .integrity import digest, strict_json, write_new
from .model import dependency_manifest

SIDECAR = "controller-runtime-identity.json"


def _inside(root, name):
    path = (root / name).resolve(strict=True)
    if (
        not path.is_relative_to(root)
        or not path.is_file()
        or (root / name).is_symlink()
    ):
        raise ValueError("runtime dependency outside sealed bundle: " + name)
    return path


def package(binary, target, root, provenance):
    binary, target, root = (
        Path(binary).resolve(strict=True),
        Path(target),
        Path(root).resolve(),
    )
    target.mkdir()
    copied = target / binary.name
    shutil.copy2(binary, copied)
    models = {
        "task_xml": (
            root / ".substrate/mjpc/mjpc/tasks/quadruped/task_flat.xml",
            root / ".substrate/mjpc",
            "source",
        ),
        "canonical_xml": (
            root / "unitree_robots/go2/phase2_flat.xml",
            root,
            "canonical",
        ),
    }
    entries = {}
    for key, (scene, base, prefix) in models.items():
        closure = dependency_manifest(scene, base)
        for name, expected in closure["files"].items():
            dest = target / prefix / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / name, dest)
            if digest(dest) != expected:
                raise ValueError("model changed while sealing")
        entries[key] = (Path(prefix) / scene.relative_to(base)).as_posix()
    text = subprocess.check_output(["ldd", str(binary)], text=True)
    if "not found" in text:
        raise ValueError("unresolved native shared library")
    library_paths = {}
    loader = None
    for line in text.splitlines():
        match = re.search(r"(?:=>\s*)?(/[^\s]+)\s+\(", line)
        if not match:
            if "linux-vdso" in line or not line.strip():
                continue
            raise ValueError("unrecognized ldd dependency: " + line)
        path = Path(match.group(1)).resolve(strict=True)
        name = Path(match.group(1)).name
        dest = target / "lib" / name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(path, dest)
        library_paths[name] = "lib/" + name
        if name.startswith("ld-linux"):
            loader = "lib/" + name
    if loader is None:
        raise ValueError("ELF loader missing")
    # Preserve build provenance without invoking its historical paths during execution.
    write_new(target / "build-provenance.json", {"role": "archival_only", **provenance})
    files = {
        p.relative_to(target).as_posix(): digest(p)
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }
    value = {
        "schema": 1,
        "kind": "sealed-go2-native-runtime",
        "binary": binary.name,
        "binary_sha256": provenance["binary_sha256"],
        "workers": provenance["workers"],
        "loader": loader,
        "library_dir": "lib",
        "libraries": library_paths,
        **entries,
        "files": files,
    }
    write_new(target / SIDECAR, value)
    verify(copied, target / SIDECAR)
    return value


def verify(binary, identity_path):
    if Path(identity_path).is_symlink() or Path(binary).is_symlink():
        raise ValueError("runtime binary/identity must not be symlinked")
    identity_path = Path(identity_path).resolve(strict=True)
    root = identity_path.parent
    if identity_path.name != SIDECAR or identity_path.is_symlink():
        raise ValueError("invalid runtime identity sidecar")
    value = strict_json(identity_path.read_text())
    if value.get("schema") != 1 or value.get("kind") != "sealed-go2-native-runtime":
        raise ValueError("unsupported runtime identity")
    expected = value.get("files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("empty runtime closure")
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != identity_path
    }
    if actual != set(expected):
        raise ValueError("runtime file set differs")
    for name, sha in expected.items():
        if digest(_inside(root, name)) != sha:
            raise ValueError("runtime dependency hash mismatch: " + name)
    binary = Path(binary).resolve(strict=True)
    if (
        binary != _inside(root, value["binary"])
        or digest(binary) != value["binary_sha256"]
        or not os.access(binary, os.X_OK)
    ):
        raise ValueError("binary does not match sealed runtime identity")
    for key in ("task_xml", "canonical_xml", "loader"):
        _inside(root, value[key])
    for name in value["libraries"].values():
        _inside(root, name)
    return value


def argv(binary, identity_path):
    value = verify(binary, identity_path)
    root = Path(identity_path).resolve().parent
    return [
        str(root / value["loader"]),
        "--library-path",
        str(root / value["library_dir"]),
        str(Path(binary).resolve()),
    ], root / value["task_xml"]


def loaded_libraries(pid, identity_path):
    value = strict_json(Path(identity_path).read_text())
    root = Path(identity_path).resolve().parent
    paths = set()
    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1].startswith("/") and ".so" in fields[-1]:
            paths.add(Path(fields[-1]).resolve(strict=True))
    expected = {root / rel for rel in value["libraries"].values()}
    if not paths or not paths.issubset(expected):
        raise ValueError(
            "native process loaded a library outside its sealed closure: "
            + repr(paths - expected)
        )
    return {str(p.relative_to(root)): digest(p) for p in sorted(paths)}
