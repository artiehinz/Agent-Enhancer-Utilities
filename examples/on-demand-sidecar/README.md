# On-demand reliability sidecar

This example uses the production-ready skills-first adapter without a
persistent MCP connection. It uses the local closed-contract planner as a
selector and calls the free hosted planner only when the contract requires a
sidecar.

Run both paths:

```sh
python -B examples/on-demand-sidecar/run.py both
```

Expected behavior:

- `low_risk.activation` is `local-abstention` and
  `remote_planner_calls` is `0`;
- `high_risk.activation` is `remote-after-local-selection` and total
  `remote_planner_calls` is `1`;
- the local and hosted planner decisions must match or the adapter fails
  closed.

The canonical adapter lives at
`skills/guard-external-plugin-workflows/scripts/on_demand.py`. It uses only
Python's standard library, sends the same closed 17-field capability contract
already used by the service, and rejects destination payloads, credentials,
URLs, records, personal data, raw identifiers, and unknown tools locally.

This example proves the activation boundary, not effectiveness. The separate
on-demand agent benchmark freezes skill selection, verifies zero low-risk
remote calls, and preserves a condition-blind outcome evaluator.
