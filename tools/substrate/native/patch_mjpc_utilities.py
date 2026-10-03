"""Generate the one-file hardened MJPC utilities copy from the pinned source."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

EXPECTED_SHA256 = "1924b6cea946cbac517abc1808e9433ddc8c1a390aee5e5c570d5aeab8fbd118"

OLD = """  if (dist < 0) {  // SHOULD NOT OCCUR
    mju_error("no group 0 geom detected by raycast");
  }

  return pos[2] + height_offset - dist;
"""

NEW = """  if (dist < 0) {
    // A divergent planner rollout can leave the ray origin below all group-0
    // geometry. Do not terminate the controller process: mark this mjData as
    // invalid so Trajectory::CheckWarnings rejects the rollout.
    mjData* mutable_data = const_cast<mjData*>(data);
    mutable_data->warning[mjWARN_BADQPOS].lastinfo = -1;
    mutable_data->warning[mjWARN_BADQPOS].number += 1;
    return pos[2];
  }

  return pos[2] + height_offset - dist;
"""


def hardened_text(data: bytes) -> str:
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("pinned MJPC utilities.cc identity drifted")
    text = data.decode()
    if text.count(OLD) != 1:
        raise ValueError("Ground fatal block did not match exactly once")
    return text.replace(OLD, NEW)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: patch_mjpc_utilities.py SOURCE OUTPUT")
    source, output = map(Path, sys.argv[1:])
    patched = hardened_text(source.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(patched)


if __name__ == "__main__":
    main()
