"""Recompute the #166 schema-1 qpos/qvel/target/applied digest from raw rows."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = "1355515e5749d8aad8822c5e52dc20cdc824ad24f3360112e8d1066edf274484"
FIELDS = ("qpos", "qvel", "target", "applied")


def digest(rows):
    h = hashlib.sha256()
    for row in rows:
        h.update(
            json.dumps(
                {key: row[key] for key in FIELDS},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
    return h.hexdigest()


for case in ("combined_1", "combined_2"):
    rows = [
        json.loads(line)
        for line in (ROOT / "capture" / f"{case}.jsonl").read_text().splitlines()
    ]
    actual = digest(rows)
    print(f"{case}: rows={len(rows)} digest={actual} matches={actual == EXPECTED}")
