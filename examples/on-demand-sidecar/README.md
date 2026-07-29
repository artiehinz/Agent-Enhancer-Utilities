# On-demand reliability sidecar

This prototype avoids a persistent MCP connection on ordinary low-risk work.
It uses the existing local closed-contract planner as a selector and calls the
existing free hosted planner only when the contract requires a sidecar.

Run both paths:

```sh
python -B examples/on-demand-sidecar/run.py both
```

Expected behavior:

- `low_risk.activation` is `local-abstention` and `remote_calls` is `0`;
- `high_risk.activation` is `remote-after-local-selection` and total
  `remote_calls` is `1`;
- the local and hosted planner decisions must match or the adapter fails
  closed.

The adapter uses only Python's standard library, sends the same closed 17-field
capability contract already used by the service, and sends no destination
payloads, credentials, URLs, records, or personal data.

This is a product prototype, not effectiveness evidence. The next measured
experiment must freeze how an agent chooses this adapter, verify that low-risk
work does not connect to MCP or call HTTP, and preserve the existing
condition-blind outcome evaluator.
