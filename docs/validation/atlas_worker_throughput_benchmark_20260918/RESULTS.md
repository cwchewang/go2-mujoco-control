# Atlas worker throughput benchmark closeout

Date: `2026-09-18`

Task commit: `44be501436865f7139264385ac6c6d74b8497f58`

Frozen base: `99ad6e51cf51800571121339d53e5337a0ef0ae6`

Mode: `infrastructure benchmark / offline-only`

## FACTS

- The benchmark measured N=`1`, `2`, `3`, and `4` in that order, with two
  complete repetitions at every N. It launched 20 worker subprocesses total;
  every worker returned `0`, completed its bundle, and reported no timeout or
  failure.
- Every worker used the same frozen bundle and immutable task worktree. Each
  worker used a distinct temporary directory. Bytecode writes were disabled
  with `-B` and `PYTHONDONTWRITEBYTECODE=1`.
- The fixed bundle contained 72 repetitions of each of the following per
  worker: the full Atlas Python contract suite (`22` tests),
  `tools/check_repo_hygiene.py`, `git diff --check`, and a tracked C/C++/header/
  Python source scan. Each repetition also performed four SHA-256 traversals
  over the selected sources and wrote a per-pass digest report to the worker's
  isolated temporary directory.
- The source workload selected 215 tracked C/C++/header/Python files totaling
  2,586,820 bytes per traversal. The digest was identical for every worker:
  `7d3333bfa362d6929141196396752c8f56ad7dcb2c0aa8d2a60ed6029d507dff`.
- Each worker executed 576 bundle commands: 72 contract-suite launches, 72
  hygiene checks, 72 diff checks, 72 source scans, and 288 source traversals.
- The host was `Atlas` on WSL2, Linux `6.18.33.2`, Python `3.10.12`, with
  `os.cpu_count()` equal to 8. N=4 reached a maximum observed one-minute load
  average of `3.155`; its minimum observed `MemAvailable` was `14,464,744 KiB`
  (`13.795 GiB`). The complete before/during/after `/proc` snapshots are in
  `metrics.json`.
- The only repeated non-empty stderr was the normal successful unittest
  summary (`Ran 22 tests ... OK`). No unexpected stderr, failed return code,
  or timeout was observed.
- The required remote refresh was attempted but the managed linked worktree
  rejected the `FETCH_HEAD` write as read-only. No Git metadata was changed;
  the exact task commit, `HEAD`, `origin/main`, and the task branch ref were
  verified read-only before measurement.

## DERIVED METRICS

The table reports each batch. Throughput is completed workers divided by batch
wall time. Speedup and latency ratio use the mean of the two N=1 batches as the
baseline. Resource values are maxima/minima across each batch's before, during,
and after snapshots as specified in `metrics.json`.

| N | repeat | batch wall (s) | throughput (workers/s) | throughput speedup | mean latency (s) | max latency (s) | latency ratio | peak load 1m | min MemAvailable (GiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 61.686829 | 0.016211 | 1.000x | 61.630465 | 61.630465 | 1.000x | 0.414 | 13.886 |
| 1 | 2 | 61.685117 | 0.016211 | 1.000x | 61.624840 | 61.624840 | 1.000x | 0.720 | 13.897 |
| 2 | 1 | 60.995968 | 0.032789 | 2.023x | 60.915826 | 60.917392 | 0.988x | 1.226 | 13.868 |
| 2 | 2 | 60.992943 | 0.032791 | 2.023x | 60.925959 | 60.926245 | 0.989x | 1.375 | 13.859 |
| 3 | 1 | 60.894229 | 0.049266 | 3.039x | 60.834235 | 60.834716 | 0.987x | 1.815 | 13.833 |
| 3 | 2 | 60.892636 | 0.049267 | 3.039x | 60.855060 | 60.856302 | 0.988x | 2.097 | 13.828 |
| 4 | 1 | 60.944280 | 0.065634 | 4.049x | 60.893701 | 60.895981 | 0.988x | 2.654 | 13.802 |
| 4 | 2 | 61.796715 | 0.064728 | 3.993x | 61.314018 | 61.725388 | 0.995x | 3.155 | 13.795 |

Across repetitions, mean throughput was `0.016211`, `0.032790`, `0.049266`,
and `0.065181` workers/s for N=1 through N=4. Relative to N=1, those are
`1.000x`, `2.023x`, `3.039x`, and `4.021x`. N=4 provided `32.3%` more
throughput than N=3. Mean worker latency remained within `1.2%` below the N=1
baseline at N=3 and within `0.9%` below it at N=4; the N=4 repeat-2 maximum
was `61.725388 s`, only `0.15%` above the N=1 maximum.

## RECOMMENDATION

Recommend `ATLAS_MAX_WORKERS=4` for offline Atlas worker concurrency. All
four levels completed without failures or pathological resource pressure, and
N=4 retained near-linear throughput with no material per-worker latency
inflation while delivering a `32.3%` gain over N=3. The 8-vCPU host retained
substantial memory headroom and the observed N=4 load remained below half of
the available logical CPU count.

This benchmark characterizes offline worker concurrency only. It does not
characterize MuJoCo/DDS host-live concurrency; host-live concurrency remains
fixed at `1`.

Classification: `ATLAS_WORKER_THROUGHPUT_BENCHMARK_COMPLETE`
