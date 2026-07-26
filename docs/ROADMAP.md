# Roadmap: The Reliability Sidecar for Agent Workflows

Agent Enhancer Utilities should become the reliability sidecar that agents
deliberately compose with other plugins. Domain plugins still search, analyze,
create, update, send, and publish. Agent Enhancer adds coordination, duplicate
resistance, bounded concurrency, shared quotas, failure testing, freshness
control, and explicit recovery rules around those operations.

This direction is most valuable for repeated, scheduled, parallel, or
high-consequence workflows. A one-time low-risk plugin call should normally
proceed without sidecar overhead.

## North-star outcome

An agent using several plugins should be able to answer these questions before
it acts:

1. What is the stable identity of this operation?
2. Can the downstream plugin make the operation idempotent?
3. What coordination or quota guard is required?
4. How will success be verified?
5. What should happen after a timeout, crash, or uncertain result?
6. What guarantee was actually achieved, and what risk remains?

Agent Enhancer should turn the answers into a small, inspectable guard plan and
help execute that plan using opaque identifiers and bounded temporary state.

## Current focus

Backend `0.6.2` is live on the existing production app with 24 modules, 37
Claude tools, 37 ChatGPT tools, and Official MCP Registry `0.6.2` marked
latest. Public package `v1.5.0` provides all seven skills, cross-host manifests,
and two runnable sidecar examples. Real USDC remains disabled.

The next work is commercial validation, not another broad module expansion:

1. Recruit five external design partners and run the Sidecar v1 recipes for 14
   days.
2. Measure correct selection and abstention, duplicate recovery, successful
   verification, D7 repeat, and willingness to pay for higher capacity.
3. Reconcile the first real hosting invoice and owner-support time so
   profitability has an evidence-backed cost floor.
4. Keep the shared circuit breaker, action budget, and version fence
   demand-gated. Build the smallest one only when observed failures show that
   the planner, checkpoint, and existing primitives cannot express the need.
5. Prepare the paid-capacity configuration and operator checklist, but do not
   enable settlement until the existing storage, wallet, demand, and approval
   gates are satisfied.

### Open-source integration lane

Use the public package to contribute working integration artifacts rather than
generic promotional links:

1. Keep the existing Docker and curated-list submissions accurate; open no
   additional general awesome-list PRs while they remain under review.
2. Maintain the focused
   [OpenHands Extensions PR #418](https://github.com/OpenHands/extensions/pull/418),
   which adds only the no-auth remote MCP definition and generated catalog
   index. Its schema/catalog tests and live initialization pass; fork workflows
   still require maintainer approval.
3. Keep the validated [Goose recipe](../examples/goose/) in this repository,
   but do not submit it while Goose maintainers are pausing new external
   recipes and MCP servers.
4. Maintain the focused
   [Agno cookbook PR #9178](https://github.com/agno-agi/agno/pull/9178),
   which demonstrates failed-generation recovery, competing-worker fencing,
   lost-response marker read-back, and an honest duplicate-resistant
   guarantee with a synthetic destination.
5. Wait for maintainer interest on the vendor-neutral
   [Microsoft MCP for Beginners proposal #949](https://github.com/microsoft/mcp-for-beginners/issues/949)
   and
   [Agent Framework Samples proposal #115](https://github.com/microsoft/Agent-Framework-Samples/issues/115);
   do not open either implementation PR first.
6. Coordinate neutral x402 retry fixtures through
   [issue #831](https://github.com/x402-foundation/x402/issues/831).
   Challenge drift is reproducible without wallets or settlement, but
   overlapping fixes already exist, so wait for maintainer direction instead
   of opening a duplicate PR.

Keep at most two new integration PRs active at once. Every upstream artifact
must have a runnable local equivalent, a source-tagged endpoint, exact test
instructions, and a maintainer-appropriate contribution path.

## Product boundary

The sidecar can:

- coordinate agents that share an external plugin or resource;
- prevent simultaneous work and suppress work already known to be complete;
- limit concurrency, call rate, or the number of attempted actions;
- coordinate refresh ownership and multi-stage fan-out/fan-in workflows;
- test retry and webhook failure behavior in bounded non-production fixtures;
- inspect plugin contracts and detect capability or schema drift;
- recommend recovery behavior and report the residual guarantee.

The sidecar cannot:

- automatically intercept every call made by another plugin;
- add idempotency support to a downstream API that does not provide it;
- create a transaction spanning Agent Enhancer and another plugin;
- prove an external action completed merely because a lock, stamp, or baton was
  acquired;
- make a send-only or create-only operation exactly once when the destination
  cannot deduplicate or be searched reliably;
- improve a domain plugin's knowledge, data quality, permissions, or analysis.

The product must never describe a workflow as exactly once unless the
downstream operation itself has a transactional idempotency or uniqueness
guarantee. Agent Enhancer's `exactly-once-baton` is a one-use coordination
capability, not an exactly-once wrapper around an external side effect.

## Standard sidecar lifecycle

Opinionated skills and future planning tools should use one common lifecycle:

1. **Classify** the external operation: read, create, update, send, delete,
   refresh, or batch.
2. **Identify** it with a stable, opaque operation key. Sensitive source data
   should be hashed locally and never sent to Agent Enhancer.
3. **Guard** it with the smallest suitable primitive: lock, seen stamp, baton,
   semaphore, rate gate, barrier, negative cache, freshness lease, or a future
   action budget.
4. **Preflight** through the domain plugin: search for an existing marker,
   re-read the current version, or confirm that the work is still needed.
5. **Act** through the domain plugin.
6. **Verify** through the domain plugin whenever it supports read-after-write
   or delivery status.
7. **Record** completion only after verification, then release temporary
   coordination state only when the live primitive supports authorized release.
8. **Report** the guarantee achieved, evidence observed, and any remaining
   failure window.

Every guarded workflow should use one of these guarantee labels:

| Label | Meaning |
| --- | --- |
| Provider-idempotent | The destination transactionally deduplicates a stable operation key. |
| Duplicate-resistant | A stable marker can be searched and verified, but a consistency or crash window remains. |
| Concurrency-safe | Simultaneous workers are coordinated, but a later retry might repeat the external action. |
| Rate/concurrency-bounded | Load is limited, without making the business action unique. |
| Best-effort | The destination cannot reliably search, verify, or deduplicate the action. |

## Reliability profiles

The sidecar should offer named profiles instead of making every agent assemble
low-level primitives from scratch:

| Profile | Typical guard plan |
| --- | --- |
| `create-once` | Stable marker, lock, destination search, create, read-back verification, optional advisory seen stamp |
| `update-safely` | Lock, version re-read, update, read-back verification, then authorized release or shortest-TTL expiry |
| `send-at-most-once` | Lock or baton plus provider idempotency when available; otherwise report the uncertain-send window |
| `refresh-if-stale` | Freshness lease, negative cache, rate gate, refresh, freshness verification |
| `fan-out-bounded` | Per-item guards and destination checks, semaphore, shared rate gate, optional post-verification seen stamps, barrier before synthesis |
| `scheduled-run` | Stable run identity, one run owner, checkpoints, bounded retries, completion receipt |
| `write-budget` | Shared maximum action count or cost budget, with a hard stop and explicit override path |

Profiles are plans, not claims. The achieved guarantee depends on the
capabilities of the external plugin.

## Phase 0 — Clarify and teach the sidecar model

Status: complete in public release `v1.4.0`.

- Position Agent Enhancer as a reliability sidecar for other agent tools and
  plugins.
- Add a `guard-external-plugin-workflows` skill that selects a reliability
  profile, describes the call order, and states the residual risk.
- Publish a capability-to-guarantee matrix for common external tool shapes:
  provider idempotency, searchable marker, conditional update, read-after-write,
  delivery receipt, and send-only.
- Add worked examples for:
  - searchable page or database creation;
  - a shared document or model update;
  - a scheduled research import;
  - bounded parallel analysis followed by one synthesis;
  - email or messaging sends where the result may remain uncertain.
- Add positive and negative prompt evaluations. The sidecar should activate for
  repeated, parallel, scheduled, quota-sensitive, or duplicate-sensitive work
  and abstain from ordinary one-time commands.
- Standardize the final reliability report:
  profile, operation identity, guards used, verification evidence, guarantee
  label, and residual risk.

Exit criteria:

- An agent can produce the same safe plan for the same external capability
  shape without vendor-specific improvisation.
- Documentation never implies automatic interception or cross-plugin
  transactions.
- One-time low-risk requests remain short and unaffected.

## Phase 1 — Add a Workflow Guard Planner

Status: live in backend `0.6.2` (introduced in `0.6.1`).

Create a read-only planning module. It should accept bounded capability facts,
not raw records or credentials:

- operation class and whether duplicates are harmful;
- whether work is parallel, scheduled, or retried;
- availability of provider idempotency;
- availability and consistency of destination search;
- support for stable markers, conditional writes, read-after-write, and
  delivery status;
- concurrency and quota limits;
- required freshness and expiry.

It should return:

- the recommended reliability profile;
- an ordered plan using existing primitives;
- where the domain plugin must be called;
- stable-key and marker guidance;
- timeout and uncertain-result recovery rules;
- the achievable guarantee label;
- explicit residual risks and unsupported claims.

The planner should support a dry-run mode that produces a plan without creating
coordination state.

Exit criteria:

- Plans are deterministic for equivalent capability descriptions.
- The planner abstains when the supplied facts are insufficient.
- No plan claims exactly once solely because a baton, lock, or seen stamp is
  present.

## Phase 2 — Add bounded workflow state

Status: Opaque Workflow Checkpoint is live in backend `0.6.2`; remaining
proposals are demand-gated.

Evaluate these small, generic modules:

### Opaque workflow checkpoints

Track bounded states such as `claimed`, `external_result_uncertain`,
`caller_verified`, `failed`, and `compensated` under an opaque operation
identifier and TTL. A checkpoint is coordination evidence, not proof of the
external action and not a permanent audit log. This is the
[selected first stateful proposal](./OPAQUE_WORKFLOW_CHECKPOINTS.md).

### Shared circuit breaker

Allow a swarm to pause calls to a failing dependency after a bounded number of
typed failures, then permit one probe after a cooldown. This complements the
negative cache and rate gate. It is the
[next stateful candidate](./SHARED_CIRCUIT_BREAKER.md).

### Action budget

Atomically enforce a maximum number of external attempts or writes across
workers. Start with integer counts. Do not accept payment credentials,
financial account details, or unbounded monetary authority.

### Version fence

Bind an opaque resource identifier to an expected version fingerprint while an
update is in progress. This can help agents detect stale plans, but it must not
be represented as an atomic compare-and-swap at the destination.

### Privacy-safe completion receipt

Return a compact record of the selected profile, guards, timestamps, opaque
hashes, and reported guarantee. It must distinguish agent-observed verification
from provider-backed proof and expire unless a durable feature is explicitly
designed later.

Exit criteria:

- Each module solves a failure mode that existing primitives cannot express
  clearly.
- Every stateful module is bounded, expiring, idempotent where appropriate, and
  usable without sending private content.
- Checkpoints and receipts are not marketed as external truth or durable audit
  infrastructure.

## Phase 3 — Build and validate integration recipe packs

Priority: now — validate the released Sidecar with five external design
partners before adding another stateful module.

Recipes should be organized by capability shape first and named plugin second.
Candidate packs include:

- knowledge bases and searchable record stores;
- cloud files and collaborative documents;
- spreadsheets, CRMs, and other shared mutable records;
- email, chat, and notification systems;
- calendars and booking systems;
- public-equity research and other scheduled data pipelines;
- webhook consumers and event imports;
- software-development tools with issues, deployments, and CI jobs.

Each recipe should specify:

- the external tool capabilities it assumes;
- the stable operation identity and destination marker;
- the exact sidecar call order;
- crash points and recovery behavior;
- verification and compensation options;
- the guarantee label;
- a contract or recipe version.

Use `worked-once-recipe-vault` only for recipes that have passed an end-to-end
test against the stated capability shape. Treat a worked recipe as versioned
compatibility evidence, not a future guarantee.

Initial reference recipes:

### Searchable page creation

Derive a stable opaque source key locally, acquire a lock, search the
destination for a stored marker, create only when absent, read the marker back,
then record completion. This is duplicate-resistant when destination search can
lag and provider-idempotent only when the destination supplies that guarantee.

### Parallel investment research

Use a per-artifact guard and durable-result check, an optional advisory seen
stamp after verification, a freshness lease per ticker and data date, a
semaphore and rate gate for provider calls, a barrier before portfolio
synthesis, and a lock around the final shared model or thesis-tracker update.
The sidecar improves workflow reliability, not investment conclusions.

### Messaging or email send

Prefer a provider idempotency key or a queryable delivery identifier. Without
one, coordinate simultaneous senders and stop blind retries after an uncertain
timeout. Report `concurrency-safe` or `best-effort`, never exactly once.

Exit criteria:

- Every published recipe includes failure injection or replay testing where the
  external surface permits it.
- Recipe tests cover timeout before action, timeout after action, agent crash,
  stale search, rate limiting, verification failure, and changed tool
  contracts.
- Recipes remain useful when the named vendor is replaced by another plugin
  with the same capability shape.

## Phase 4 — Make composition increasingly automatic

Priority: later, subject to host capabilities

- Use MCP tool schemas and annotations to infer operation class, side effects,
  and likely verification options.
- Detect contract drift before executing a saved recipe.
- Recommend a sidecar profile automatically when a plan contains repeated,
  parallel, scheduled, or duplicate-sensitive external actions.
- Generate an execution checklist and reliability report from the selected
  profile.
- Explore native pre-tool and post-tool hooks only on hosts that explicitly
  support them.
- Explore an SDK or proxy middleware for developer-owned applications that need
  true automatic wrapping. Keep this separate from the account-free plugin:
  middleware that handles credentials or payloads has a different privacy,
  security, and operational model.

Automatic recommendation must remain explainable and easy to decline. The
agent should not add locks, network calls, or latency to every trivial plugin
operation.

## Additional product ideas

### Reliability contract

Define a small portable contract that any recipe can consume:

- external operation class;
- stable-key support;
- search and consistency behavior;
- conditional-write support;
- verification and delivery evidence;
- retry semantics;
- concurrency and quota limits;
- compensation support.

This becomes the common language between domain plugins and the sidecar.

### Reliability linting

Given a proposed multi-plugin plan, flag:

- create or send operations retried without a stable identity;
- seen stamps represented as completion before external verification;
- batons treated as proof of downstream completion;
- locks that expire before the protected work can finish;
- parallel work without a shared rate gate;
- writes based on stale reads;
- barriers that can never reach their threshold;
- retries after an uncertain send;
- sensitive content proposed as a coordination key.

### Compensation planner

When true atomicity is impossible, recommend bounded recovery:

- locate and merge a duplicate;
- archive an unverified extra record;
- mark a partial update for human review;
- resume from the last verified checkpoint;
- stop rather than retry an uncertain message or irreversible action.

The sidecar should recommend compensation but should not perform a destructive
external action without the normal domain-plugin authorization.

### Guarded batch summary

For batch workflows, report counts such as attempted, skipped as already seen,
blocked by another worker, throttled, verified, uncertain, failed, and awaiting
review. This makes the value of the sidecar visible without retaining source
records.

### Contract drift watch

Combine the existing MCP contract tools with recipe versions. If an external
plugin changes tool annotations, required fields, idempotency behavior, or
verification outputs, pause the saved recipe and request review.

### Failure rehearsal

Use the existing failure sequence and webhook tools to rehearse recovery before
a workflow touches production data. Produce a test result tied to the recipe
version and expected failure points.

## Success measures

Measure whether the sidecar improves the larger workflow, not merely whether a
utility returned HTTP 200:

- duplicate external actions avoided;
- conflicting writers prevented;
- provider quota violations avoided;
- stale refreshes suppressed;
- workflows recovered from a tested failure;
- uncertain outcomes correctly stopped and escalated;
- guarded workflows with an explicit guarantee label;
- correct abstention on low-risk one-time requests;
- zero sensitive payloads or credentials retained by coordination utilities.

Outcome evidence must distinguish inferred prevention from directly observed
events. For example, a denied lock is evidence that a conflicting worker was
blocked, while a seen-stamp hit alone does not prove what the external plugin
previously completed.

## Deliberate non-goals

- Replacing domain plugins or duplicating their APIs
- Proxying arbitrary private plugin payloads through the service
- Storing credentials, customer data, messages, documents, or financial records
- Acting as a permanent workflow database or compliance audit log
- Claiming universal exactly-once execution
- Becoming a general autonomous workflow engine
- Adding coordination calls to every ordinary one-time request

## Recommended first delivery slice

1. Add the `guard-external-plugin-workflows` skill.
2. Define the reliability contract and five guarantee labels.
3. Specify the read-only Workflow Guard Planner.
4. Publish and test the searchable-page and parallel-research recipes.
5. Add prompt evaluations for correct activation, safe abstention, and honest
   guarantee language.
6. Add the standardized guarded-workflow summary.
7. Use observed recipe failures to choose between checkpoints, a circuit
   breaker, and an action budget as the first new stateful module.

## First delivery status

Completed in the public skills repository on 2026-07-25:

1. Added and validated `guard-external-plugin-workflows`.
2. Published the reliability contract, five guarantee labels, standard outcome,
   and capability-shape recipes.
3. Specified the read-only Workflow Guard Planner with closed JSON schemas and
   added an executable local dry-run reference with eleven passing tests; the
   live MCP contract linter returned zero findings across nine rules.
4. Tested the create-once coordination primitives and the fan-out-bounded
   sequence with temporary opaque live state. External vendor writes remain
   deliberately outside this primitive test.
5. Added six activation and four abstention evaluation cases, including honest
   baton and uncertain-send language.
6. Added cross-plugin outcome-evidence rules to the effectiveness methodology.
7. Used the live seen-stamp and lock behavior to select Opaque Workflow
   Checkpoints first and retain a Shared Circuit Breaker as the next candidate.
8. Passed the isolated `0.6.0` preview and five controlled synthetic Notion
   scenarios: normal, identical replay, concurrent workers, crash before
   create, and crash after create before verification. Each stable marker
   produced exactly one verified page.
9. Promoted backend `0.6.1` to the existing production app, passed canonical
   all-tools acceptance, and published `0.6.1` as latest in the Official MCP
   Registry without enabling USDC.

The ChatGPT submission copy and multilingual starter prompts now position the
target 37-tool app as a deliberate reliability sidecar, include a guarded
cross-plugin test, and preserve abstention for a one-time external write.

See [SIDECAR_RECIPE_TESTS.md](./SIDECAR_RECIPE_TESTS.md) for observed evidence
and remaining vendor-specific coverage. The planner and checkpoint have
live backend `0.6.1` implementations maintained outside this repository; the
circuit breaker remains a specification.
