# Runnable examples

The examples use the free, no-auth progressive MCP endpoint and Python's
standard library:

- [`reliability-sidecar`](./reliability-sidecar/) combines the guard planner
  with a mock domain agent and replays a duplicate-sensitive create.
- [`multi-agent-checkpoint`](./multi-agent-checkpoint/) races two workers for
  one expiring checkpoint and verifies that only the owner crosses the
  simulated action boundary.

Both examples discover and describe a module before invoking it. They fail
closed if the expected free module is unavailable or its result no longer
matches the documented safety contract.
