---
name: guard-external-plugin-workflows
description: Plan and coordinate reliable workflows that combine Agent Enhancer Utilities with another plugin or external tool. Use for repeated, parallel, scheduled, quota-sensitive, freshness-sensitive, duplicate-sensitive, or high-consequence creates, updates, sends, refreshes, imports, and batch jobs where agents must select guards, verify downstream effects, recover from uncertain results, and state the guarantee honestly. Do not invoke for ordinary one-time low-risk reads or writes unless the user explicitly requests a reliability plan.
---

# Guard External Plugin Workflows

Use Agent Enhancer Utilities as a deliberate reliability sidecar. The external
plugin still performs the domain action. Never imply that installation alone
intercepts other plugins or creates a cross-plugin transaction.

## Decide whether to add the sidecar

Use this workflow when at least one condition is true:

- two or more workers may touch the same work or resource;
- a job is scheduled, resumed, replayed, or processed in batches;
- duplicate creates or sends would be harmful;
- a shared concurrency or API quota must be respected;
- one worker should own a refresh while peers reuse the result;
- a timeout could leave the external result uncertain;
- the user explicitly asks for a guarded plan or reliability assessment.

Abstain from coordination calls for an ordinary one-time low-risk read or
write. Explain the sidecar only when it affects the answer.

## Build the reliability contract

Before changing state, inspect the external plugin's available tool contract or
documentation. Determine:

- operation class: read, create, update, send, delete, refresh, or batch;
- whether duplicates are harmful;
- whether attempts can be parallel, scheduled, or retried;
- provider idempotency or atomic uniqueness support;
- destination search and its consistency;
- stable-marker, conditional-write, read-after-write, or delivery-status
  support;
- concurrency, rate, freshness, and expiry constraints;
- available verification and compensation.

Use only established capability facts. If a fact changes the safe plan and
cannot be discovered, state the assumption or stop before the external side
effect. Read
[references/reliability-contract.md](references/reliability-contract.md) for
the field definitions, profile selection, and guarantee matrix.

For a deterministic read-only dry run, pass the closed reliability contract to
`scripts/plan_workflow.py`. The script does not call either plugin or create
coordination state. A valid low-risk one-time contract returns a typed
`no-sidecar` decision.

For execution, prefer `scripts/on_demand.py`. It runs the same local selector
first. Low-risk work returns `local-abstention` with zero network calls.
Risk-bearing work checks exactly one hosted planner result before any selected
coordination call. Local and hosted plan drift fails closed.

## Create opaque identities

Create one stable logical operation identity from the operation class, source
identity, destination scope, and recipe version.

- Use a local HMAC-SHA-256 with a caller-controlled secret for sensitive or
  low-entropy identifiers.
- A plain SHA-256 is acceptable only for already opaque, non-sensitive,
  high-entropy identifiers.
- Send only the resulting opaque value to Agent Enhancer.
- Never send document text, messages, customer records, credentials, personal
  data, or raw external identifiers as coordination keys.
- Keep each Agent Enhancer `idempotency_key` stable only while recovering the
  identical sidecar request. Do not confuse it with the logical operation
  identity.

If workers cannot derive the same safe opaque identity, coordination cannot
reliably deduplicate them. Report that limitation.

## Select a profile

Choose the narrowest profile that covers the failure:

- `create-once`: lock, destination preflight, create, verify, then optional
  post-verification seen stamp;
- `update-safely`: lock, version re-read, update, verify, then release;
- `send-at-most-once`: provider idempotency when available; otherwise serialize
  senders and stop on an uncertain result;
- `refresh-if-stale`: freshness lease, negative cache when appropriate, shared
  rate gate, refresh, then freshness verification;
- `fan-out-bounded`: per-item guards and destination checks, semaphore, rate
  gate, optional post-verification seen stamps, and barrier before synthesis;
- `scheduled-run`: stable run identity, one run owner, bounded retries, and
  verified completion;
- `write-budget`: shared action limit when a supported bounded counter exists.
  Until it exists, do not simulate it with a lock or rate gate.

Read [references/recipes.md](references/recipes.md) only for the capability
shape involved in the current request.

## Activate tools only when selected

Do not persistently connect MCP for the skills-first path. Build the closed
contract, then run:

```sh
python scripts/on_demand.py plan --input contract.json
```

If the result is `local-abstention`, continue without Agent Enhancer. If the
result selects a sidecar, use only candidate tools present in its stages. Read
the public contract at `https://liberated.site/v1/tools/{slug}` before the
first invocation, then call the selected guard:

```sh
python scripts/on_demand.py invoke \
  --slug workflow-checkpoint \
  --input checkpoint.json \
  --idempotency-key stable_request_key_0001
```

The adapter allows the planner, checkpoint, and the coordination primitives
listed below. It rejects free text, credential-like fields, raw identifiers,
unknown tools, and missing idempotency identities before network access.
Derive identity fields locally as described above.

If the user asked only for analysis or design, stop after the plan. Invoke
stateful tools only when executing the authorized workflow. If an unknown fact
would change the safety boundary, state the assumption or stop. Do not force a
nearby tool.

Prefer:

- `workflow-guard-planner` for the hosted deterministic version-1 contract
  plan;
- `workflow-checkpoint` for generation-fenced `claimed`, uncertain,
  caller-verified, failed, and compensated recovery state around a material
  external side effect;
- `penny-lock` for one temporary resource owner;
- `global-seen-stamp` for atomic seen-or-mark state. A miss creates the stamp,
  so use it as a bounded claim or post-verification advisory cache, never as a
  read-only proof of external completion;
- `exactly-once-baton` for a one-use coordination capability, never as proof of
  the external action;
- `negative-cache-ticket` for a temporary typed lookup failure;
- `swarm-semaphore` for bounded parallel holders;
- `swarm-rate-gate` for a shared request budget;
- `barrier-bell` for fan-in after unique arrivals;
- `freshness-lease` for one renewable refresh owner.

Follow the live tool description over this summary.

The persistent Agent Enhancer MCP at `https://liberated.site/mcp` remains a
backward-compatible option for hosts that prefer discovery. It is not the
default for this skill because persistent connection metadata can add overhead
to unrelated low-risk tasks.

For a harmful create, send, delete, or other duplicate-sensitive external
effect, prefer a workflow checkpoint over representing completion with a lock,
stamp, or baton. Reuse an outer idempotency key only for the exact same
checkpoint request in the same generation. Use a fresh key for a new
generation, a new recovery decision, or any request made after checkpoint
expiry.

## Keep the call order safe

For an external write:

1. Acquire the selected coordination guard.
2. Re-check the destination through the external plugin.
3. Perform the external action.
4. Verify through the external plugin.
5. Record advisory seen or completion state only after verification.
6. Release temporary state when the described primitive supports release.

When using `workflow-checkpoint`, claim before the destination preflight,
transition to `external_result_uncertain` when an attempt may have occurred,
and transition to `caller_verified` only after an allowed evidence class is
actually observed. Do not begin a new external action when the remaining claim
time is within the published safety margin.

Do not hold a lock longer than its TTL. Do not release a guard owned by another
worker. A denied guard means stand down or wait; it does not prove the other
worker completed.

## Recover from uncertain results

Classify failures by where they occurred:

- **Before the external call:** retry the identical sidecar request according
  to its idempotency rules.
- **Definite external rejection:** correct only typed, safe-to-correct errors;
  otherwise stop.
- **Timeout or crash during/after the external call:** treat the result as
  uncertain. Search or query delivery status before any retry.
- **Found stable marker or delivery record:** verify it and finish without
  repeating the action.
- **Not found in an eventually consistent search:** wait within a bounded
  window and re-check. Do not claim absence is conclusive.
- **No search, delivery status, or provider idempotency:** stop and request
  review rather than blindly retrying a create, send, delete, or irreversible
  action.

Never write a seen stamp merely to escape uncertainty. If a workflow uses a
seen stamp as an early claim, report that a crash can suppress work until the
stamp expires and verify the destination before skipping on a later hit.

## Label the achieved guarantee

Use exactly one overall label, plus stage-specific labels when they materially
differ:

- `provider-idempotent`
- `duplicate-resistant`
- `concurrency-safe`
- `rate/concurrency-bounded`
- `best-effort`

Use `provider-idempotent` only when the destination itself transactionally
deduplicates or enforces uniqueness. Locks, stamps, leases, and batons cannot
raise a workflow to that label.

## Report the guarded workflow

End a material guarded workflow with this compact structure:

```text
Reliability profile:
Operation identity: <opaque hash prefix or "not established">
Guards used:
External verification:
Outcome: verified | skipped | blocked | uncertain | failed
Guarantee: <one approved label>
Residual risk:
Recovery or review:
```

For batches, also report attempted, already-seen, blocked, throttled, verified,
uncertain, failed, and awaiting-review counts. Do not infer prevented
duplicates from successful tool calls; distinguish observed evidence from
interpretation.
