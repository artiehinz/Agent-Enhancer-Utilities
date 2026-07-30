# Runnable examples

The examples use Python's standard library with either the free no-auth MCP or
the direct on-demand HTTP contract:

- [`reliability-sidecar`](./reliability-sidecar/) combines the guard planner
  with a mock domain agent and replays a duplicate-sensitive create.
- [`multi-agent-checkpoint`](./multi-agent-checkpoint/) races two workers for
  one expiring checkpoint and verifies that only the owner crosses the
  simulated action boundary.
- [`goose`](./goose/) is a validated Goose recipe that adds the same
  reliability-sidecar lifecycle to an authorized workspace or domain task.
- [`sidecar-benchmark`](./sidecar-benchmark/) is a pre-registered,
  deterministic with/without benchmark with sanitized run-level evidence.
- [`sidecar-agent-benchmark`](./sidecar-agent-benchmark/) is the preregistered,
  metered Codex tier that measures real token use, tool calls, latency,
  multi-agent behavior, and machine-verified outcomes. Both completed
  validations remain published. The core-profile sample demonstrated
  duplicate prevention but still failed the connection-overhead gates.
- [`on-demand-sidecar`](./on-demand-sidecar/) demonstrates local abstention,
  one hosted planner check for risk-bearing work, and fail-closed plan drift.
- [`on-demand-agent-benchmark`](./on-demand-agent-benchmark/) is a separate
  skills-only Codex preregistration. Neither condition exposes MCP; only the
  with condition receives one repo-scoped skill. Its complete publication
  report contains 20 pairs per scenario and passes the frozen gates.

The Python examples discover and describe a module before invoking it. They
fail closed if the expected free module is unavailable or its result no longer
matches the documented safety contract. The Goose recipe uses the same
progressive discovery tools and keeps the destination action in Goose.
The deterministic benchmark is intentionally model-free and makes no
token-saving or agent-quality claim. The persistent-MCP metered tier preserves
its failed validations. The separate skills-first metered tier publishes its
passed validation and complete 20-pair-per-scenario publication sample without
pooling any of those rows.
