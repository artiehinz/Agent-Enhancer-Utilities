# Sidecar recipe test evidence

Test date: 2026-07-25

This file contains the isolated Sidecar v1 release evidence followed by the
earlier production-primitive observations that selected the checkpoint design.

## Isolated Sidecar v1 acceptance

Candidate:

- public skills commit: `a7c37775aa1cefa1b5eb6024786fc9a7bf6ec78d`;
- backend commit: `52bfd816738bd8af36d5dcf54dbe6beb59146eb7`;
- backend version: `0.6.0`;
- DigitalOcean deployment:
  `6d5397ae-b2ee-4203-b4a0-bb52a1477aef`;
- recipe version: `sidecar-v1/1`;
- external connector: the Notion connector exposed through plugin package
  `0.1.7`;
- observed window: 2026-07-25 22:49–22:56 UTC.

The short-lived preview used a fresh development PostgreSQL component, the
existing managed Valkey cluster under a unique preview namespace, disabled
payments, disabled automatic deployment, and independently generated preview
secrets. The external test used one disposable Notion database and five
synthetic records. No production Notion, investment, messaging, customer, or
other plugin data was read or changed.

Observed platform gates:

- 24 of 24 hosted module self-tests passed;
- all 37 Claude tools and all 37 ChatGPT tools were invoked successfully;
- PostgreSQL, Valkey, discovery, replay, free-boundary, negative-case, status,
  and exact-deployment-commit checks passed;
- the planner selected `create-once` with the honest
  `duplicate-resistant` guarantee;
- the local Valkey integration gate gave exactly one owner to 100 concurrent
  claims, and a separate hosted 20-contender check also gave exactly one
  owner.

Observed Notion scenarios:

| Scenario | Result |
| --- | --- |
| Normal | One marker search, one create, one read-back, and one `caller_verified` transition |
| Identical replay | Replayed the same outer execution, searched the stable marker, skipped a second create, and retained one page |
| Concurrent workers | Ten callers produced one checkpoint owner and one page |
| Crash before create | The first generation was abandoned before any external call; a second generation recovered and created one page |
| Crash after create | The first generation recorded `external_result_uncertain`; after claim expiry, generation two found the existing marker and verified it without another create |

The final aggregate query returned exactly five rows—one per stable marker—with
`Verified` checked on every row. The checkpoint continued to report
`external_proof: false`; the Notion read-back, not the checkpoint, supplied the
external evidence.

Limitations:

- Notion creation did not expose provider idempotency, so the achieved
  guarantee is duplicate-resistant, not exactly once.
- The run observed immediate marker visibility. It did not inject a prolonged
  Notion search-consistency delay or a Notion-wide outage.
- The preview proved the specified connector and recipe versions at the
  observed time; it is not a future guarantee for changed tool contracts.

## Production promotion

The accepted runtime was promoted to the existing `agent-utility-lab`
production app, not a replacement app. A production-only Redis JSON
normalization issue was found by the hosted gate, corrected at the public
output boundary, and covered by a regression test before promotion.

Final release evidence:

- live backend version: `0.6.1`;
- final production commit:
  `d28fe0af12778b010c877ea69ddfc6e6de4b6046`;
- production deployment:
  `eef2bec1-d77b-41b1-9caf-03fdadec4866`;
- 206 automated tests, production build, Compose integration, container and
  secret scans, and both branch CI workflows passed;
- two repeated 24/24 preview self-test runs and the canonical authenticated
  production acceptance passed;
- all 37 Claude and all 37 ChatGPT direct tools were invoked;
- Official MCP Registry `0.6.1` is active and marked latest;
- payments remain disabled and all public modules remain free.

## Earlier production primitive checks

Environment: live Agent Enhancer Utilities direct tools backed by
`https://liberated.site/mcp?profile=core`, using opaque synthetic namespaces and 60-second
temporary state. No external record was created in these earlier checks.

These checks validate the coordination contracts used by the recipes. They do
not prove an external plugin's consistency, idempotency, or write behavior.

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

The most immediate missing state was not another rate or concurrency limiter.
It was an explicit distinction between:

- work claimed;
- an external result that is uncertain;
- external evidence reported by the caller;
- failure or compensation.

That evidence selected and led to the `0.6.0` implementation of
[Opaque Workflow Checkpoints](./OPAQUE_WORKFLOW_CHECKPOINTS.md). A
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

The isolated `0.6.0` preview subsequently exercised the deployed planner and
checkpoint against the controlled Notion write scenarios recorded above.

## Remaining vendor coverage

Before expanding this worked recipe to other capability shapes or vendors,
test against each exact external plugin/tool version:

- eventual-search delay;
- destination record removed after a sidecar stamp;
- unguarded external writer;
- changed tool schema or action annotations;
- uncertain send behavior for messaging tools that cannot be searched.
