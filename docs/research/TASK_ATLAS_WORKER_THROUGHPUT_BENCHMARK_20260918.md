# TASK_ATLAS_WORKER_THROUGHPUT_BENCHMARK_20260918

## Goal
Measure how Atlas offline task throughput and per-task latency scale at concurrency 1, 2, 3, and 4 so the default `ATLAS_MAX_WORKERS` can be chosen from evidence rather than guesswork.

## Frozen base
- Canonical main: `99ad6e51cf51800571121339d53e5337a0ef0ae6`
- Branch: `research/atlas-worker-throughput-benchmark-20260918`
- Infrastructure benchmark only.

## Hard prohibitions
- Do not launch MuJoCo, DDS, controller/simulator, hardware, or any host-live scientific capability.
- Do not change `.github/**`, `tools/atlas_*`, controller, gait, MPC, WBC, IK, terrain, scientific thresholds, or raw `_runs` evidence.
- Do not tune the benchmark after seeing intermediate results.

## Benchmark design
Run a deterministic local benchmark harness from this task worktree. The harness itself may be temporary/untracked; only final validation artifacts should be committed.

Measure concurrency levels `N = 1, 2, 3, 4` in that order. For each N, launch N identical worker subprocesses simultaneously. Each subprocess must execute the same fixed representative offline bundle against the same immutable source tree, with separate temporary/cache directories so workers do not write each other's files.

Use only read-only or isolated-temp operations. The representative bundle should include all of:
1. repeated Atlas Python contract tests with bytecode writes disabled;
2. repeated repository hygiene checks;
3. repeated `git diff --check` / source-tree scan work;
4. a deterministic CPU+filesystem source-processing workload over tracked C++/header/Python sources (for example repeated SHA-256 traversal into a per-worker temporary directory or equivalent standard-library workload).

Choose repetition counts before collecting the first N=1 measurement, targeting roughly 20-60 seconds per individual worker at N=1 so scheduler/resource contention is measurable but the task stays lightweight. Record the chosen counts in the result before reporting measurements, and do not change them between N values.

For every N record at minimum:
- total wall time for the batch;
- each worker wall time and return code;
- throughput = completed worker bundles / batch wall time;
- mean and max per-worker latency;
- slowdown versus N=1;
- host CPU/load and memory snapshots before, during, and after using standard Linux `/proc`, `os`, `resource`, or commonly available read-only tools; if a metric is unavailable, record that explicitly rather than substituting guesses;
- any failures, timeouts, or anomalous stderr.

Run each N twice if the full benchmark remains under a reasonable runtime; otherwise one predeclared run per N is acceptable. Do not discard or cherry-pick repetitions.

## Decision rule
Recommend a default worker count from `{2,3,4}` using these priorities in order:
1. zero failures and no pathological resource pressure;
2. meaningful total throughput gain over lower N;
3. acceptable per-worker latency inflation;
4. preserve headroom for normal desktop/Atlas use and occasional compilation bursts.

Do not recommend 4 merely because all four technically finish. If 3 captures nearly all throughput of 4 with materially lower latency/resource pressure, prefer 3. If 4 scales cleanly, prefer 4. Keep host-live concurrency at 1 regardless of this result.

## Required artifacts
Write only:
- `docs/validation/atlas_worker_throughput_benchmark_20260918/RESULTS.md`
- `docs/validation/atlas_worker_throughput_benchmark_20260918/metrics.json`

`RESULTS.md` must clearly separate FACTS, DERIVED METRICS, and RECOMMENDATION, include the fixed workload/repetition counts, and state that this benchmark characterizes offline worker concurrency only, not MuJoCo/DDS host-live concurrency.

## Acceptance
Classify `ATLAS_WORKER_THROUGHPUT_BENCHMARK_COMPLETE` only if all four concurrency levels are measured with the same frozen workload and the artifacts contain enough raw timing/resource facts to independently recompute the recommendation.