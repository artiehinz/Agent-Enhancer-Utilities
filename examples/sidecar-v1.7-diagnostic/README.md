# Sidecar v1.7 exploratory diagnostic

This diagnostic compares no sidecar, released skill `v1.6.0`, and candidate
skill `v1.7.0` on overlapping workers and low-risk abstention. It reuses the
condition-blind synthetic destination and metered Codex harness from the
published on-demand benchmark without changing or pooling that 200-run report.

The single production app creates an explicit order limitation. The exact
`v1.6.0` local planner must run against backend `0.6.10`; the exact `v1.7.0`
planner must run against backend `0.7.0`. The report is exploratory and cannot
support a confirmatory product claim.

The immutable `v1.6.0` tag predates the on-demand adapter used by the published
200-run study. The baseline therefore pins the final pre-`v1.7.0` commit on the
`1.6.0` release line (`a161e4f...`) and discloses that artifact mismatch. The
tag is not rewritten.

Run the two pre-deployment conditions:

```sh
python -B run.py --condition no-sidecar
python -B run.py --condition skill-v1.6.0
```

After deploying backend `0.7.0`, run:

```sh
python -B run.py --condition skill-v1.7.0
```

The first two `v1.7.0` trials each reached the fixed 360-second timeout. The
run was stopped under a documented post-start futility amendment rather than
hiding or repeatedly replacing invalid rows. See
[`v1.7.0-outcome.md`](./v1.7.0-outcome.md) and the unchanged
[`diagnostic-latest.json`](./results/diagnostic-latest.json).

The workflow-discovery fix is released separately as `v1.7.1`. Its remediation
diagnostic has its own frozen plan and output:

```sh
python -B run_remediation.py
```

It reuses only the published `no-sidecar` and `v1.6.0` baseline rows. It does
not rewrite, complete, or pool the incomplete `v1.7.0` condition.

Every guarded run requires `AGENT_ENHANCER_INTERNAL_METRICS_TOKEN`; production
must acknowledge that the traffic is excluded from public usage. The runner
writes `results/diagnostic-latest.json` after every trial so interrupted work
can resume without rewriting completed rows.
