"""Build matched FD-traced MJPC sources from one exact pinned translation unit."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

EXPECTED_SHA256 = "e44b7ab9941e9d6397527c1e5af77c70319329667436d8a45e1b2d10d80fa74b"
EXPECTED_GIT_BLOB = "03f67529a212d6c11f2dcad0a4bf44edd78fa1f2"
INCLUDE = '#include "mjpc/utilities.h"\n'
INCLUDE_WITH_TRACE = '#include "mjpc/utilities.h"\n#include "model_derivative_indices.h"\n\n#include <atomic>\n#include <chrono>\n#include <cmath>\n#include <cstdint>\n#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <iomanip>\n#include <stdexcept>\n'
OLD = """  // evaluate indices
  int s = skip + 1;
  evaluate_.push_back(0);
  for (int t = s; t < T - s; t += s) {
    evaluate_.push_back(t);
  }
  evaluate_.push_back(T - 2);
  evaluate_.push_back(T - 1);
"""
OLD_INSTRUMENTED = """  // Evaluate in source order and retain one event slot per scheduled task.
  std::vector<int> legacy_indices{0};
  const int stride = skip + 1;
  for (int t = stride; t < T - stride; t += stride) {
    legacy_indices.push_back(t);
  }
  legacy_indices.push_back(T - 2);
  legacy_indices.push_back(T - 1);
  evaluate_ = legacy_indices;
"""
FIXED_INSTRUMENTED = """  // Use the unique-index patch; all FD event tracing matches the baseline.
  evaluate_ = go2_substrate::ModelDerivativeEvaluateIndices(T, skip);
"""
TRACE_TYPES = "struct FDSummary {\n  std::uint64_t hash = 14695981039346656037ULL;\n  double norm = 0.0;\n  double max_abs = 0.0;\n};\nstruct FDEvent {\n  int t=-1; int worker=-1; std::uint64_t call=0;\n  std::int64_t start_ns=0; std::int64_t end_ns=0;\n  FDSummary before; FDSummary after;\n};\nnamespace {\nstd::atomic<std::uint64_t> g_fd_call_index{0};\nstd::int64_t FDTraceNowNs() {\n return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();\n}\nstd::uint64_t FDTraceHash(const double* data,std::size_t count,std::uint64_t hash) {\n const auto* bytes=reinterpret_cast<const unsigned char*>(data);\n for(std::size_t i=0;i<count*sizeof(double);++i){hash^=bytes[i];hash*=1099511628211ULL;} return hash;\n}\nFDSummary FDTraceSummary(const double* data,int count) {\n FDSummary result; double squared_norm=0.0;\n for(int i=0;i<count;++i){double magnitude=std::abs(data[i]);squared_norm+=data[i]*data[i];if(magnitude>result.max_abs)result.max_abs=magnitude;}\n result.norm=std::sqrt(squared_norm);result.hash=FDTraceHash(data,count,result.hash);return result;\n}\n}  // namespace"
OLD_SCHEDULE = """  // evaluate derivatives
  int count_before = pool.GetCount();
  for (int t : evaluate_) {
    pool.Schedule([&m, &data, &A = A, &B = B, &C = C, &D = D, &x, &u, &h,
                   dim_state, dim_state_derivative, dim_action, dim_sensor, tol,
                   mode, t, T]() {
      mjData* d = data[ThreadPool::WorkerId()].get();
      // set state
      SetState(m, d, x + t * dim_state);
      d->time = h[t];

      // set action
      mju_copy(d->ctrl, u + t * dim_action, dim_action);

      // Jacobians
      if (t == T - 1) {
        // Jacobians
        mjd_transitionFD(m, d, tol, mode, nullptr, nullptr,
                         DataAt(C, t * (dim_sensor * dim_state_derivative)),
                         nullptr);
      } else {
        // derivatives
        mjd_transitionFD(
            m, d, tol, mode,
            DataAt(A, t * (dim_state_derivative * dim_state_derivative)),
            DataAt(B, t * (dim_state_derivative * dim_action)),
            DataAt(C, t * (dim_sensor * dim_state_derivative)),
            DataAt(D, t * (dim_sensor * dim_action)));
      }
    });
  }
  pool.WaitCount(count_before + evaluate_.size());
  pool.ResetCount();
"""
NEW_SCHEDULE = '  // Trace records use unique slots, so tracing does not lock around FD work.\n  const char* trace_path = std::getenv("GO2_MJPC_FD_TRACE_PATH");\n  std::vector<FDEvent> fd_events(trace_path ? evaluate_.size() : 0);\n  const std::uint64_t call_index = trace_path ? g_fd_call_index.fetch_add(1) + 1 : 0;\n  int count_before = pool.GetCount();\n  for (std::size_t slot = 0; slot < evaluate_.size(); ++slot) {\n    const int t = evaluate_[slot];\n    pool.Schedule([&m, &data, &A = A, &B = B, &C = C, &D = D, &x, &u, &h,\n                   &fd_events, trace_path, slot, call_index,\n                   dim_state, dim_state_derivative, dim_action, dim_sensor, tol,\n                   mode, t, T]() {\n      const int worker = ThreadPool::WorkerId();\n      mjData* d = data[worker].get();\n      SetState(m, d, x + t * dim_state);\n      d->time = h[t];\n      mju_copy(d->ctrl, u + t * dim_action, dim_action);\n      const std::int64_t start_ns = trace_path ? FDTraceNowNs() : 0;\n      const FDSummary before = trace_path ? FDTraceSummary(d->qacc_warmstart, m->nv) : FDSummary{};\n      if (t == T - 1) {\n        mjd_transitionFD(m, d, tol, mode, nullptr, nullptr,\n                         DataAt(C, t * (dim_sensor * dim_state_derivative)),\n                         nullptr);\n      } else {\n        mjd_transitionFD(\n            m, d, tol, mode,\n            DataAt(A, t * (dim_state_derivative * dim_state_derivative)),\n            DataAt(B, t * (dim_state_derivative * dim_action)),\n            DataAt(C, t * (dim_sensor * dim_state_derivative)),\n            DataAt(D, t * (dim_sensor * dim_action)));\n      }\n      if (trace_path) {\n        const FDSummary after = FDTraceSummary(d->qacc_warmstart, m->nv);\n        fd_events[slot] = {t, worker, call_index, start_ns, FDTraceNowNs(), before, after};\n      }\n    });\n  }\n  pool.WaitCount(count_before + evaluate_.size());\n  pool.ResetCount();\n\n  if (trace_path) {\n    if (std::find(evaluate_.begin(), evaluate_.end(), T - 2) == evaluate_.end()) {\n      throw std::runtime_error("FD trace missing penultimate knot");\n    }\n    std::uint64_t hash = 14695981039346656037ULL;\n    hash = FDTraceHash(DataAt(A, (T - 2) * dim_state_derivative * dim_state_derivative),\n                       dim_state_derivative * dim_state_derivative, hash);\n    hash = FDTraceHash(DataAt(B, (T - 2) * dim_state_derivative * dim_action),\n                       dim_state_derivative * dim_action, hash);\n    hash = FDTraceHash(DataAt(C, (T - 2) * dim_sensor * dim_state_derivative),\n                       dim_sensor * dim_state_derivative, hash);\n    hash = FDTraceHash(DataAt(D, (T - 2) * dim_sensor * dim_action),\n                       dim_sensor * dim_action, hash);\n    std::ofstream trace(trace_path, std::ios::app);\n    if (!trace) throw std::runtime_error("FD trace output cannot be opened");\n    trace << "{\\"call_index\\":" << call_index << ",\\"events\\":[";\n    for (std::size_t i = 0; i < fd_events.size(); ++i) {\n      if (i) trace << \',\';\n      const auto& event = fd_events[i];\n      trace << "{\\"t\\":" << event.t << ",\\"worker\\":" << event.worker\n            << ",\\"call_index\\":" << event.call\n            << ",\\"start_ns\\":" << event.start_ns\n            << ",\\"end_ns\\":" << event.end_ns\n            << ",\\"warmstart_before_fnv1a64\\":\\"" << std::hex << std::setw(16) << std::setfill(\'0\') << event.before.hash << "\\""\n            << ",\\"warmstart_before_norm\\":" << std::dec << event.before.norm\n            << ",\\"warmstart_before_max_abs\\":" << event.before.max_abs\n            << ",\\"warmstart_after_fnv1a64\\":\\"" << std::hex << std::setw(16) << std::setfill(\'0\') << event.after.hash << "\\""\n            << ",\\"warmstart_after_norm\\":" << std::dec << event.after.norm\n            << ",\\"warmstart_after_max_abs\\":" << event.after.max_abs << \'}\';\n    }\n    trace << "],\\"jacobian_t34_fnv1a64\\":\\"" << std::hex\n          << std::setw(16) << std::setfill(\'0\') << hash\n          << "\\",\\"index_count\\":" << std::dec << evaluate_.size()\n          << "}\\n";\n  }\n'
OLD_RUN = """  // evaluate derivatives
  int count_before = pool.GetCount();
"""
# The stable anchor makes the same task instrumentation active in both sources.
INSTRUMENTED_BLOCK = OLD_SCHEDULE


def _base(data: bytes) -> str:
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("pinned MJPC model_derivatives.cc SHA-256 drifted")
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob != EXPECTED_GIT_BLOB:
        raise ValueError("pinned MJPC model_derivatives.cc git blob drifted")
    text = data.decode()
    if (
        text.count(INCLUDE) != 1
        or text.count(OLD) != 1
        or text.count(OLD_SCHEDULE) != 1
    ):
        raise ValueError("pinned MJPC diagnostic patch anchors mismatch")
    text = text.replace(INCLUDE, INCLUDE_WITH_TRACE, 1)
    text = text.replace("namespace mjpc {\n", "namespace mjpc {\n" + TRACE_TYPES, 1)
    return text.replace(OLD_SCHEDULE, NEW_SCHEDULE, 1)


def render(data: bytes, fixed: bool) -> str:
    text = _base(data)
    replacement = FIXED_INSTRUMENTED if fixed else OLD_INSTRUMENTED
    if text.count(OLD) != 1:
        raise ValueError("pinned MJPC index block did not match exactly once")
    return text.replace(OLD, replacement, 1)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: patch_mjpc_model_derivatives_diagnostic.py SOURCE ORIGINAL_OUT FIXED_OUT"
        )
    source, original, fixed = map(Path, sys.argv[1:])
    data = source.read_bytes()
    original_text = render(data, False)
    fixed_text = render(data, True)
    original.parent.mkdir(parents=True, exist_ok=True)
    fixed.parent.mkdir(parents=True, exist_ok=True)
    original.write_text(original_text)
    fixed.write_text(fixed_text)


if __name__ == "__main__":
    main()
