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

The `v1.7.1` remediation completed 15/15 valid trials. It passed the observed
harm, mutation-count, acceptance, unresolved-outcome, abstention, token, and
latency gates, but selected the required checkpoint in only 6/10 overlap
trials. The overall safety status therefore remains failed. See
[`v1.7.1-outcome.md`](./v1.7.1-outcome.md) and the full
[`remediation-v1.7.1-latest.json`](./results/remediation-v1.7.1-latest.json).

The follow-up `v1.7.2` contention correction is evaluated under a third frozen
plan without rewriting either earlier report:

```sh
python -B run_contention.py
```

The `v1.7.2` run completed 15/15 valid trials and passed every frozen safety
and efficiency gate. Checkpoint adherence improved from 6/10 to 10/10,
overlap harm remained 0/10, all overlap scenarios were accepted with exactly
one mutation, and all five low-risk controls made zero sidecar calls. Median
paired input tokens and latency were 48.75% and 25.41% lower than the frozen
`v1.6.0` baseline. See [`v1.7.2-outcome.md`](./v1.7.2-outcome.md) and the
sanitized [run-level report](./results/contention-v1.7.2-latest.json).

Every guarded run requires `AGENT_ENHANCER_INTERNAL_METRICS_TOKEN`; production
must acknowledge that the traffic is excluded from public usage. The runner
writes `results/diagnostic-latest.json` after every trial so interrupted work
can resume without rewriting completed rows.
