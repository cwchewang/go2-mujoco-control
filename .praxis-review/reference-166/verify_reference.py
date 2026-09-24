"""Independent audit of #166 source evidence and sealed reference trace."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EXPECTED = "1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484"
FIELDS = ("qpos", "qvel", "target", "applied")

def read_json(path):
    return json.loads(path.read_text())

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def trajectory_digest(rows):
    h = hashlib.sha256()
    for row in rows:
        h.update(json.dumps({k: row[k] for k in FIELDS}, sort_keys=True, separators=(",", ":")).encode())
    return h.hexdigest()

def require(condition, message):
    if not condition:
        raise AssertionError(message)

capture = ROOT / "capture"
manifest = read_json(capture / "manifest.json")
actual_paths = {p.relative_to(capture).as_posix() for p in capture.rglob("*") if p.is_file() and p.name != "manifest.json"}
require(actual_paths == set(manifest), "capture file set differs from its manifest")
for name, expected_sha in manifest.items():
    require(sha256(capture / name) == expected_sha, f"capture manifest mismatch: {name}")
package_index = read_json(ROOT / "source-package-index.json")
indexed_files = {entry["path"]: entry for entry in package_index["files"]}
for name in manifest:
    entry = indexed_files[f"formal/capture/{name}"]
    require(sha256(capture / name) == entry["sha256"], f"source package index mismatch: {name}")
    require((capture / name).stat().st_size == entry["size"], f"source package size mismatch: {name}")
require(
    sha256(ROOT / "formal-RESULTS.md") == indexed_files["formal/RESULTS.md"]["sha256"],
    "source RESULTS.md package index mismatch",
)

protocol = read_json(capture / "protocol.json")
require(protocol["schema"] == 1, "unexpected historical protocol schema")
require(protocol["id"] == "rl-shared-transfer-combination-v1", "unexpected #166 protocol")
require(protocol["source_identity"]["commit"] == "30e74dc507bec7a642a8c98be26081f2c6f0822d", "source commit mismatch")
require(protocol["source_identity"]["checkpoint_sha256"] == "9d9ad783a1017b6eced5984eb95279cc5b36db8cc84d21e646f46ba2a8023d9d", "checkpoint mismatch")
first, repeat = protocol["cases"]
for case in (first, repeat):
    require(case["scene"] == "unitree_robots/go2/phase2_flat.xml", "scene mismatch")
    require(case["adapter"] is True and case["reset"] == "shared_home", "deployment mismatch")
    require(case["first_inference_tick"] == 10, "startup mismatch")
    require(case["commands"] == [[0, 1.0]], "command mismatch")
    require(case["horizon_ticks"] == 6000, "horizon mismatch")
require(repeat["repeat_of"] == first["id"], "repeat case linkage mismatch")

qualification = read_json(ROOT / "qualification-admission.json")
flat = qualification["models"]["phase2_flat"]
closure = flat["closure"]["files"]
for filename in ("go2.xml", "phase2_flat.xml"):
    relative = f"unitree_robots/go2/{filename}"
    require(sha256(ROOT / filename) == closure[relative], f"shared model source hash mismatch: {filename}")
xml = (ROOT / "phase2_flat.xml").read_text()
require('file="go2.xml"' in xml, "flat scene does not include shared Go2 model")

summary = read_json(ROOT / "committed-formal-summary.json")
require(summary["issue_number"] == 166 and summary["head"] == "9e82e56ac2a5db63d7834e86ce402d542bf10ae8", "formal summary identity mismatch")
require(summary["offline_verification"]["status"] == "VERIFIED" and summary["offline_verification"]["physics_steps"] == 0, "offline verification mismatch")
require(summary["capture"]["attempts_consumed_by_external_ledger"] == 2, "attempt ledger mismatch")
require("1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484" in (ROOT / "committed-results.md").read_text(), "committed RESULTS.md omits digest")
require(read_json(ROOT / "source-package-manifest.json")["result_commit"] == "6f67769851aaffed1c1826d138293e52265dbba7", "source closeout commit mismatch")

case_reports = {}
loaded = {}
for name in ("combined_1", "combined_2"):
    rows = [json.loads(line) for line in (capture / f"{name}.jsonl").read_text().splitlines()]
    require(len(rows) == 6001 and [r["tick"] for r in rows] == list(range(6001)), f"frame sequence mismatch: {name}")
    require(all(len(r["qpos"]) == 19 and len(r["qvel"]) == 18 and len(r["target"]) == 12 for r in rows), f"state/action dimensions mismatch: {name}")
    require(all(len(r["applied"]) == 12 for r in rows[:-1]) and rows[-1]["applied"] is None, f"applied control shape mismatch: {name}")
    actual = trajectory_digest(rows)
    analysis = read_json(capture / f"{name}_analysis.json")
    require(actual == EXPECTED == analysis["trace_sha256"], f"authoritative digest mismatch: {name}")
    require(analysis["verdict"] == "PASS" and analysis["steps"] == 6000, f"capture outcome mismatch: {name}")
    loaded[name] = rows
    case_reports[name] = {"rows": len(rows), "recomputed_trace_sha256": actual, "analysis_verdict": analysis["verdict"]}
for field in FIELDS:
    require(all(a[field] == b[field] for a, b in zip(loaded["combined_1"], loaded["combined_2"])), f"repeat stream differs: {field}")

capture_admission = read_json(capture / "admission.json")
claims = [read_json(ROOT / "ledger" / f"{name}.json") for name in ("combined_1", "combined_2")]
require(capture_admission["status"] == "CAPTURE_COMPLETE" and capture_admission["live_runs"] == 2, "capture admission mismatch")
require([claim["case"] for claim in claims] == ["combined_1", "combined_2"], "authoritative ledger cases mismatch")

result = {
    "status": "VERIFIED",
    "expected_sha256": EXPECTED,
    "trace_canonicalization": "historical schema-1 SHA-256 over concatenated canonical JSON objects containing only qpos, qvel, target, applied; sort_keys=true; separators=(',', ':')",
    "condition": {"model": "shared Go2 phase2_flat", "scene": first["scene"], "reset": first["reset"], "first_inference_tick": first["first_inference_tick"], "adapter": first["adapter"], "command": first["commands"][0][1]},
    "model": {"physical_sha256": flat["physical_sha256"], "go2_xml_sha256": closure["unitree_robots/go2/go2.xml"], "phase2_flat_xml_sha256": closure["unitree_robots/go2/phase2_flat.xml"]},
    "cases": case_reports,
    "repeat_streams_identical": list(FIELDS),
    "formal_verification": summary["offline_verification"],
    "ledger_attempts": [claim["case"] for claim in claims],
}
(ROOT / "reference-verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, indent=2, sort_keys=True))
