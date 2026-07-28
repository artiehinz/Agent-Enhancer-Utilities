# Paired reliability-sidecar benchmark

This deterministic, model-free benchmark compares the same synthetic workflow
with and without the Reliability Sidecar Contract v1.

It covers:

1. a duplicate-sensitive create whose success response is lost;
2. overlapping multi-worker implementation;
3. a shared provider rate limit;
4. repeated refresh of already-current data; and
5. a one-time low-risk read where the sidecar must abstain.

Run:

```sh
python -B examples/sidecar-benchmark/run.py
python -B examples/sidecar-benchmark/test_benchmark.py
```

The runner executes five harness-validation pairs per scenario, excludes them
from the report, then executes 20 published pairs with randomized condition
order. The fixed seed, scenario definitions, success thresholds, and
limitations are in
[`preregistered-plan.json`](./preregistered-plan.json).

The committed [`results/latest.json`](./results/latest.json) includes
sanitized run-level rows and aggregates. It does not contain prompts, user
data, credentials, IP addresses, or external provider records.

## What it proves

The suite can prove deterministic invariants such as:

- a guarded ambiguous success is reconciled without a second mutation;
- only one competing worker crosses the synthetic write boundary;
- shared quota is enforced before the provider rejects a call;
- already-current work is skipped; and
- an ordinary read adds no sidecar calls.

It does not use an LLM and therefore does not claim token savings, better
reasoning, or improved real-world agent quality. Token and model-cost fields
are explicitly `null`. A later measured-agent tier must keep model, prompt,
workspace, and host settings fixed and publish its own run-level evidence.

## Optional production adapter

[`adapters.py`](./adapters.py) includes an optional remote adapter for
`workflow-checkpoint`. The published benchmark uses the in-memory adapter so
it is deterministic and does not turn owned production traffic into usage
evidence.

When manually exercising the remote adapter, use the source-tagged endpoint,
opaque random identifiers, short TTLs, and the private internal-metrics marker
when available.
