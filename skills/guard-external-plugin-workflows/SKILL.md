---
name: guard-external-plugin-workflows
description: Plan and coordinate reliable workflows that combine Agent Enhancer Utilities with another plugin or external tool. Use for repeated, parallel, scheduled, quota-sensitive, freshness-sensitive, duplicate-sensitive, or high-consequence creates, updates, sends, refreshes, imports, and batch jobs where agents must select guards, verify downstream effects, recover from uncertain results, and state the guarantee honestly. Do not invoke for ordinary one-time low-risk reads or writes unless the user explicitly requests a reliability plan.
---

# Guard External Plugin Workflows

Use Agent Enhancer as a reliability sidecar. The domain tool still performs
and verifies the external action. Never imply a cross-service transaction.

## Select or abstain

Use the sidecar for parallel, scheduled, replayable, quota-limited,
freshness-sensitive, or materially duplicate-sensitive work. Abstain for an
ordinary one-time low-risk operation.

Build the closed 17-field capability contract from known provider facts. Read
[references/reliability-contract.md](references/reliability-contract.md) only
when a field or guarantee is unclear. If the contract already exists, do not
load that reference. Read [references/recipes.md](references/recipes.md) only
when the external operation shape itself is unclear.

Resolve this skill's directory once, then run its local selector:

```sh
python <skill-dir>/scripts/on_demand.py plan --input contract.json
```

`local-abstention` makes zero network calls. A risk-bearing plan checks exactly
one hosted plan and returns `execution_recipe`. Local/hosted drift fails
closed. Keep persistent MCP disconnected for this skills-first path.

## Enforce the external-write boundary

For a material or irreversible write without provider idempotency, require
`workflow-checkpoint` when concurrency, schedules, or retries are possible. A
simple lock is insufficient.

When `execution_recipe.required_guard` is `workflow-checkpoint`, read
[references/checkpoint-execution.md](references/checkpoint-execution.md) and
use the bundled `checkpoint-blueprint` and `checkpoint-step` commands. Do not
inspect the adapter source, tests, or live schema during normal execution.
Generate one blueprint before spawning workers; give every worker the same
file and a distinct holder label.

Only a holder whose claim reports `acquired` or `reused` may continue. Record
`external_attempt_started` immediately before the domain action. After a lost
response, record uncertainty, reconcile through the destination, and never
blindly retry. Record `caller_verified` only after destination evidence.
Every checkpoint result has `external_proof: false`.

## Use only selected tools

Invoke only tools named by the plan through the validated adapter:

```sh
python <skill-dir>/scripts/on_demand.py invoke \
  --slug workflow-checkpoint \
  --input checkpoint.json \
  --idempotency-key stable_request_key_0001
```

Use `penny-lock` only for lower-risk ownership or scheduled/read coordination.
Use leases, semaphores, rate gates, barriers, stamps, batons, and negative
cache tickets only when the plan selects them. A stamp or baton never proves
external completion.

If the user asked only for analysis or design, stop after planning. Never send
payloads, messages, documents, credentials, personal data, or raw external
identifiers to Agent Enhancer.

## Report honestly

End material work with the selected guarantee and residual risk:

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

Successful sidecar calls alone do not prove a prevented duplicate or a
completed domain action.
