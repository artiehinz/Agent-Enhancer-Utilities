# Open-Source Integration and Sidecar Adoption Plan

Last reviewed: 2026-07-29

## Objective

Make the reliability-sidecar pattern useful inside established agent projects,
earn adoption through tested contributions, and make Agent Enhancer the easiest
free reference implementation without turning upstream pull requests into
advertising.

The project should contribute three different kinds of artifacts:

1. **Connectors and registry entries** expose the complete hosted MCP. They do
   not copy backend module code into the receiving repository.
2. **Workflow examples** teach and test a small part of the sidecar lifecycle
   with a synthetic destination. They use only the modules required for that
   workflow.
3. **Neutral protocol fixtures** improve an upstream project without requiring
   Agent Enhancer. Our repository may separately document which Agent Enhancer
   modules implement or test the same behavior.

Do not impose an arbitrary numerical cap on active contributions. Open each
artifact only after confirming a concrete upstream gap, checking for duplicate
issues or work, following the repository's contribution path, and validating a
local equivalent. A useful issue-first proposal is preferable to an unsolicited
large patch. Generic listings and backlinks are not integrations.

## What we are promoting

Use **Reliability Sidecar Contract v1** as the working name. Do not call it an
industry standard until at least two independent projects implement the
contract.

The portable lifecycle is:

1. Classify the intended external operation.
2. Derive a stable opaque operation identity.
3. Plan the smallest appropriate guard.
4. Claim or checkpoint the operation before the external attempt.
5. Preflight the destination when search or version checks are available.
6. Execute the operation through the domain MCP.
7. Treat a lost response after a possible write as uncertain, not as an
   ordinary retryable failure.
8. Reconcile through provider status, read-after-write, or a stable marker.
9. Record caller-observed evidence separately from provider-backed proof.
10. Report the achieved guarantee and residual risk.

The first public contract package should contain:

- a concise Markdown specification;
- closed JSON Schemas for capability facts, guard plans, checkpoints, evidence,
  and final reports;
- a state-transition table;
- a guarantee vocabulary: `provider-idempotent`, `duplicate-resistant`,
  `concurrency-safe`, `rate/concurrency-bounded`, and `best-effort`;
- conformance fixtures for known failure, ambiguous success, competing workers,
  stale search, changed tool contract, and correct abstention;
- one local in-memory reference adapter and one optional remote Agent Enhancer
  adapter;
- a machine-readable contract version.

## Module bundles

The 24 hosted modules should be described in six bundles. Upstream examples
should select the smallest bundle that solves the demonstrated problem.

| Bundle | Modules |
| --- | --- |
| Core sidecar | `workflow-guard-planner`, `workflow-checkpoint` |
| Coordination | `penny-lock`, `global-seen-stamp`, `exactly-once-baton`, `swarm-semaphore`, `swarm-rate-gate`, `barrier-bell`, `freshness-lease`, `negative-cache-ticket` |
| Failure rehearsal | `status-code-forge`, `failure-sequence-forge`, `safe-synthetic-fixture-vault`, `webhook-attempt-meter` |
| MCP contracts | `mcp-tool-contract-linter`, `mcp-capability-handshake-diff`, `mcp-elicitation-safety-linter`, `mcp-schema-edge-case-atlas` |
| x402 diagnostics | `x402-error-rosetta-stone`, `x402-requirement-drift-diff`, `x402-facilitator-compatibility-diff`, `x402-quote-fingerprint-guard` |
| Reusable knowledge | `error-code-cemetery`, `worked-once-recipe-vault` |

## Exact repository and module map

### Active and existing submissions

| Repository | Contribution | Agent Enhancer scope | Current action |
| --- | --- | --- | --- |
| [docker/mcp-registry #4537](https://github.com/docker/mcp-registry/pull/4537) | Remote MCP registry definition | Connects to all 24 modules through the six progressive MCP tools | Current branch is mergeable. The full Go suite, entry validator, remote build path, catalog generation, live initialization, and 24-module discovery passed on 2026-07-28. Wait for review and comment only after a material change or maintainer request. |
| [OpenHands/extensions #418](https://github.com/OpenHands/extensions/pull/418) | No-auth remote MCP catalog connector | Connects OpenHands to all 24 modules; no backend code is copied | The generated catalog is in sync and 101 focused schema/catalog tests pass. Keep the patch metadata-only and wait for review. |
| [agno-agi/agno #9178](https://github.com/agno-agi/agno/pull/9178) | Deterministic recovery cookbook | Uses `workflow-guard-planner` and `workflow-checkpoint` | Rebased onto current `main`; cookbook pattern, Ruff, mypy, and the live deterministic example pass. The body closes issue #9179. Leave the stale maintainer-owned `missing-issue-link` label untouched and wait for review. |
| [punkpeye/awesome-mcp-servers #10889](https://github.com/punkpeye/awesome-mcp-servers/pull/10889) | Curated server listing | Lists the complete service; description covers all bundles | Rebased onto current `main`; submission checks pass. Ownership and score are visible on the Glama Connector, but the workflow requires a server-style badge path that returns 404 for connectors. Wait for Glama support's emailed answer before changing or commenting again. |
| [punkpeye/awesome-mcp-devtools #242](https://github.com/punkpeye/awesome-mcp-devtools/pull/242) | Focused testing-tool listing | Emphasizes Failure rehearsal, MCP contracts, and x402 diagnostics; the endpoint still exposes all 24 modules | Current branch is clean and mergeable. Monitor only. Do not duplicate this entry in more generic awesome lists. |
| [aaif-goose/goose #10780](https://github.com/aaif-goose/goose/pull/10780) | Reliability-sidecar recipe | Uses `workflow-guard-planner` and `workflow-checkpoint` around another MCP | The recipe passes Goose CLI `1.44.0` validation and a live MCP smoke. Owner-qualified `agent-enhancer__lab.*` tool names now match Goose exposure and the review thread is resolved. The remaining failed `security-scan` is an upstream `pull_request_target` checkout refusal before recipe content is scanned; maintainers can use the linked minimal base-workflow fix in `aa44e4d`. |
| [github/awesome-copilot #2474](https://github.com/github/awesome-copilot/pull/2474) | Vendor-neutral ambiguous external-write recovery skill | Portable planner, checkpoint, evidence, and abstention concepts; no hosted dependency | All nine applicable checks pass and five unrelated jobs skip. The robot marker in the title is required by that repository for AI-authored contributions. |
| [erpipe-org/mcp-odoo #61](https://github.com/erpipe-org/mcp-odoo/pull/61) | Replay fence for an approved Odoo write whose response is lost | Portable checkpoint and reconciliation concepts implemented inside the Odoo MCP | The regression fixture commits a synthetic external mutation, drops its response, and proves a same-token retry cannot issue a second write. The branch is rebased onto `v1.3.0`; focused tests, Ruff, mypy, and the portable full suite pass. The PR is ready for review rather than draft. |
| [nshkrdotcom/codex_sdk #3](https://github.com/nshkrdotcom/codex_sdk/pull/3) | Conservative MCP tool-call retry default | Guard planning, stable identity, and uncertain-result handling | `tools/call` retries now default to zero while explicit retries remain available for replay-safe operations. A synthetic mutation commits before a dropped response and proves only one call is sent by default. Format checks, 117 affected tests, and strict Credo pass. |
| [zavora-ai/adk-rust #506](https://github.com/zavora-ai/adk-rust/pull/506) | Explicit opt-in for MCP tool replay after reconnect | Planner/checkpoint ambiguity boundary expressed in client behavior | Automatic reconnect remains for discovery and resources; `ConnectionRefresher` and `McpToolset` require `with_tool_call_retries()` before replaying a possibly mutating tool. Format checks, 87 MCP tests, and strict Clippy pass. |
| Official MCP Registry | Published server metadata | Connects clients to all 24 modules | Continue version publication and endpoint smoke tests for each backend release. |

### Open issue-first proposals and design conversations

| Repository | Proposed contribution | Modules or portable concepts | Current action |
| --- | --- | --- | --- |
| [MCPJam Inspector #3555](https://github.com/MCPJam/inspector/issues/3555) | Add a local stateful ambiguous-success fixture to the inspector | `workflow-guard-planner`, `workflow-checkpoint`, and `failure-sequence-forge` concepts | Wait for the requested maintainer placement decision, then contribute the smallest local fixture. It must need no hosted service, model, or credentials. |
| [Kiln #112](https://github.com/codeofaxel/Kiln/issues/112) | Prevent duplicate queued physical prints after an accepted job response is lost | Stable opaque operation identity, durable uniqueness, and read-back | Wait for maintainer direction before changing the AGPL code. The proposed invariant is same key plus same payload returns the existing job id; same key plus conflicting payload fails. |
| [mcp-use #2054](https://github.com/mcp-use/mcp-use/issues/2054) | Local multi-server example with a synthetic destination and recovery guard | Planner, checkpoint, reconciliation, and evidence | The issue is labeled `duplicate`. Find the canonical issue and coordinate there; do not open a PR from this duplicate. |
| [lastmile-ai/mcp-agent #640](https://github.com/lastmile-ai/mcp-agent/issues/640) | Add a durable external-write recovery example to the existing resilience request | `workflow-guard-planner`, `workflow-checkpoint` | The issue closed without a maintainer-selected examples location. Retain the local concept and do not open a PR unless the project reopens or redirects it. |
| [langchain-ai/langchain-mcp-adapters #170](https://github.com/langchain-ai/langchain-mcp-adapters/issues/170) | Keep reconnect retries from becoming blind mutating-tool retries | Planner/checkpoint concepts expressed as a `ToolCallInterceptor` example | The existing retry issue contains the deterministic fixture proposal, but another contributor already volunteered. Do not duplicate their work; monitor for an explicit request. |
| [microsoft/mcp-for-beginners #949](https://github.com/microsoft/mcp-for-beginners/issues/949) | Vendor-neutral lesson and ambiguous-success exercise | Teach the portable equivalents of `workflow-guard-planner` and `workflow-checkpoint`; optionally use `failure-sequence-forge` for the exercise | Do not open a PR until a maintainer confirms scope and placement. The lesson must run locally without Agent Enhancer. |
| [microsoft/Agent-Framework-Samples #115](https://github.com/microsoft/Agent-Framework-Samples/issues/115) | Multi-agent handoff with two competing workers, one synthetic write, a lost response, reconciliation, and evidence | `workflow-guard-planner`, `workflow-checkpoint`; local `ReliabilityBackend` required, remote adapter optional | Do not open a PR until maintainers select language and placement. |
| [x402-foundation/x402 #831](https://github.com/x402-foundation/x402/issues/831) | Neutral conformance fixtures and retry guidance for payment requirements that change during retry | Fixtures correspond to `x402-requirement-drift-diff`, `x402-quote-fingerprint-guard`, and `x402-error-rosetta-stone`; `failure-sequence-forge` can author the local rehearsal | Coordinate with maintainers to avoid overlapping fixes. Upstream tests must not require the hosted MCP or real settlement. |

### Additional framework and smaller-repository candidates

Approach these only with the specific contribution below:

1. **[pydantic/pydantic-ai-harness](https://github.com/pydantic/pydantic-ai-harness)**:
   do not open a duplicate capability request. Its existing `StepPersistence`
   already records `started`, `completed`, and `failed` tool effects,
   idempotency keys, and `unknown_after_crash`, and explicitly makes external
   deduplication the orchestrator's responsibility. First build a local
   interoperability mapping from `ToolEffectRecord` to
   `ReliabilityReportV1`; propose upstream work only if that exercise exposes
   a missing public primitive.
2. **[creatornader/atrib](https://github.com/creatornader/atrib)**:
   build a local evidence adapter that consumes signed action records and
   session checkpoints. Set `external_proof: true` only when tool-side or
   counterparty evidence verifies the destination result; an agent signature
   alone proves authorship, not external truth. Verify locally before asking
   for an upstream framework adapter.
3. **[anulum/synapse-channel](https://github.com/anulum/synapse-channel)**:
   run a paired benchmark against its existing claims, checkpoints, receipts,
   replay recovery, and coding-fleet benchmark. Publish a neutral mapping from
   Synapse receipts to `ReliabilityReportV1`. Connect over its public protocol
   and do not copy AGPL implementation code.
4. **[EtanHey/cmuxlayer](https://github.com/EtanHey/cmuxlayer)**:
   use as an independent comparison for ambiguous terminal writes and
   multi-agent recovery. It already observes terminal state before replaying
   uncertain launcher writes. The repository requires a contributor voucher,
   so prepare the benchmark locally and approach it only after a maintainer
   vouches for the contribution.
5. **GitHub Agentic Workflows**:
   compare our fixture vocabulary with its current Safe Outputs and MCP Scripts
   retry specifications, which already distinguish non-idempotent operations
   and require caller-controlled side-effect checks. Contribute only a
   demonstrable missing conformance case, not another parallel specification.

Do not target AutoGen for a new feature contribution; its repository directs
new feature work to Microsoft Agent Framework. Do not open more generic
awesome-list pull requests.

## Delivery phases

### Phase A: proof before expansion

1. Finish the ambiguous-success before/after fixture.
2. Pre-register and run paired multi-agent tasks with the sidecar enabled and
   disabled.
3. Measure verified completion, duplicate writes, recovery, unresolved
   uncertainty, manual intervention, tool calls, tokens, model cost, and
   latency.
4. Publish all runs, including neutral or negative results.
5. Freeze Reliability Sidecar Contract v1 from the observed workflow rather
   than from marketing language.

Exit gate: at least one repeated fixture shows a material reliability or
net-cost benefit, and the one-time low-risk fixture demonstrates correct
abstention with negligible overhead.

### Phase B: maintain open integrations

1. Wait for review on Agno, OpenHands, Goose, Awesome Copilot, mcp-odoo,
   Codex SDK, and ADK-Rust; respond promptly to maintainer feedback.
2. Keep Docker and both curated-list submissions current without posting
   status-only comments.
3. Rebase only when upstream drift requires it.
4. Make one follow-up only after a meaningful update; never post periodic bump
   comments.
5. If a project declines a hosted dependency, offer the local contract adapter
   and keep the remote adapter optional.
6. Treat the remaining Goose security scan as an upstream workflow failure.
   The content review about unqualified tool names was valid and is fixed; do
   not conflate that resolved feedback with the independent base-workflow
   checkout refusal.

Exit gate: each PR is merged or has received a final maintainer decision.

### Phase C: educational adoption

1. Wait for responses on the two Microsoft proposals.
2. If accepted, implement the vendor-neutral local exercise first.
3. Mention Agent Enhancer only as an optional free reference implementation.
4. Publish the same runnable fixture in this repository if the upstream
   project does not respond after one useful follow-up.

Exit gate: one portable lesson or sample runs without credentials and proves
the ambiguous-success invariant.

### Phase D: protocol-specific adoption

1. Turn the x402 challenge-drift reproduction into neutral fixtures.
2. Assert behavior for an unchanged challenge, changed challenge, expired
   quote, facilitator mismatch, timeout before settlement, and timeout after a
   possibly accepted payment.
3. Coordinate with issue #831 before creating a patch.
4. Keep Agent Enhancer branding out of the upstream tests. Publish a separate
   case study mapping those fixtures to the four x402 diagnostic modules.

Exit gate: maintainers accept the fixtures, guidance, or a narrower
maintainer-requested change.

### Phase E: framework and small-project expansion

1. Follow the existing mcp-use, LangChain, MCPJam, and Kiln discussions;
   implement only the maintainer-selected scope. Keep mcp-agent closed unless
   maintainers reopen or redirect it. Maintain the now-open Codex SDK and
   ADK-Rust PRs.
2. Use paired fixtures to show what framework durability solves and what still
   requires destination reconciliation.
3. Test Pydantic AI Harness interoperability before proposing any new
   capability.
4. Build atrib, Synapse, and cmuxlayer integrations locally first, respecting
   their Apache, AGPL, and contributor-vouch boundaries.
5. Open each resulting contribution only when it is independently useful,
   tested, and non-duplicative.

Exit gate: two independent frameworks can run the same conformance fixture
through the local contract adapter, and at least one can optionally use the
remote service.

### Phase F: promotion after useful work lands

For each merged integration:

1. Publish a case study with the original failure, unguarded outcome, guarded
   outcome, exact modules, measurements, and limitations.
2. Produce a short side-by-side GIF or video from captured test evidence.
3. Add the integration to the compatibility table and release notes.
4. Thank the project and share the specific example only in channels where
   project rules permit it.
5. Ask five developers to reproduce the example and report installation
   friction.
6. Separate owned automation from external usage in public metrics.

Consider a Show HN launch only after two workflow integrations merge and the
paired benchmark data is public.

## Contribution rules

- The upstream project must gain a runnable connector, test, lesson, fixture,
  or example. A backlink alone is not enough.
- Keep all examples deterministic and use synthetic destinations unless a
  maintainer explicitly requests a real provider.
- Never send credentials, user content, or destination records to the sidecar.
- Never claim cross-plugin transactions or universal exactly-once execution.
- Prefer a local adapter plus an optional remote adapter when an upstream
  project should not depend on a hosted vendor.
- Do not automatically comment on or modify third-party repositories.
- Detect CI failure, merge conflicts, endpoint drift, version drift, and broken
  links automatically, then require human review before any upstream action.
- Stop after one useful follow-up when a maintainer does not respond.

## License boundary

The main public repository remains MIT until a versioned licensing transition.
Already released MIT code cannot be withdrawn from existing recipients.

Future upstream patches may still be contributed under the receiving
repository's license when they are independently useful and contain no private
backend implementation. Mark the relevant files or patch with the required
SPDX identifier and record the exception in a `LICENSES` inventory.

Keep the hosted module implementations, payment code, production persistence,
and differentiating algorithms in the private service repository. Connectors,
schemas, fixtures, clients, and small reference adapters may remain public.

## Success criteria

Primary:

- merged workflow integrations;
- developers who reproduce a fixture successfully;
- verified workflows completed;
- duplicate mutations prevented;
- ambiguous outcomes reconciled or safely stopped;
- repeat external use;
- measured token, cost, or recovery benefit after sidecar overhead;
- correct abstention on low-risk work.

Secondary:

- registry presence;
- stars;
- directory count;
- social impressions.

Do not describe automated smoke tests as beta-user usage.

## Immediate order of work

1. Wait for decisions on every current pull request. Respond only to specific
   maintainer feedback; do not post status-only comments or open another PR
   while the current queue is under review.
2. Wait for placement decisions on MCPJam #3555 and Kiln #112. Resolve the
   canonical target behind the duplicate mcp-use #2054 issue. Do not duplicate
   the already-volunteered LangChain #170 work or reopen closed mcp-agent #640
   without maintainer direction.
3. Complete the frozen skills-first on-demand validation. Retain the result
   even if it is negative or neutral. Do not begin publication runs unless
   every fixed validation gate passes.
4. After design-partner recruitment begins, build local interoperability
   probes for Pydantic AI Harness and atrib, then
   a paired benchmark adapter for Synapse. Do not open upstream requests until
   those probes show a specific missing primitive. For each probe, require a
   runnable local fixture, a vendor-neutral output mapping, explicit external
   proof semantics, and a short statement of what the target already solves.
5. Wait for responses on Microsoft issues #949 and #115 and continue x402
   coordination through #831.
6. Promote only merged integrations and published evidence.

The local probes should answer narrow questions before any new contribution:

- Pydantic AI Harness: can `ToolEffectRecord`, including
  `unknown_after_crash`, map losslessly into `ReliabilityReportV1`, and which
  fields remain orchestrator-owned?
- atrib: which signed records prove authorship only, and which independent
  tool or counterparty attestations can justify `external_proof: true`?
- Synapse: does its receipt/checkpoint path reduce ambiguous replays under the
  same paired fixture, and how does its overhead compare with the skills-first
  sidecar?

Open an upstream issue or PR only if a completed local probe exposes one
specific missing primitive whose fix is useful without Agent Enhancer. Keep
the hosted backend implementation private and contribute only portable
schemas, adapters, examples, or fixtures under the receiving repository's
license.

## Existing production deployment policy

Use the existing DigitalOcean app behind `https://liberated.site` as the only
hosted development, debugging, and release target. Do not create a new app or
a permanent or temporary staging app.

- Run local validation before pushing the existing production source branch.
- Keep `PAYMENTS_MODE=disabled` and real USDC settlement off.
- Use opaque short-TTL fixture identities and mark owned production checks as
  internal automation.
- Exclude benchmark, CI, integration, and smoke-test traffic from public usage
  evidence.
- Temporary downtime is acceptable during the current customer-free beta.
- Keep migrations additive and preserve the prior known-good deployment for
  rollback.
- Do not create additional DigitalOcean infrastructure without a new explicit
  owner decision.
