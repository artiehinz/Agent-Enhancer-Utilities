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

Backend `0.6.9` is live on the existing production app and public package
`v1.6.0` is released. They retain all 24 modules, 37 Claude tools, 37 ChatGPT
tools, and all seven skills, and add Reliability Sidecar Contract v1 plus a
deterministic paired evidence suite. The recommended MCP connection now uses a
three-tool core profile while an experimental one-tool compact profile still
reaches all 24 modules. Official MCP
Registry `0.6.4` remains the latest immutable registry version until the
next registry release gate is complete. Real USDC remains disabled.

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

### Reliability proof, clean measurement, and paired benchmark

The next evidence release must demonstrate value in the larger agent workflow,
not merely show that an Agent Enhancer tool returned successfully. It has three
ordered workstreams:

1. **Prove ambiguous-success recovery.** Extend the synthetic reliability
   example so an external write commits and its first response is lost. Compare
   a naive retry, which can create a duplicate, with a guarded run that records
   `external_result_uncertain`, reads back a stable marker, records
   `caller_verified`, and does not repeat the mutation. Preserve the honest
   `duplicate-resistant` guarantee and `external_proof: false`; this is not a
   cross-plugin transaction or universal exactly-once claim.
2. **Start a clean external-use baseline.** Treat the first 655 module
   observations as a mixed automation window, not verified beta-user usage.
   Archive an aggregate-only internal snapshot, mark every owned test and
   integration run, exclude the old window publicly, and begin a new baseline
   only after marked automation is proven to write zero public observations.
3. **Run a controlled with/without-sidecar benchmark.** Execute the same
   multi-agent, multi-step fixtures with Agent Enhancer disabled and enabled.
   Keep the model/version, reasoning setting, agent count, prompts, tool set,
   workspace snapshot, budgets, timeouts, and injected failures fixed. Reset
   the destination between paired runs, randomize run order, repeat each
   condition enough to report a distribution, and evaluate outcomes without
   using the condition label.

The initial benchmark matrix should include:

- a duplicate-sensitive create whose success response is lost;
- a parallel multi-agent development task with overlapping implementation and
  verification responsibilities;
- a bounded batch under a shared rate limit;
- a scheduled or repeated refresh where stale work should be suppressed; and
- an ordinary one-time low-risk task where correct abstention should add
  negligible overhead.

Capture total model input, output, cached, and reasoning tokens when the host
reports them; model and external-tool cost at the recorded rate sheet; agent
turns; tool calls; repeated or conflicting calls; wall-clock and critical-path
latency; successful final-state verification; duplicate mutations; recovery
rate; unresolved ambiguous outcomes; manual interventions; and sidecar-only
overhead. Do not infer token savings when a host does not expose usage.

Pre-register the fixtures, evaluator, sample size, exclusions, and success
thresholds before running the comparison. Publish sanitized run-level results,
the aggregation script, confidence intervals or full distributions, and
failures as well as successes. The benchmark may show that the sidecar helps
failure-prone workflows while adding overhead to simple work; do not select
only tasks or runs that make the product look beneficial.

After at least one benchmark meets its pre-registered reliability or net-cost
gate, publish a GitHub case study and add a summarized comparison to the
Evidence page. A later video may show the same fixture side by side, including
the injected failure, tool timeline, tokens, cost, verified result, and
limitations. Produce that video from captured benchmark evidence rather than
from an unverified marketing script.

The deterministic first tier is implemented in `v1.6.0`: 50 unpublished
validation runs were excluded, followed by 200 published run-level records
covering 20 paired runs for each scenario. The synthetic suite reduced harmful
duplicate or unresolved events from 160 to 0, maintained or improved verified
completion, and correctly made zero sidecar calls in the low-risk abstention
scenario. These results validate the state machine and fixtures, not model
quality or token savings. Model tokens, cost, and agent latency remain
unavailable until the same preregistered scenarios are run through real,
metered agent hosts.

The first metered Codex validation is preserved under
`examples/sidecar-agent-benchmark/`. It pins Codex CLI `0.144.0-alpha.4`,
`gpt-5.6-sol` at medium reasoning, identical paired prompts, disposable
destination state, randomized condition order, condition-blind evaluation,
real token/tool/latency capture, and a combined protocol hash. Codex Apps are
disabled in both conditions so the only condition difference is the marked
production Agent Enhancer MCP.

The backend `0.6.4` sample failed honestly: eight harmful overlap events
occurred in each condition, while the low-risk connected condition added
10.466% median input-token overhead and 28.431% median latency overhead despite
making zero sidecar calls. Backend `0.6.5` therefore introduced an explicitly
instructed three-tool core profile.

The completed `0.6.5` validation eliminated six observed unguarded overlap
events, improved verified completion from 80% to 90%, and kept low-risk
sidecar calls at zero. It still failed overall because connection-only
input-token overhead was 10.779% and latency overhead was 27.341%. Preserve
both failed summaries and do not pool their rows.

The compact engineering probe then ran five additional low-risk pairs through
backend `0.6.8`. All ten rows were valid, made zero sidecar calls, and used the
one-tool compact profile. Median input-token overhead was still 10.561% and
median latency overhead was 38.523%, above the same 5% references. This probe
is explicitly exploratory and cannot confirm a product claim, but it is enough
to reject a third always-connected validation.

The next iteration should test conditional activation through the existing
skills and HTTP contracts so low-risk work does not connect the MCP at all.
Freeze a new preregistration only after that selector and activation boundary
are fixed without reference to favorable outcomes. Preserve the same safety
policy and condition-blind outcome evaluator. Run a later publication sample
only after every fixed validation gate passes.

Backend `0.6.4` also completed the clean measurement boundary. It preserved
the mixed pre-marker window as aggregate-only internal evidence, removed its
raw discovery and module observations, recorded the cutoff in the operator
audit trail, and began a database-backed external baseline at
`2026-07-28T19:07:18.657Z`. A marked full production acceptance covering both
37-tool direct connectors left public observations at zero.

The next metered validations later contributed 136 observations to that
window because their dotted-key Codex override quoted the HTTP header name,
causing Codex to reject it while continuing the MCP session. Those
observations match owned benchmark timing and module use and are not
represented as beta-user traffic. Backend `0.6.7`
archives the indistinguishable mixed window without deleting its
privacy-bounded rows, advances the public cutoff, and returns only a boolean
`owned_automation_excluded` acknowledgement. The harness now performs a real
Codex preflight and rejects every unacknowledged sidecar invocation. Backend
`0.6.8` exposes the same acknowledgement on a small catalog search so that
preflight does not invoke the full planner result.

### Planned licensing transition

The repository remains MIT until a deliberate versioned transition, but the
intended direction is to stop publishing new original product work under MIT.
MIT permits copying, modification, redistribution, sublicensing, and sale, so
it cannot protect the project from commercial clones or redistributed forks.

For a future major release, prefer
[PolyForm Strict 1.0.0](https://polyformproject.org/licenses/strict/1.0.0),
or a counsel-approved source-available equivalent, with a separate written
commercial license available from Artie Hinz. PolyForm Noncommercial is not
the preferred default because it still permits noncommercial modification and
redistribution. PolyForm Strict permits noncommercial use but does not grant
permission to distribute copies or create modified works.

Treat this as a release boundary, not a silent metadata edit:

1. Confirm the final terms, attribution notice, commercial-license process,
   jurisdiction, and enforcement expectations with qualified legal counsel.
2. Accept that already-published MIT versions and copies remain usable under
   their original terms. Tag the final MIT release and apply the new license
   only to a clearly identified later major version and its new work.
3. Keep proprietary backend implementation and future differentiating
   algorithms out of the public package. Publish only the skills, manifests,
   clients, fixtures, evidence, and integration material that must be public.
4. Review whether Agent Skills, MCP directories, ChatGPT or Claude venues,
   package indexes, and existing integrations accept a source-available
   package before changing the repository license.
5. At transition, replace every repository-wide MIT reference in manifests,
   README, archives, contribution policy, release metadata, and package
   indexes. Use `source-available`, not `open source`, for the main project.
6. Maintain a narrow, explicit exception for upstream contributions. A patch,
   connector definition, example, or independently useful code fragment may
   be released under the receiving project's MIT, Apache-2.0, or other
   required license only when each contributed file or patch has a clear SPDX
   identifier and does not contain proprietary product code.
7. Keep a `LICENSES` inventory or equivalent mapping so a permissively
   licensed upstream fragment cannot be mistaken for permission to copy the
   wider source-available project.
8. Do not attempt to relicense work already contributed to another project or
   code for which the project does not own all necessary rights.

A restrictive license controls copying of the protected code; it does not
prevent someone from independently rebuilding the underlying ideas or methods.
Keep commercially sensitive implementation details private when practical.

### Upstream open-source contribution lane

Use the public package to contribute working integration artifacts rather than
generic promotional links:

The exact repository-to-module map, contribution sequence, protocol package,
promotion gates, and licensing boundary are maintained in
[OPEN_SOURCE_INTEGRATION_PLAN.md](./OPEN_SOURCE_INTEGRATION_PLAN.md).

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
- paired task-success, duplicate, retry, token, cost, and latency differences
  between guarded and unguarded runs;
- net benefit after subtracting the sidecar's own tokens, calls, and latency;
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
