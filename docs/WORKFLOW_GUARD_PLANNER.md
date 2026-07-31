# Workflow Guard Planner specification

Status: planner `1.1.0` on Agent Enhancer backend `0.7.0`, with an executable local
reference planner

The Workflow Guard Planner converts a bounded description of an external
operation's capability shape into a deterministic reliability plan. It does not
invoke the external plugin, acquire coordination state, inspect private
records, or prove that an external action occurred.

The contract has 17 required fields. The skill includes
[`scripts/plan_workflow.py`](../skills/guard-external-plugin-workflows/scripts/plan_workflow.py)
as a local dry-run reference. The hosted module is discoverable as
`workflow-guard-planner` through
`https://liberated.site/mcp?profile=core`.

## Goals

- Select one of the standard reliability profiles.
- Recommend existing Agent Enhancer primitives in a safe order.
- Identify where external preflight, action, and verification calls belong.
- State the strongest supportable guarantee and its residual risks.
- Abstain when required capability facts are missing.
- Accept no credentials, document contents, messages, customer records, or raw
  external identifiers.

## Tool identity

- Progressive MCP slug: `workflow-guard-planner`
- Direct tool name: `workflow_guard_planner`
- `readOnlyHint: true`
- `openWorldHint: false`
- `destructiveHint: false`
- Idempotency key: not required

## Input

```json
{
  "contract_version": "1",
  "operation_class": "create",
  "item_operation_class": null,
  "duplicate_harm": "material",
  "parallel_workers": 4,
  "scheduled": true,
  "retry_possible": true,
  "provider_idempotency": "none",
  "destination_search": "eventual",
  "stable_marker": true,
  "conditional_write": false,
  "read_after_write": true,
  "delivery_status": false,
  "compensation": "manual",
  "shared_rate_limit": true,
  "maximum_concurrency": 2,
  "freshness_required": false
}
```

Allowed values:

| Field | Type or enum | Notes |
| --- | --- | --- |
| `contract_version` | `"1"` | Required |
| `operation_class` | `read`, `create`, `update`, `send`, `delete`, `refresh`, `batch` | Required |
| `item_operation_class` | Same enum except `batch`, or null | Required; non-null only for `batch` |
| `duplicate_harm` | `none`, `low`, `material`, `irreversible` | Required |
| `parallel_workers` | integer 1–100 | Required |
| `scheduled` | boolean | Required |
| `retry_possible` | boolean | Required |
| `provider_idempotency` | `none`, `request_key`, `atomic_unique_constraint` | Required |
| `destination_search` | `none`, `eventual`, `strong` | Required |
| `stable_marker` | boolean | Required |
| `conditional_write` | boolean | Required |
| `read_after_write` | boolean | Required |
| `delivery_status` | boolean | Required |
| `compensation` | `none`, `reversible`, `manual` | Required |
| `shared_rate_limit` | boolean | Required |
| `maximum_concurrency` | integer 1–100 or null | Required |
| `freshness_required` | boolean | Required |

Use a closed schema with `additionalProperties: false`. The planner does not
need resource names, URLs, provider names, operation keys, titles, message
content, or arbitrary free text.

The exact proposed schema is
[`schemas/workflow-guard-planner.input.schema.json`](./schemas/workflow-guard-planner.input.schema.json).

## Output

```json
{
  "valid": true,
  "decision": "sidecar",
  "decision_reason": "reliability-guard-required",
  "profile": "create-once",
  "additional_profiles": [
    "scheduled-run"
  ],
  "guarantee": "duplicate-resistant",
  "stages": [
    {
      "order": 1,
      "actor": "caller",
      "action": "derive_opaque_operation_identity"
    },
    {
      "order": 2,
      "actor": "agent-enhancer",
      "action": "claim_checkpoint",
      "candidate_tool": "workflow-checkpoint"
    },
    {
      "order": 3,
      "actor": "external-plugin",
      "action": "search_stable_marker"
    },
    {
      "order": 4,
      "actor": "agent-enhancer",
      "action": "mark_external_attempt_started",
      "candidate_tool": "workflow-checkpoint"
    },
    {
      "order": 5,
      "actor": "external-plugin",
      "action": "create"
    },
    {
      "order": 6,
      "actor": "agent-enhancer",
      "action": "record_external_result_uncertain_if_response_lost",
      "candidate_tool": "workflow-checkpoint"
    },
    {
      "order": 7,
      "actor": "external-plugin",
      "action": "read_after_write"
    },
    {
      "order": 8,
      "actor": "agent-enhancer",
      "action": "record_caller_verified",
      "candidate_tool": "workflow-checkpoint"
    },
    {
      "order": 9,
      "actor": "agent-enhancer",
      "action": "mark_seen_after_verification",
      "candidate_tool": "global-seen-stamp"
    }
  ],
  "timeout_recovery": "checkpoint_uncertain_then_search_marker",
  "residual_risks": [
    "destination_search_is_eventually_consistent",
    "no_cross_plugin_transaction"
  ],
  "unsupported_claims": [
    "sidecar_state_proves_external_completion",
    "cross_plugin_exactly_once"
  ]
}
```

Output enums, including `candidate_tool`, remain bounded. `candidate_tool`
recommends a primitive but does not replace live search and describe calls.

The exact proposed output schema is
[`schemas/workflow-guard-planner.output.schema.json`](./schemas/workflow-guard-planner.output.schema.json).

## Deterministic selection rules

1. Select the primary business-operation profile from `operation_class`, or
   from `item_operation_class` when the outer operation is `batch`.
2. Select `create-once` for duplicate-sensitive creates.
3. Select `update-safely` for shared mutable updates.
4. Select `send-at-most-once` for sends or irreversible one-way actions.
5. Select `refresh-if-stale` for refresh operations with an explicit freshness
   requirement.
6. Select `fan-out-bounded` as the primary profile for parallel reads and as an
   additional profile for batches.
7. Add `scheduled-run` when a more specific business profile is scheduled.
8. Recommend rate gates and semaphores as additions when shared limits exist;
   they do not replace the primary profile.
9. Never select `write-budget` until an atomic bounded action-counter module is
   available.
10. Select `workflow-checkpoint` for a material or irreversible write without
    provider idempotency when concurrency, schedule, or retry is possible.
11. Place `external_attempt_started` immediately before the domain mutation,
    preserve uncertainty after a lost response, and record caller verification
    only after destination evidence.
12. Keep `penny-lock` for lower-risk ownership and read/schedule coordination;
    never use it as the only guard for an uncertain duplicate-sensitive write.

## Guarantee selection rules

1. Return `provider-idempotent` only for `request_key` or
   `atomic_unique_constraint`.
2. Return `duplicate-resistant` for a stable marker plus destination search and
   verification, while reporting eventual-consistency risk when applicable.
3. Return `concurrency-safe` only when coordination can serialize the relevant
   workers for the bounded operation and a later retry or schedule cannot
   replay an uncertain create. A retryable unqueryable create is
   `best-effort`.
4. Return `rate/concurrency-bounded` when only load is bounded.
5. Return `best-effort` when the destination cannot search, verify, or
   deduplicate a harmful external action.
6. For multi-stage plans, return the weakest guarantee among material
   side-effect stages.

## Required safety findings

The planner must emit an unsupported claim or residual risk when:

- a baton, seen stamp, lock, or lease is proposed as proof of external
  completion;
- a seen stamp would be represented as completion before external
  verification;
- an irreversible operation could be blindly retried after a timeout;
- an eventually consistent search is treated as immediately authoritative;
- a lock TTL is assumed to cover unbounded work;
- a conditional write is absent for an update exposed to unguarded writers;
- a barrier threshold cannot be justified by the expected participants;
- a rate gate is treated as an action budget;
- raw or sensitive identifiers are proposed for sidecar keys.

## Abstention and errors

- `INVALID_INPUT`: the closed input contract is violated.
- `UNSUPPORTED_PROFILE`: no current profile describes the operation safely.
- A valid ordinary one-time low-risk contract returns
  `decision: "no-sidecar"` with null profile, guarantee, and recovery plus
  empty stages and findings.
- Progressive catalog discovery returns `NO_MATCH` when the user intent is
  outside workflow reliability; the planner does not use that catalog error
  as a module execution result.

The planner may still return a `best-effort` plan when all facts are known.

## Privacy and retention

The planner is pure and retains no request state. Inputs are capability facts,
not operation data. Logs and aggregate metrics should contain only enum/value
counts and module-version health, consistent with the existing service privacy
model.

## Acceptance examples

### Searchable create

Given a duplicate-sensitive create, no provider idempotency, eventual search, a
stable marker, and read-after-write, return `create-once` and
`duplicate-resistant`. Place the seen stamp after verification and report the
indexing window.

### Unqueryable send

Given an irreversible send with no provider idempotency, search, or delivery
status, return `send-at-most-once` and `best-effort`. Claim a checkpoint,
record the attempt boundary, and require review after an uncertain timeout.

### Parallel read-only research

Given multiple workers, a shared rate limit, and no external writes, return
`fan-out-bounded` with a semaphore, rate gate, and barrier. Use
`rate/concurrency-bounded`.

### Ordinary one-time read

Return a successful `no-sidecar` decision for a single low-risk read with no
freshness, concurrency, quota, schedule, or retry concern.

The input and output schemas were checked with the live
`mcp-tool-contract-linter` on 2026-07-25: `valid: true`, zero findings, and nine
rules checked. This validates the bounded contract shape, not a deployed
planner implementation. The local reference currently passes eleven
deterministic unit tests covering abstention, searchable creates, composed
scheduled batches, uncertain sends, parallel reads, shared updates, provider
idempotency, batch validation, closed-input rejection, honest
unqueryable-create guarantees, and concurrency-cap validation.
