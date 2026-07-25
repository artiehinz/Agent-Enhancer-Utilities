# Sidecar recipe test evidence

Test date: 2026-07-25

Environment: live Agent Enhancer Utilities direct tools backed by
`https://liberated.site/mcp`, using opaque synthetic namespaces and 60-second
temporary state. No Notion, investment, messaging, customer, or other
production plugin data was read or changed.

These tests validate the current coordination contracts used by the recipes.
They do not prove an external plugin's consistency, idempotency, or write
behavior.

## Prior cross-plugin observations

The roadmap began from two user-run composition checks:

- A Notion workflow confirmed that Agent Enhancer does not modify Notion's
  search, create, or update tools. Notion writes do not accept Agent Enhancer
  idempotency keys, so a crash after creation can still duplicate a retry unless
  the workflow stores and searches a stable destination marker.
- A Public Equity Investing workflow confirmed that Agent Enhancer does not
  change financial knowledge, source quality, modeling, or conclusions. Its
  value appears in repeated and parallel processing: filing deduplication,
  refresh ownership, shared provider quotas, and one guarded final tracker
  update.

Both checks found that installing the plugins does not connect them
automatically. The new sidecar skill supplies that deliberate composition
workflow.

## Create-once guard sequence

Observed:

- the first `penny-lock` call acquired the opaque work key;
- replaying the identical call with the same idempotency key returned the same
  result with `idempotency_replayed: true`;
- a different owner was denied while the lock remained active;
- the first `global-seen-stamp` call returned `seen_before: false`;
- a later call for the same opaque content hash returned `seen_before: true`.

The external search/create/read-back boundary was simulated and no external
record was created.

Finding:

`global-seen-stamp` is an atomic seen-or-mark operation. The first call creates
state, so it cannot serve as a read-only completion check. A stamp hit is
sidecar evidence only and must not replace destination verification. The
create-once recipe therefore uses the destination's stable marker as the source
of external evidence and writes an optional stamp only after verification.

The live direct surface exposed no `penny-lock` release operation. Recipes must
choose the shortest practical TTL and must not claim immediate release unless a
future live contract explicitly supports it.

## Fan-out-bounded sequence

Observed:

- one worker acquired a freshness lease and a different holder was denied;
- a capacity-two semaphore admitted two holders and denied a third;
- a capacity-two rate gate allowed two unique one-token operations and denied
  the third with `insufficient_tokens` and a bounded retry delay;
- a threshold-two barrier remained closed after one unique arrival and released
  after the second;
- both semaphore permits and the freshness lease were explicitly released by
  their current holders.

Finding:

The current primitives support the ownership, concurrency, quota, and fan-in
parts of the parallel-research recipe. They still do not represent whether an
external worker result was stored or verified. Barrier arrival must therefore
occur only after the caller has verified its durable result.

## Resulting design decision

The most immediate missing state is not another rate or concurrency limiter. It
is an explicit distinction between:

- work claimed;
- an external result that is uncertain;
- external evidence reported by the caller;
- failure or compensation.

That evidence selected
[Opaque Workflow Checkpoints](./OPAQUE_WORKFLOW_CHECKPOINTS.md) as the first
new stateful sidecar proposal. A
[Shared Circuit Breaker](./SHARED_CIRCUIT_BREAKER.md) remains the next candidate
for swarm-wide dependency failure containment.

## Planner contract and reference

The exact closed planner input and output schemas were submitted to the live
`mcp-tool-contract-linter`. It returned `valid: true`, zero findings, and nine
rules checked.

The local reference planner passes nine unit tests and a CLI smoke test. The
smoke input described a scheduled four-worker batch create with eventual
destination search, a stable marker, read-after-write, a shared rate limit, and
capacity two. It produced:

- primary profile `create-once`;
- additional profiles `fan-out-bounded` and `scheduled-run`;
- guarantee `duplicate-resistant`;
- run lock, per-item lock, semaphore, rate gate, destination search, create,
  read-back, post-verification seen stamp, barrier, and report stages;
- explicit eventual-search, lock-expiry, advisory-stamp, and
  no-cross-plugin-transaction risks.

This is deterministic planning evidence, not a deployed MCP planner or an
external write test.

## Remaining end-to-end tests

Before publishing a vendor-named recipe as worked-once evidence, test against
the exact external plugin/tool version:

- timeout before the external call;
- timeout after the destination accepts the action;
- crash before verification;
- eventual-search delay;
- destination record removed after a sidecar stamp;
- unguarded external writer;
- changed tool schema or action annotations.
