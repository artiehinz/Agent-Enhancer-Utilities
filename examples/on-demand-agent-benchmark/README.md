# Skills-first on-demand agent benchmark

This benchmark measures whether a repo-scoped Agent Enhancer skill improves
five controlled Codex workflows without the persistent MCP overhead measured
in the earlier benchmark.

The two conditions differ only here:

- `without-sidecar` has no Agent Enhancer skill and no MCP;
- `with-sidecar` has one
  `guard-external-plugin-workflows` repo skill, without `.mcp.json` or MCP
  dependency metadata.

Both conditions receive the same prompt, frozen capability facts, model,
reasoning effort, disposable destination, injected failures, evaluator, and
condition-blind machine-state checks. Condition order is randomized within
each pair.

## Frozen scenarios

1. A duplicate-sensitive create whose first successful response is lost.
2. Two overlapping development workers.
3. Two workers sharing one rate-limited batch.
4. Two scheduled refresh workers suppressing stale work.
5. An ordinary one-time low-risk read where the skill must abstain.

The report measures condition-blind scenario acceptance, harmful outcomes, manual
intervention, activation and abstention accuracy, direct HTTP calls, tokens,
and wall-clock latency. The fixed gates are in
[`preregistered-plan.json`](./preregistered-plan.json).

## Run

Set `AGENT_ENHANCER_INTERNAL_METRICS_TOKEN` locally so production can exclude
all benchmark traffic from public usage. Never commit that value.

Run unit tests:

```sh
python -B examples/on-demand-agent-benchmark/test_benchmark.py
```

Run the frozen validation:

```sh
python -B examples/on-demand-agent-benchmark/run.py --phase validation
```

The default validation report is
`results/validation-latest.json`. Workspaces and raw Codex event logs remain
under ignored `.local-results/` only when `--keep-workspaces` is supplied.

Publication is blocked unless the complete five-pair validation report passes
every preregistered gate:

```sh
python -B examples/on-demand-agent-benchmark/run.py --phase publication
```

## Validation result

The frozen validation completed 50 valid runs, five pairs per scenario, and
passed every preregistered gate. The complete sanitized report is
[`results/validation-latest.json`](./results/validation-latest.json).

| Scenario | Without sidecar | With sidecar | Honest conclusion |
|---|---:|---:|---|
| Ambiguous create | 5/5 verified, 0 harm | 5/5 verified, 0 harm | No measured reliability benefit; guarded runs cost more |
| Overlapping workers | 0/5 verified, 10 harm | 4/5 verified, 2 harm | 80% fewer harmful conflicts, with substantial overhead |
| Shared rate limit | 5/5 verified, 0 harm | 5/5 verified, 0 harm | No measured reliability benefit; guarded runs cost more |
| Scheduled refresh | 5/5 verified, 0 harm | 5/5 verified, 0 harm | No measured reliability benefit; guarded runs cost more |
| Low-risk control | 5/5 verified | 5/5 verified, 5/5 abstained | Zero adapter and remote calls, as required |

Across the four risk scenarios, scenario acceptance rose from 75% to 95% and
harmful events fell from 10 to 2. All of that harm reduction came from the
overlapping-worker scenario. The result does not support a general claim that
Agent Enhancer is faster or cheaper. Median low-risk token and latency
differences were below zero, but the skill made no calls in those runs, so the
difference is treated as host variance rather than product savings.

Two guarded shared-rate runs timed out on their first attempt. Their partial
pairs and the two timeout rows remain as four infrastructure exclusions. Both
pairs were rerun successfully with the same frozen protocol, model, prompt,
and timeout.

Do not pool these rows with the persistent-MCP `0.6.4`, `0.6.5`, or compact
probe results. A failed or neutral complete validation remains evidence and
must be retained.

## Publication result

The separate publication sample completed 200 valid runs: 20 pairs for each
of the five scenarios. It passed every preregistered gate.

| Scenario | Acceptance without → with | Runs with confirmed harm | Unresolved outcomes | Paired token p50 / p90 | Paired latency p50 / p90 |
|---|---:|---:|---:|---:|---:|
| Ambiguous create | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | +572% / +777% | +365% / +455% |
| Overlapping workers | 8 → 19 / 20 | 12 → 1 / 20 | 0 → 0 | +257% / +404% | +202% / +266% |
| Shared rate limit | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | +284% / +462% | +150% / +192% |
| Scheduled refresh | 18 → 20 / 20 | 2 → 0 / 20 | 0 → 0 | +240% / +342% | +140% / +281% |
| Low-risk control | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | -34% / +1% | -33% / -1% |

Across the four risk scenarios, runs with at least one confirmed harmful
mutation, conflict, or rejection fell from 14/80 to 1/80, a 92.857%
reduction. The legacy `verified` field is now described as evaluator
acceptance: it rose from 66/80 to 79/80. The condition-blind evaluator ran and
a final response was present for all 160 retained risk-scenario rows.

The original pooled counters remain 26 to 2, but they are secondary because
one run can emit correlated categories. Twelve unguarded overlap runs each
emitted both one duplicate-mutation counter and one conflicting-action
counter; one guarded run did the same. Unresolved outcomes were 0 in both
conditions, so none of the original 26 or 2 counters represented an unknown
result.

This finer breakdown is a post-hoc descriptive reanalysis of unchanged rows,
not a new preregistered gate. Reproduce it with `python reanalyze.py`; inspect
[`results/publication-reanalysis.json`](./results/publication-reanalysis.json)
for p50, p90, and p95 absolute and paired distributions.

The observed low-risk median differences were -33.913% input tokens and
-32.53% wall-clock latency. The skill made no adapter or remote call in those
runs, so these differences are not attributed to Agent Enhancer and are not
reported as savings. Guarded runs in every risk-bearing scenario used
materially more tokens and time.

Three guarded shared-rate runs timed out during the initial execution. The
resume path discarded one partial counterpart and reran all three pairs under
the unchanged frozen protocol. Those four infrastructure rows remain in
`infrastructure_exclusions`.

The complete sanitized report is
[`results/publication-latest.json`](./results/publication-latest.json).
