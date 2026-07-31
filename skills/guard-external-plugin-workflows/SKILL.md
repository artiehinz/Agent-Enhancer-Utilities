---
name: guard-external-plugin-workflows
description: Plan and coordinate reliable workflows that combine Agent Enhancer Utilities with another plugin or external tool. Use for repeated, parallel, scheduled, quota-sensitive, freshness-sensitive, duplicate-sensitive, or high-consequence creates, updates, sends, refreshes, imports, and batch jobs where agents must select guards, verify downstream effects, recover from uncertain results, and state the guarantee honestly. Do not invoke for ordinary one-time low-risk reads or writes unless the user explicitly requests a reliability plan.
---

# Guard External Plugin Workflows

Use Agent Enhancer as an explicit reliability sidecar. The domain tool still
performs and verifies the external action. Never imply that this skill
intercepts another plugin or creates a cross-service transaction.

## Select or abstain

Use the sidecar for parallel, scheduled, replayable, quota-limited,
freshness-sensitive, or materially duplicate-sensitive work. Abstain for an
ordinary one-time low-risk operation.

Build the closed 17-field capability contract before changing state. Inspect
the domain tool for provider idempotency, stable-marker search, read-back,
delivery status, conditional writes, rate limits, and compensation. Use only
known facts; stop or state an assumption when an unknown fact changes safety.

Read [references/reliability-contract.md](references/reliability-contract.md)
for field definitions, opaque identity rules, guarantees, and recovery. Read
[references/recipes.md](references/recipes.md) only for the current operation
shape.

Run the local selector first:

```sh
python scripts/on_demand.py plan --input contract.json
```

`local-abstention` makes zero network calls. A risk-bearing plan checks exactly
one hosted planner result and returns a compact `execution_recipe`. Local and
hosted drift fails closed. Keep persistent MCP disconnected for this
skills-first path unless the host specifically requires it.

## Enforce the external-write boundary

For a material or irreversible create, update, send, or delete without
provider idempotency, use `workflow-checkpoint` whenever concurrent workers,
scheduled execution, or retries are possible. A lock, stamp, lease, or baton
alone is insufficient because it cannot resolve a committed write whose
response was lost.

Execute a checkpointed write in this order:

1. Derive one stable opaque operation identity locally.
2. Claim `workflow-checkpoint`; stand down on
   `write_execution_in_progress`.
3. Preflight the destination by stable marker, current version, or delivery
   status when available.
4. Transition `claimed -> external_attempt_started` immediately before the
   external call.
5. Perform the domain action once.
6. On a lost response, transition to `external_result_uncertain` before
   reconciliation.
7. Reconcile through stable-marker search, delivery status, or read-back.
8. Transition to `caller_verified` only after allowed evidence is observed.

Never reset an attempt-started or uncertain checkpoint to `claimed`. Never
blindly retry an uncertain external write. If reconciliation is inconclusive,
leave it uncertain and stop for review. Every checkpoint result has
`external_proof: false`; it records caller assertions, not provider proof.

Use a stable outer idempotency key only to recover the identical checkpoint
request in the same generation. Use a new key for a new transition,
generation, or post-expiry decision. Do not start an external action within
the live checkpoint's published expiry safety margin.

## Use only selected tools

Invoke only tools named by the plan. Read the live contract at
`https://liberated.site/v1/tools/{slug}` before the first invocation.

```sh
python scripts/on_demand.py invoke \
  --slug workflow-checkpoint \
  --input checkpoint.json \
  --idempotency-key stable_request_key_0001
```

Use:

- `workflow-checkpoint` for harmful external-write ownership, attempt
  boundaries, uncertainty, reconciliation, and verification;
- `penny-lock` for lower-risk temporary ownership and scheduled/read
  coordination, never as the only guard for an uncertain duplicate-sensitive
  write;
- `freshness-lease` for one refresh owner;
- `swarm-semaphore` and `swarm-rate-gate` for shared concurrency and request
  budgets;
- `barrier-bell` for verified fan-in;
- `global-seen-stamp` only as an advisory claim or post-verification cache;
- `exactly-once-baton` for one-use coordination, not external completion;
- `negative-cache-ticket` for a temporary typed lookup failure.

If the user asked only for analysis or design, stop after planning. Never send
payloads, messages, documents, credentials, personal data, or raw external
identifiers to Agent Enhancer.

## Report honestly

Use one guarantee label: `provider-idempotent`, `duplicate-resistant`,
`concurrency-safe`, `rate/concurrency-bounded`, or `best-effort`. Use
`provider-idempotent` only when the destination transactionally enforces it.

End material work with:

```text
Reliability profile:
Operation identity: <opaque prefix or not established>
Guards used:
External verification:
Outcome: verified | skipped | blocked | uncertain | failed
Guarantee:
Residual risk:
Recovery or review:
```

For batches, also report attempted, already-seen, blocked, throttled,
verified, uncertain, failed, and awaiting-review counts. Successful sidecar
calls alone do not prove a prevented duplicate or a completed domain action.
