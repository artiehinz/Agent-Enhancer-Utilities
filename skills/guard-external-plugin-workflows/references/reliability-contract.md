# Reliability contract

Use this contract to describe the capability shape of an external operation
before selecting Agent Enhancer guards. Record facts and explicit assumptions;
do not include raw records, credentials, messages, or personal data.

## Contents

1. Contract fields
2. Profile selection
3. Guarantee matrix
4. Guard invariants
5. Recovery rules
6. Standard outcome

## Contract fields

```yaml
contract_version: "1"
operation_class: read | create | update | send | delete | refresh | batch
item_operation_class: null | read | create | update | send | delete | refresh
duplicate_harm: none | low | material | irreversible
parallel_workers: 1
scheduled: false
retry_possible: false
provider_idempotency: none | request_key | atomic_unique_constraint
destination_search: none | eventual | strong
stable_marker: false
conditional_write: false
read_after_write: false
delivery_status: false
compensation: none | reversible | manual
shared_rate_limit: false
maximum_concurrency: null
freshness_required: false
```

This is the normalized input shape used by the local read-only planner. Use a
non-null `item_operation_class` only when the outer class is `batch`. The exact
closed schema is
[`../../docs/schemas/workflow-guard-planner.input.schema.json`](../../docs/schemas/workflow-guard-planner.input.schema.json).
Keep human-readable assumptions in the local report, not in the planner input.

- `provider_idempotency: request_key` means the destination transactionally
  replays or deduplicates a
  documented stable key.
- `atomic_unique_constraint` means the destination rejects a duplicate identity
  in the same transaction as creation.
- `destination_search: eventual` cannot prove immediate absence after an
  uncertain write.
- `stable_marker` means a caller-chosen opaque identity can be stored and later
  queried or read back.
- `conditional_write` includes a documented version, ETag, or compare-and-swap
  precondition enforced by the destination.
- `delivery_status` must identify the attempted send, not merely show general
  service availability.

## Profile selection

| Need | Profile | Required external facts |
| --- | --- | --- |
| Avoid duplicate records | `create-once` | Stable identity; search or provider idempotency |
| Protect a shared mutable record | `update-safely` | Re-read; preferably conditional write and read-back |
| Avoid duplicate irreversible sends | `send-at-most-once` | Prefer provider idempotency or delivery status |
| Refresh shared stale data once | `refresh-if-stale` | Freshness rule and verifiable refresh result |
| Process items concurrently then synthesize | `fan-out-bounded` | Stable item identities and known fan-in threshold |
| Run one scheduled job instance | `scheduled-run` | Stable schedule/run identity |
| Cap total attempted writes | `write-budget` | A supported atomic action counter; otherwise unavailable |

Multiple profiles may be composed. Report stage-specific guarantees and choose
the weakest material stage as the overall guarantee.

## Guarantee matrix

| Destination capability | Allowed guarantee |
| --- | --- |
| Documented transactional idempotency key | `provider-idempotent` |
| Atomic unique constraint for the operation identity | `provider-idempotent` |
| Strong search plus stable marker and verified read-back | `duplicate-resistant` |
| Eventual search plus stable marker and verified read-back | `duplicate-resistant`, with an indexing window |
| Lock plus external verification but no durable marker | `concurrency-safe` |
| Semaphore or rate gate around independent actions | `rate/concurrency-bounded` |
| No reliable search, marker, delivery status, or idempotency | `best-effort` |

Rules:

- Never derive `provider-idempotent` from Agent Enhancer state.
- A lock prevents overlapping owners only during its valid TTL.
- A retryable or scheduled create without provider idempotency, a queryable
  stable marker, or strong absence evidence remains `best-effort`;
  serializing workers cannot prevent a later duplicate after an uncertain
  result.
- A seen stamp is atomic seen-or-mark state. A miss creates the stamp, and
  neither a hit nor a miss proves the external action.
- A baton proves one consumption, not completion of the following action.
- Verification improves evidence but does not make two services transactional.
- If a multi-stage workflow has different guarantees, do not hide the weaker
  irreversible stage behind a stronger read-only stage.

## Guard invariants

1. Derive the logical operation identity before acquiring state.
2. Use only opaque identifiers with Agent Enhancer.
3. Reuse a sidecar idempotency key only for the identical sidecar request.
4. Use `workflow-checkpoint` for a material duplicate-sensitive write without
   provider idempotency when parallel, scheduled, or retry execution is
   possible. A simple lock is not sufficient.
5. Re-check destination state after obtaining the guard.
6. Record `external_attempt_started` immediately before the external call.
7. Mark advisory seen or completion state only after external verification,
   unless the stamp is explicitly being used as a temporary claim with
   crash-delay risk.
8. Treat denied or expired coordination as state, not business completion.
9. Preserve attempt-started and uncertain state across recovery.
10. Bound every wait, retry, TTL, and concurrency limit.
11. Stop blind retries after an uncertain external write.
12. Use live tool manifests for schemas and limits.
13. Report assumptions and residual risk.

## Recovery rules

| Failure point | Default recovery |
| --- | --- |
| Sidecar call definitely failed before state change | Correct or retry per typed error |
| Sidecar result uncertain | Replay the identical request with its stable idempotency key |
| External tool rejected without applying | Correct only a typed, safe error |
| External tool timed out | Query by provider key, stable marker, or delivery ID |
| Eventual search returns absent after timeout | Wait a bounded consistency window and re-check |
| External result exists and verifies | Do not repeat; finish and record completion |
| Result cannot be queried | Stop and send to review for harmful or irreversible actions |
| Verification disagrees | Preserve evidence, release only owned guards, and escalate |

After `external_attempt_started`, recovery must reconcile or stop for review;
it must not abandon the checkpoint or repeat the domain mutation merely
because the claim expired.

## Standard outcome

```yaml
reliability_profile: create-once
operation_identity: "sha256-prefix-or-not-established"
guards_used: []
external_verification: "what the destination proved"
outcome: verified | skipped | blocked | uncertain | failed
guarantee: provider-idempotent | duplicate-resistant | concurrency-safe | rate/concurrency-bounded | best-effort
residual_risk: "specific remaining failure window"
recovery_or_review: "next safe action or none"
batch_counts:
  attempted: 0
  already_seen: 0
  blocked: 0
  throttled: 0
  verified: 0
  uncertain: 0
  failed: 0
  awaiting_review: 0
```

Omit `batch_counts` for non-batch work. Do not expose the full operation HMAC
when a short prefix is enough for the user's local report.
