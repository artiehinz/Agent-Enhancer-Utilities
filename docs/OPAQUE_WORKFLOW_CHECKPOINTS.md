# Opaque Workflow Checkpoints

Status: live; attempt-boundary revision for Agent Enhancer backend `0.7.0`

The sidecar needs to distinguish ownership, external uncertainty, and
caller-observed verification. Existing locks, leases, stamps, and batons do not
represent that lifecycle:

- a lock or lease represents temporary ownership;
- a seen-stamp miss creates state before any downstream work;
- a baton represents one consumption;
- none proves that an external plugin completed an action.

Opaque Workflow Checkpoints provide bounded coordination state without
claiming a transaction or external proof.

## Proposed stages

| Stage | Meaning |
| --- | --- |
| `claimed` | One caller temporarily owns recovery or execution for the opaque operation |
| `external_attempt_started` | The caller durably records the boundary immediately before an external mutation |
| `external_result_uncertain` | The caller reports that an external attempt may have occurred but cannot yet be verified |
| `caller_verified` | The caller reports one allowed class of external evidence |
| `failed` | The caller reports a definite failure; recovery is allowed only when the checkpoint was created with `retry_failed: true` |
| `compensated` | The caller reports that an authorized recovery action was verified |

The service must return `external_proof: false` for every stage. It stores and
coordinates caller assertions; it does not contact or attest to the external
plugin.

## Proposed operations

### `workflow-checkpoint-claim`

Atomically create or recover one active claim for an opaque workflow key.

Input:

- opaque namespace, workflow key, and holder;
- claim TTL from 60 to 3,600 seconds;
- state TTL from 60 to 3,600 seconds;
- standard outer idempotency key.

Output includes:

- whether the claim was acquired or recovered;
- a typed claim disposition, including `write_execution_in_progress` for a competing caller;
- whether destination inspection is required before another external action;
- current stage and monotonically increasing generation;
- claim and state expiry;
- workflow hash;
- `external_proof: false`.

### `workflow-checkpoint-transition`

Atomically transition the current generation while owned by the active holder.

Input:

- opaque namespace, workflow key, and holder;
- expected generation;
- `from_stage` and `to_stage`;
- opaque inner observation key to deduplicate the reported transition;
- an allowed evidence enum when entering `caller_verified` or `compensated`;
- optional HMAC-SHA-256 evidence fingerprint;
- standard outer idempotency key.

Allowed evidence enums:

- `provider_idempotency_result`;
- `atomic_unique_result`;
- `stable_marker_readback`;
- `conditional_write_result`;
- `delivery_status`;
- `durable_result_readback`;
- `manual_review`.

Do not accept response bodies, record content, provider URLs, messages,
credentials, or arbitrary free text.

### `workflow-checkpoint-status`

Read a known opaque checkpoint without acquiring or transitioning it. The tool
must never list keys or holders and must not reveal a stored holder value or
evidence fingerprint. It may report the bounded evidence enum and whether a
fingerprint exists.

### `workflow-checkpoint-abandon`

Release a `claimed` checkpoint only when the caller asserts that the external
action did not start. This operation must be unavailable from
`external_attempt_started` or `external_result_uncertain`. Abandonment is not allowed to erase
`caller_verified`, `failed`, or `compensated` evidence.

## Transition rules

Allowed:

- absent or expired → `claimed`;
- `claimed` → `external_attempt_started`;
- `claimed` → `external_result_uncertain`;
- `claimed` → `caller_verified`;
- `claimed` → `failed`;
- `external_attempt_started` → `caller_verified`;
- `external_attempt_started` → `external_result_uncertain`;
- `external_attempt_started` → `failed`;
- `external_attempt_started` → `compensated`;
- `external_result_uncertain` → `caller_verified`;
- `external_result_uncertain` → `failed`;
- `external_result_uncertain` → `compensated`;
- `failed` → `claimed` only under a new generation when the recipe explicitly
  permits retry;
- expired claim with nonterminal state → a new recovery claim.

Disallowed:

- `caller_verified` → `claimed`;
- `compensated` → `claimed`;
- any transition under a stale generation;
- changing the transition body under a reused idempotency or observation key;
- abandoning after the caller recorded that an external action started or
  might have started.

`caller_verified` and `compensated` are final. `failed` is retry-gated rather
than unconditionally terminal. Final stages remain readable until state TTL
expiry. The module is not a permanent audit log.

## Recovery behavior

When a new worker recovers an expired `claimed` checkpoint:

1. inspect the external destination before acting;
2. if the record or delivery can be verified, transition to
   `caller_verified`;
3. if the result may exist but cannot be queried, transition to
   `external_result_uncertain` and stop harmful retries;
4. if absence is strongly established and the recipe allows retry, claim a new
   generation and continue;
5. preserve the standard guarantee label; checkpoint state cannot raise it.

When recovering `external_attempt_started` or `external_result_uncertain`, the
stage is preserved. The worker must reconcile the destination and must not
repeat a harmful action merely because the claim expired.

## Privacy and security

- Send only opaque, high-entropy identifiers.
- Use a local HMAC for sensitive or low-entropy source identities.
- Never store external content or secrets.
- The service applies a domain-separated keyed HMAC before storing workflow,
  holder, or observation identities. It never stores raw caller identifiers.
- Do not expose key or holder enumeration.
- Bind state transitions to the current holder and generation.
- Use a stable outer idempotency key only to recover the exact same request in
  the same generation. Use a fresh key for a new generation, recovery
  decision, or request after checkpoint expiry; otherwise the longer-lived
  PostgreSQL execution ledger can correctly replay an older request instead of
  mutating the new checkpoint.
- Use inner observation keys to deduplicate one caller-observed transition.
- Keep TTLs bounded and choose the shortest practical duration.
- Claim and state TTL configuration is fixed for the record lifetime.
- Valkey Lua uses server time for expiry and fencing decisions.
- v1 does not renew a claim. Do not begin an external action inside the
  published 15-second expiry safety margin; choose a claim TTL longer than the
  bounded external deadline or do not use the checkpoint.

## Relationship to guarantee labels

| Checkpoint evidence | Maximum label it can support by itself |
| --- | --- |
| `claimed` | `best-effort` |
| `external_attempt_started` | `best-effort` |
| `external_result_uncertain` | `best-effort` |
| `caller_verified` with read-back | Depends on destination capability; never above `duplicate-resistant` without provider idempotency |
| `caller_verified` with provider idempotency result | `provider-idempotent`, only because of the provider contract |
| `failed` or `compensated` | No uniqueness guarantee |

The checkpoint records why the caller chose a label; it does not manufacture
the guarantee.

## Acceptance criteria

- Competing claims yield one active owner.
- Identical claim and transition retries replay deterministically.
- Reusing a key with a changed body returns a typed conflict.
- Stale generations cannot transition state.
- A checkpoint cannot skip directly from absent to `caller_verified`.
- Only the active holder can transition or abandon.
- `external_result_uncertain` cannot be abandoned.
- `external_attempt_started` survives expiry recovery and cannot be abandoned.
- No terminal state can be overwritten before expiry.
- Status is read-only and reveals no raw holder.
- Expiry permits bounded recovery without implying that the external action did
  or did not occur.
- Every output includes `external_proof: false`.
- A checkpoint stores at most 16 generations and 32 observation results.
- Application and Valkey restart behavior is tested; production must preserve
  the documented persistence and no-eviction boundary or describe the module
  as ephemeral coordination.
