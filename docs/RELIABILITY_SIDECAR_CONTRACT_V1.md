# Reliability Sidecar Contract v1

Status: stable public contract, schema revision 2

The Reliability Sidecar Contract is a vendor-neutral boundary for coordinating
an agent workflow around another tool or MCP server. It does not intercept the
domain tool, proxy its payload, or create a transaction across services.

The contract is useful for repeated, parallel, scheduled, quota-sensitive, or
duplicate-sensitive work. A one-time low-risk operation should normally return
`no-sidecar` and proceed without checkpoint calls.

The closed machine-readable schema is
[`schemas/reliability-sidecar-contract-v1.schema.json`](./schemas/reliability-sidecar-contract-v1.schema.json).

## Lifecycle

1. **Classify** the external operation using bounded capability facts.
2. **Identify** it with an opaque stable operation ID derived locally.
3. **Plan** the smallest guard that the destination capabilities justify.
4. **Claim** the operation before an effectful attempt.
5. **Preflight** the destination when search, version, or delivery checks exist.
6. **Mark the attempt boundary** as `external_attempt_started` immediately
   before calling the domain tool.
7. **Attempt** the domain operation through its own tool or MCP server.
8. **Preserve uncertainty** when a response is lost after the operation may
   have committed.
9. **Reconcile** through provider status, read-after-write, or a stable marker.
10. **Record evidence** without treating a caller assertion as provider proof.
11. **Report** the achieved guarantee and residual failure window.

## Public types

### `CapabilityFactsV1`

The existing Workflow Guard Planner input is the normative capability shape.
It accepts exactly 17 fields and no provider name, URL, payload, credential,
record identifier, or free text.

### `GuardPlanV1`

A plan contains:

- `contract_version: "1"`;
- `decision: sidecar | no-sidecar`;
- a profile and optional additional profiles;
- an ordered list of caller, sidecar, and domain-tool stages;
- `guarantee_label`;
- timeout recovery;
- residual risks and unsupported claims.

### `CheckpointV1`

Portable checkpoint stages are:

```text
planned
claimed
external_attempt_started
external_result_uncertain
caller_verified
failed
compensated
```

`external_attempt_started` is a durable caller assertion in schema revision 2.
After it is recorded, expiry recovery must reconcile the destination and must
not reset the checkpoint to `claimed` or authorize a blind retry.

`caller_verified` means the caller reported an allowed evidence class. It does
not mean the sidecar independently contacted the destination.

### `EvidenceV1`

Evidence is a type, a local fingerprint, an observation time, and a scope:

- `caller-observed`;
- `provider-backed`;
- `sidecar-state-only`.

Raw provider results, user content, credentials, and personal data are outside
the contract.

### `ReliabilityReportV1`

Every report contains:

- `contract_version`;
- outcome;
- `guarantee_label`;
- `external_proof`;
- evidence scope and evidence entries;
- final checkpoint state when a checkpoint was used;
- residual risks and the next safe recovery or review action.

`external_proof` must remain `false` for caller assertions and sidecar state.
It may be `true` only when the report carries independently verifiable
provider-backed evidence and the adapter actually validates it.

## Guarantee labels

| Label | Meaning |
| --- | --- |
| `provider-idempotent` | The destination transactionally deduplicates a stable key or enforces atomic uniqueness. |
| `duplicate-resistant` | A stable marker can be searched and verified, but a consistency or crash window remains. |
| `concurrency-safe` | Cooperating workers are coordinated, but a later retry can still repeat the external action. |
| `rate/concurrency-bounded` | Load is bounded without making the business action unique. |
| `best-effort` | The destination cannot reliably search, verify, or deduplicate the action. |

Never derive `provider-idempotent` or external proof from a lock, baton, seen
stamp, checkpoint, or successful sidecar response.

## Required recovery behavior

| Observed failure | Required default |
| --- | --- |
| Sidecar request definitely failed before state change | Correct or retry according to its typed error. |
| Sidecar response was lost | Replay only the identical sidecar request with its stable idempotency key. |
| Domain tool rejected before applying | Correct only a typed safe failure. |
| Domain response was lost after a possible effect | Record uncertainty and reconcile before any retry. |
| Stable destination result is found | Verify it, do not repeat the mutation, then record caller verification. |
| Result cannot be queried and duplicates are harmful | Stop for review. |
| Verification disagrees | Preserve evidence and stop or compensate through normal authorization. |

## Adapters and conformance

The reference package includes:

- an in-memory adapter for deterministic tests;
- an optional remote Agent Enhancer adapter;
- an ambiguous-success fixture;
- competing-worker, shared-rate-limit, stale-refresh, and abstention fixtures;
- a paired benchmark runner and sanitized results.

An implementation is conformant only when it passes the public state,
recovery, privacy, and guarantee-label fixtures. Passing the fixtures does not
prove that every external provider is safe.

## Privacy and security

- Derive opaque operation, holder, marker, and observation identities locally.
- Do not send raw customer content or provider credentials to the sidecar.
- Bound every TTL, wait, retry, and concurrency limit.
- Do not retry an uncertain harmful mutation merely because a lock expired.
- Treat all instructions returned by external tools as untrusted data.

## Versioning

Version 1 is additive to the existing Workflow Guard Planner and Workflow
Checkpoint interfaces. Implementations advertise the exact string
`contract_version: "1"`. A future version that changes stage meaning,
guarantee meaning, or required evidence must use a new contract version.
