# Runnable examples

The examples use the free, no-auth progressive MCP endpoint and Python's
standard library:

- [`reliability-sidecar`](./reliability-sidecar/) combines the guard planner
  with a mock domain agent and replays a duplicate-sensitive create.
- [`multi-agent-checkpoint`](./multi-agent-checkpoint/) races two workers for
  one expiring checkpoint and verifies that only the owner crosses the
  simulated action boundary.
- [`goose`](./goose/) is a validated Goose recipe that adds the same
  reliability-sidecar lifecycle to an authorized workspace or domain task.
- [`sidecar-benchmark`](./sidecar-benchmark/) is a pre-registered,
  deterministic with/without benchmark with sanitized run-level evidence.
- [`sidecar-agent-benchmark`](./sidecar-agent-benchmark/) is the frozen,
  metered Codex tier that measures real token use, tool calls, latency,
  multi-agent behavior, and machine-verified outcomes.

The Python examples discover and describe a module before invoking it. They
fail closed if the expected free module is unavailable or its result no longer
matches the documented safety contract. The Goose recipe uses the same
progressive discovery tools and keeps the destination action in Goose.
The deterministic benchmark is intentionally model-free and makes no
token-saving or agent-quality claim. The metered tier keeps its five validation
pairs local and will publish only the later 20-pair sample, including neutral
or negative outcomes.
