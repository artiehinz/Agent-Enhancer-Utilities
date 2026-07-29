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

The report measures verified completion, harmful outcomes, manual
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

Across the four risk scenarios, verified completion rose from 75% to 95% and
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
