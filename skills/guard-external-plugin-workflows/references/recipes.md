# External plugin reliability recipes

Select recipes by capability shape. Vendor names are examples, not guarantees
that a current connector exposes every assumed capability. Inspect the live
tool contract before executing.

## Contents

1. Searchable page or database creation
2. Shared document or model update
3. Scheduled research import
4. Parallel research and one synthesis
5. Email or messaging send
6. Failure rehearsal

## Searchable page or database creation

Use for a Notion-like database, knowledge base, CRM, issue tracker, or file
store that can retain and query a stable marker.

Assumptions:

- the source item has a stable identity;
- the destination can store an opaque import marker;
- search or direct lookup is available;
- the created record can be read back.

Plan:

1. Derive `operation_hmac = HMAC(shared local coordination secret,
   canonical(source identity, destination scope, "create", recipe version))`
   locally.
2. Claim `workflow-checkpoint` with the opaque operation identity.
3. Search the destination for the stored marker after acquiring the claim.
4. If found, verify the record and skip creation.
5. If absence is sufficiently established, record
   `external_attempt_started` immediately before the create. Then create the
   record with the marker in a queryable field. Document the destination's
   search consistency. This
   is not an atomic `create-if-absent` unless the destination explicitly
   supplies that primitive.
6. Read it back and verify the marker and required fields.
7. Optionally write `global-seen-stamp` only after successful verification.
   Treat it as an advisory cache; a later hit still requires destination
   verification before skipping.
8. Record `caller_verified` with stable-marker read-back evidence.

Crash recovery:

- Before the attempt-boundary transition: abandon safely or recover after
  expiry and repeat the preflight.
- During or after create: record uncertainty, then search for the marker
  without retrying the create.
- Eventual search absence: wait a bounded indexing window and search again.
- Search still inconclusive: stop for review if a duplicate is material.

Guarantee:

- `provider-idempotent` only with destination idempotency or atomic uniqueness.
- Otherwise `duplicate-resistant`; explicitly report an eventual-indexing
  window.

Never hide the marker in content that the connector cannot query reliably.

## Shared document or model update

Use for a collaborative document, spreadsheet, thesis tracker, or other mutable
record.

Assumptions:

- a stable resource identity exists;
- the current record can be re-read;
- the result can be read after update.

Plan:

1. Derive an opaque resource-operation identity.
2. For a material update that can overlap or retry, claim
   `workflow-checkpoint`; use a simple lock only for a lower-risk update.
3. Re-read the current destination state after guard acquisition.
4. Recalculate the patch; do not apply one based on a stale pre-guard read.
5. Use a destination conditional-write/version field when available.
6. Record `external_attempt_started`, then apply the update once.
7. Read back the changed fields and version.
8. Record `caller_verified` after read-back. On a lost result, mark uncertainty
   and re-read before any new update.

Guarantee:

- Destination conditional writes prevent lost updates at the provider.
- Without them, report `concurrency-safe`; the Agent Enhancer lock cannot
  prevent edits made outside the guarded workflow.

## Scheduled research import

Use for recurring filings, transcripts, reports, webhook events, or research
records.

Plan:

1. Derive a stable run identity from schedule, period, and recipe version.
2. Acquire one run owner with `penny-lock` or `freshness-lease`.
3. Derive an opaque identity for every source item.
4. Acquire a per-item guard and verify destination state. Do not use a
   seen-stamp miss as completion; calling the tool on a miss creates state.
5. Use a shared `swarm-rate-gate` and `swarm-semaphore` around provider reads.
6. Import with the searchable-creation recipe.
7. Verify every material write before optionally stamping it seen. Treat later
   stamp hits as advisory until the destination is verified.
8. Report batch counts, including uncertain and awaiting-review items.

Do not let the run-owner lease stand in for per-item completion.

## Parallel research and one synthesis

Use for public-equity research or another read-heavy fan-out/fan-in workflow.

Assumptions:

- every source artifact has a stable opaque identity;
- the provider quota and desired concurrency are known;
- the synthesis threshold is known;
- the final shared output can be read back.

Plan:

1. Acquire a per-artifact guard and check the durable result store. Optionally
   call `global-seen-stamp` only after the artifact result is durably stored or
   otherwise verified; a stamp hit is advisory and does not replace the result
   check.
2. Use `freshness-lease` per ticker/data date so one worker owns refresh.
3. Use `swarm-semaphore` to cap active analyses.
4. Use `swarm-rate-gate` for the shared provider quota.
5. Have unique workers arrive at `barrier-bell` after verified completion.
6. Start synthesis only after the required arrivals.
7. Acquire `penny-lock` around the final model or thesis-tracker update.
8. Re-read, update, and verify the final shared output.

Recovery:

- A denied lease means reuse or wait for the refresh; it does not prove data is
  current.
- A worker failure must not count as a barrier arrival.
- An expired semaphore or lock requires destination re-check before resuming.
- Changed provider data should use a new freshness identity, not overwrite the
  meaning of an old sidecar idempotency key.

Overall guarantee is usually `concurrency-safe` or
`rate/concurrency-bounded`. The sidecar does not improve financial conclusions.

## Email or messaging send

Use when simultaneous agents or retries might send the same message.

Plan:

1. Prefer a documented destination idempotency key.
2. Otherwise derive an opaque send identity and claim `workflow-checkpoint`.
3. Re-check a queryable delivery ID or sent-message marker before sending.
4. Record `external_attempt_started`, then send once through the domain plugin.
5. Verify provider delivery/acceptance status when available.
6. After a timeout, mark uncertainty and query status without a blind retry.

If no provider idempotency, sent-message query, or delivery identifier exists,
stop after an uncertain result. A lock or consumed baton prevents a concurrent
worker but cannot prove whether the provider accepted the message.

Guarantee is `provider-idempotent` with documented provider support,
`concurrency-safe` when only simultaneous workers are serialized, and otherwise
`best-effort`.

## Failure rehearsal

Before using production data, test the caller-controlled integration when
possible:

- use `failure-sequence-forge` for bounded 429, 500, and recovery sequences;
- use `status-code-forge` for one temporary controlled response;
- use `webhook-attempt-meter` for method, count, timing, and hash-only delivery
  evidence;
- use `mcp_tool_contract_linter` and handshake/schema diff tools before trusting
  a saved recipe against a changed plugin contract.

Cover timeout before action, timeout after action, agent crash, delayed search,
rate limiting, verification failure, and tool-contract drift. Do not claim a
worked recipe is a future compatibility guarantee.
