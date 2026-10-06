"""Generate narrow logical-trajectory warmstart overlays from pinned MJPC."""

from pathlib import Path
import hashlib
import sys


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError("logical warmstart patch anchor mismatch: " + old[:60])
    return text.replace(old, new)


def generate(source, output):
    source, output = Path(source), Path(output)
    paths = [
        "trajectory.h",
        "trajectory.cc",
        "planners/model_derivatives.h",
        "planners/ilqg/planner.cc",
    ]
    identity = {}
    for name in paths:
        p = source / "mjpc" / name
        text = p.read_text()
        identity[name] = hashlib.sha256(p.read_bytes()).hexdigest()
        if name == "trajectory.h":
            text = replace(
                text,
                "  std::vector<double> states;",
                "  std::vector<double> warmstarts; // warmstart at each recorded state\n  std::vector<double> warmstart_seed; // previous end of this logical rollout\n  std::vector<double> states;",
            )
        elif name == "trajectory.cc":
            text = replace(
                text,
                '#include "mjpc/trajectory.h"',
                '#include "mjpc/trajectory.h"\n#include "logical_warmstart.h"',
            )
            text = replace(
                text,
                "  // states\n  std::fill(states.begin()",
                "  warmstarts.clear();\n  warmstart_seed.clear();\n  // states\n  std::fill(states.begin()",
            )
            text = replace(
                text,
                "  for (int t = 0; t < horizon - 1; t++) {",
                "  if (go2_substrate::LogicalWarmstart()) {\n    warmstarts.resize(nv * horizon);\n    if (warmstart_seed.size() != static_cast<std::size_t>(nv)) warmstart_seed.assign(nv, 0.0);\n    mju_copy(data->qacc_warmstart, warmstart_seed.data(), nv);\n  }\n\n  for (int t = 0; t < horizon - 1; t++) {",
                2,
            )
            text = replace(
                text,
                "    // step\n    mj_step(model, data);",
                "    if (go2_substrate::LogicalWarmstart())\n      mju_copy(DataAt(warmstarts, t * nv), data->qacc_warmstart, nv);\n    // step\n    mj_step(model, data);",
                2,
            )
            text = replace(
                text,
                "  // final forward\n  mj_forward(model, data);",
                "  if (go2_substrate::LogicalWarmstart()) {\n    mju_copy(DataAt(warmstarts, (horizon - 1) * nv), data->qacc_warmstart, nv);\n    mju_copy(warmstart_seed.data(), data->qacc_warmstart, nv);\n  }\n  // final forward\n  mj_forward(model, data);",
                2,
            )
        elif name == "planners/model_derivatives.h":
            text = replace(
                text,
                "ThreadPool& pool, int skip = 0",
                "ThreadPool& pool, int skip = 0, const double* warmstarts = nullptr",
            )
        else:
            text = replace(
                text,
                "settings.fd_tolerance, settings.fd_mode, pool, derivative_skip_);",
                "settings.fd_tolerance, settings.fd_mode, pool, derivative_skip_,\n      candidate_policy[0].trajectory.warmstarts.empty() ? nullptr : candidate_policy[0].trajectory.warmstarts.data());",
            )
        target = output / "mjpc" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    return identity


def derivatives(path):
    p = Path(path)
    text = p.read_text()
    text = replace(
        text,
        '#include "mjpc/utilities.h"',
        '#include "mjpc/utilities.h"\n#include "logical_warmstart.h"',
    )
    text = replace(
        text,
        "ThreadPool& pool, int skip)",
        "ThreadPool& pool, int skip, const double* warmstarts)",
    )
    text = replace(
        text,
        "&fd_events, trace_path, slot, call_index,",
        "&fd_events, trace_path, slot, call_index, warmstarts,",
    )
    text = replace(
        text,
        "      mju_copy(d->ctrl, u + t * dim_action, dim_action);",
        '      mju_copy(d->ctrl, u + t * dim_action, dim_action);\n      if (go2_substrate::LogicalWarmstart()) {\n        if (!warmstarts) throw std::runtime_error("missing nominal warmstart knots");\n        mju_copy(d->qacc_warmstart, warmstarts + t * m->nv, m->nv);\n      }',
    )
    p.write_text(text)


if __name__ == "__main__":
    generate(sys.argv[1], sys.argv[2])
    derivatives(sys.argv[3])
