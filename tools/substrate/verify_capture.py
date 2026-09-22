"""Read-only replay of formal evidence; never integrates a plant or loads a policy."""

import argparse
import json
from pathlib import Path
import numpy as np
from .integrity import digest, strict_json, verify_bundle, verify_manifest
from .analyze_capture import analyze


def verify_capture(directory, prepared_directory):
    directory, prepared_directory = Path(directory), Path(prepared_directory)
    result = verify_manifest(directory)
    prepared = verify_bundle(prepared_directory)
    reference = strict_json((directory / "preparation-reference.json").read_text())
    if reference["manifest_sha256"] != digest(prepared_directory / "manifest.json") or result["head"] != prepared["head"]:
        raise ValueError("preparation reference mismatch")
    if result["status"] != "CAPTURE_COMPLETE" or result["scope"] != "formal_exploratory_capture":
        raise ValueError("capture incomplete or failed infrastructure boundary")
    from .launch import validate_authorization, validate_review
    prepared["prepared_manifest_sha256"] = digest(prepared_directory / "manifest.json")
    validate_authorization(strict_json((directory / "authorization.json").read_text()), prepared)
    validate_review(prepared["review"], prepared["head"])
    preflight = strict_json((directory / "preflight.json").read_text())
    if preflight.get("pass") is not True or preflight.get("git", {}).get("head") != prepared["head"]:
        raise ValueError("passing exact-head preflight missing")
    campaign_claim = strict_json((directory / "campaign-claim.json").read_text())
    if campaign_claim["head"] != prepared["head"] or campaign_claim["protocol_sha256"] != prepared["protocol_sha256"]:
        raise ValueError("campaign claim mismatch")
    protocol = strict_json((directory / "protocol.json").read_text())
    if protocol != strict_json((prepared_directory / "protocol.json").read_text()):
        raise ValueError("capture protocol mismatch")
    attempts = result["attempts"]
    if len(attempts) != protocol["max_attempts"]:
        raise ValueError("attempt budget mismatch")
    stopped = False
    recomputed = []
    reference_trace = None
    consumed = 0
    for index, item in enumerate(attempts, 1):
        if item["index"] != index:
            raise ValueError("attempt order mismatch")
        raw = directory / ("attempt_%02d.jsonl" % index)
        if stopped:
            if item["status"] != "NOT_RUN" or raw.exists():
                raise ValueError("attempt exists after campaign stop")
            recomputed.append({"index": index, "status": "NOT_RUN"})
            continue
        rows = [strict_json(line) for line in raw.read_text().splitlines()]
        if rows and rows[0]["action"] is not None:
            consumed += 1
            claim = strict_json((directory / ("attempt_%02d_claim.json" % index)).read_text())
            if claim["index"] != index or claim["head"] != prepared["head"] or claim["boundary"] != "first_post_handoff_state_control_sample":
                raise ValueError("attempt claim mismatch")
        value = analyze(rows, protocol, np.array(prepared["lower"]), np.array(prepared["upper"]), prepared["layout"], reference_trace)
        if reference_trace is None:
            reference_trace = value["trace_sha256"]
        original = strict_json((prepared_directory / "initial-state.json").read_text())
        if rows[0]["qpos"] != original["qpos"] or rows[0]["qvel"] != original["qvel"]:
            raise ValueError("initial state differs from prepared reset")
        saved = strict_json((directory / ("attempt_%02d_analysis.json" % index)).read_text())
        if any(saved[k] != v or item["analysis"][k] != v for k, v in value.items()) or item["status"] != value["verdict"]:
            raise ValueError("analyzer result differs")
        recomputed.append({"index":index,"status":value["verdict"]})
        stopped = value["verdict"] != "PASS"
    verdict = "PASS" if all(x["status"] == "PASS" for x in recomputed) else "FAIL"
    if verdict != result["capability_status"]:
        raise ValueError("campaign verdict mismatch")
    if type(result["live_runs"]) is not int or result["live_runs"] != consumed:
        raise ValueError("consumed attempt count mismatch")
    return {"status": "VERIFIED", "capability_status": verdict, "attempts": recomputed, "external_ledger_verified": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--prepared", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify_capture(args.directory, args.prepared)))


if __name__ == "__main__":
    main()
