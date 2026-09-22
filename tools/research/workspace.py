"""Generate navigation and archive inventory; never retire branches or raw data."""

import argparse
import json
from pathlib import Path
import subprocess
from tools.substrate.integrity import digest, experiment_lock

ROOT = Path(__file__).resolve().parents[2]


def render_current(value):
    return f"""# Go2 current research frontier

Generated from `docs/research/current.json`; edit that source and regenerate.

`main` remains the stable code line and long-term route.

## Active research frontier

Branch: `{value["branch"]}`.
Task: [{value["title"]}]({value["task"]}).
Closeout: [{value["title"]} results]({value["result"]}).
Stage: {value["stage"]}.
Scientific status: {value["scientific_status"]}.
Last live HEAD: `{value["last_live_head"]}`.
Next: {value["next"]}.

Read [PROJECT_RECORD](docs/PROJECT_RECORD.md) for scientific conclusions and
[TOPIC_AUDIT](docs/TOPIC_AUDIT.md) for research direction. The
[SOP](docs/research/SOP.md) governs execution. Navigation is not start authorization.
"""


def inventory(workspace):
    evidence = workspace / "archive/evidence"
    archives = []
    for path in sorted(evidence.rglob("*.tar.gz")):
        if path.is_symlink():
            raise ValueError("archive symlink unsupported")
        actual = digest(path)
        sidecar = path.parent / "SHA256SUMS"
        matches = []
        if sidecar.exists():
            for line in sidecar.read_text().splitlines():
                fields = line.split(maxsplit=1)
                if len(fields) == 2 and fields[1].lstrip(" *") == path.name:
                    matches.append(fields[0])
        if matches and matches != [actual]:
            raise ValueError("archive checksum mismatch: " + str(path))
        archives.append(
            {
                "path": path.relative_to(evidence).as_posix(),
                "sha256": actual,
                "bytes": path.stat().st_size,
                "prior_checksum_verified": bool(matches),
            }
        )
    branches = subprocess.check_output(
        ["git", "ls-remote", "--heads", "origin"], cwd=ROOT, text=True
    )
    active = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    branch_rows = []
    for line in branches.splitlines():
        sha, ref = line.split()
        name = ref.removeprefix("refs/heads/")
        branch_rows.append(
            {
                "branch": name,
                "head": sha,
                "disposition": "active"
                if name in ("main", active)
                else "retained_pending_owner_review",
            }
        )
    trees = subprocess.check_output(
        ["git", "worktree", "list", "--porcelain"], cwd=ROOT, text=True
    )
    worktrees = []
    for block in trees.strip().split("\n\n"):
        values = dict(
            line.split(" ", 1) if " " in line else (line, True)
            for line in block.splitlines()
        )
        values["disposition"] = (
            "active"
            if values.get("worktree") == str(ROOT)
            else "retained_reference_or_pending_review"
        )
        worktrees.append(values)
    return {"archives": archives, "branches": branch_rows, "worktrees": worktrees}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    p.add_argument("--workspace", type=Path)
    args = p.parse_args()
    value = json.loads((ROOT / "docs/research/current.json").read_text())
    expected = render_current(value)
    if args.check:
        if (ROOT / "CURRENT.md").read_text() != expected:
            raise ValueError(
                "CURRENT.md drifted; run python -m tools.research.workspace"
            )
        return
    (ROOT / "CURRENT.md").write_text(expected)
    if args.workspace:
        workspace = args.workspace.resolve()
        if workspace != ROOT.parent:
            raise ValueError("workspace must be the repository parent")
        with experiment_lock():
            for source, destination in (
                ("workspace-AGENTS.md", "AGENTS.md"),
                ("WORKSPACE_STANDARD.md", "WORKSPACE_STANDARD.md"),
            ):
                (workspace / destination).write_bytes(
                    (ROOT / "docs/governance" / source).read_bytes()
                )
            data = inventory(workspace)
            path = workspace / "archive/evidence/CATALOG.json"
            path.write_text(json.dumps(data, indent=2) + "\n")
            (path.parent / "SHA256SUMS").write_text(
                "".join(f"{x['sha256']}  {x['path']}\n" for x in data["archives"])
            )
            index = workspace / "archive/INDEX.md"
            # Preserve human historical notes. Only replace our generated block.
            old = index.read_text() if index.exists() else "# Archive index\n"
            marker = "\n<!-- GENERATED CATALOG -->\n"
            index.write_text(
                old.split(marker)[0]
                + marker
                + "Authoritative generated catalog: `evidence/CATALOG.json`.\n"
                + "\n".join(
                    f"- `{x['path']}` — SHA256 `{x['sha256']}`"
                    for x in data["archives"]
                )
                + "\n"
            )
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip()
            dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=ROOT, text=True
                ).strip()
            )
            (workspace / "START_HERE.md").write_text(
                f"# Go2 handoff\n\nGenerated; verify Git again on entry.\nRepository: `{ROOT}`.\nObserved HEAD: `{head}`; dirty: `{dirty}`.\n\n"
                + expected
                + "\nArchive and retained branch/worktree inventory: `archive/evidence/CATALOG.json`.\nNo raw data or branches were removed by this generator.\n"
            )
            print(json.dumps({key: len(items) for key, items in data.items()}))


if __name__ == "__main__":
    main()
