"""Generate a narrow, source-locked MJPC derivative-index overlay."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

EXPECTED_SHA256 = "e44b7ab9941e9d6397527c1e5af77c70319329667436d8a45e1b2d10d80fa74b"
EXPECTED_GIT_BLOB = "03f67529a212d6c11f2dcad0a4bf44edd78fa1f2"

INCLUDES = '#include "mjpc/utilities.h"\n'
PATCHED_INCLUDES = INCLUDES + '#include "model_derivative_indices.h"\n'

OLD = """  // evaluate indices
  int s = skip + 1;
  evaluate_.push_back(0);
  for (int t = s; t < T - s; t += s) {
    evaluate_.push_back(t);
  }
  evaluate_.push_back(T - 2);
  evaluate_.push_back(T - 1);
"""
NEW = """  // evaluate indices; retain the original order without duplicate indices.
  evaluate_ = go2_substrate::ModelDerivativeEvaluateIndices(T, skip);
"""


def patched_text(data: bytes) -> str:
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("pinned MJPC model_derivatives.cc SHA-256 drifted")
    git_blob = hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()
    if git_blob != EXPECTED_GIT_BLOB:
        raise ValueError("pinned MJPC model_derivatives.cc git blob drifted")
    text = data.decode()
    if text.count(INCLUDES) != 1 or text.count(OLD) != 1:
        raise ValueError("pinned MJPC derivative block did not match exactly once")
    text = text.replace(INCLUDES, PATCHED_INCLUDES, 1)
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: patch_mjpc_model_derivatives.py SOURCE OUTPUT")
    source, output = map(Path, sys.argv[1:])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(patched_text(source.read_bytes()))


if __name__ == "__main__":
    main()
