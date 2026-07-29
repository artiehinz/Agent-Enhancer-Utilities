# Open-Source Integration and Sidecar Adoption Plan

Last reviewed: 2026-07-28

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

Keep at most two new workflow-integration pull requests active at once.
Registry and curated-list maintenance do not consume those two slots.

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
| [docker/mcp-registry #4537](https://github.com/docker/mcp-registry/pull/4537) | Remote MCP registry definition | Connects to all 24 modules through the six progressive MCP tools | Keep the listing, icon, endpoint, version, and links current. Comment only after a material change or maintainer request. |
| [OpenHands/extensions #418](https://github.com/OpenHands/extensions/pull/418) | No-auth remote MCP catalog connector | Connects OpenHands to all 24 modules; no backend code is copied | This is active integration slot 1. Monitor CI and review. Keep the patch metadata-only. |
| [agno-agi/agno #9178](https://github.com/agno-agi/agno/pull/9178) | Deterministic recovery cookbook | Uses `workflow-guard-planner` and `workflow-checkpoint` | This is active integration slot 2. The body now closes issue #9179 and the triage check passes; leave the stale maintainer-owned label untouched and wait for review. |
| [punkpeye/awesome-mcp-servers #10889](https://github.com/punkpeye/awesome-mcp-servers/pull/10889) | Curated server listing | Lists the complete service; description covers all bundles | Wait for a maintainer answer about the verified Glama Connector score and badge path. Do not send another comment without new evidence. |
| [punkpeye/awesome-mcp-devtools #242](https://github.com/punkpeye/awesome-mcp-devtools/pull/242) | Focused testing-tool listing | Emphasizes Failure rehearsal, MCP contracts, and x402 diagnostics; the endpoint still exposes all 24 modules | Monitor only. Do not duplicate this entry in more generic awesome lists. |
| Official MCP Registry | Published server metadata | Connects clients to all 24 modules | Continue version publication and endpoint smoke tests for each backend release. |

### Prepared but intentionally not submitted

| Repository | Proposed contribution | Modules | Gate |
| --- | --- | --- | --- |
| [aaif-goose/goose](https://github.com/aaif-goose/goose) | Reliability-sidecar recipe in which Goose asks for the task, plans the guard, checkpoints the attempt, executes through another MCP, and reconciles uncertainty | `workflow-guard-planner`, `workflow-checkpoint` | Keep the tested recipe in `examples/goose/` while external recipes and MCP additions are paused. Submit only when maintainers reopen that path. |

### Waiting for maintainer interest

| Repository | Proposed contribution | Modules or portable equivalents | Gate |
| --- | --- | --- | --- |
| [microsoft/mcp-for-beginners #949](https://github.com/microsoft/mcp-for-beginners/issues/949) | Vendor-neutral lesson and ambiguous-success exercise | Teach the portable equivalents of `workflow-guard-planner` and `workflow-checkpoint`; optionally use `failure-sequence-forge` for the exercise | Do not open a PR until a maintainer confirms scope and placement. The lesson must run locally without Agent Enhancer. |
| [microsoft/Agent-Framework-Samples #115](https://github.com/microsoft/Agent-Framework-Samples/issues/115) | Multi-agent handoff with two competing workers, one synthetic write, a lost response, reconciliation, and evidence | `workflow-guard-planner`, `workflow-checkpoint`; local `ReliabilityBackend` required, remote adapter optional | Do not open a PR until maintainers select language and placement. |
| [x402-foundation/x402 #831](https://github.com/x402-foundation/x402/issues/831) | Neutral conformance fixtures and retry guidance for payment requirements that change during retry | Fixtures correspond to `x402-requirement-drift-diff`, `x402-quote-fingerprint-guard`, and `x402-error-rosetta-stone`; `failure-sequence-forge` can author the local rehearsal | Wait until one active integration slot is free and coordinate with maintainers to avoid overlapping fixes. Upstream tests must not require the hosted MCP. |

### Next candidates after an active slot opens

Approach these one at a time, with an issue or discussion before implementation:

1. **[lastmile-ai/mcp-agent](https://github.com/lastmile-ai/mcp-agent)**:
   contribute a durable orchestrator-workers example showing the boundary
   between framework durability and a possibly committed external MCP write.
   Use a local adapter in tests and an optional Agent Enhancer adapter using
   `workflow-guard-planner` and `workflow-checkpoint`. Its existing workflow,
   Temporal, tracing, and token-accounting features also make it a strong host
   for the paired benchmark.
2. **[pydantic/pydantic-ai-harness](https://github.com/pydantic/pydantic-ai-harness)**:
   request a reusable reliability capability only after benchmark evidence is
   public. It should combine planning, checkpointing, honest evidence labels,
   and correct abstention, with local tests and an optional remote adapter.
3. **[langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)**:
   propose a multi-server recovery example rather than a product listing.
   Demonstrate one domain MCP plus one reliability MCP, an uncertain mutation,
   destination read-back, and no blind replay.

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

### Phase B: finish the two active integrations

1. Respond to Agno review; the issue-link requirement is complete.
2. Monitor OpenHands catalog CI and respond to review.
3. Rebase only when upstream drift requires it.
4. Make one follow-up after a meaningful update; never post periodic bump
   comments.
5. If a project declines a hosted dependency, offer the local contract adapter
   and keep the remote adapter optional.

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

### Phase E: framework expansion

1. Select `mcp-agent` first because it is MCP-native and already supports
   durable workflows, tracing, and token accounting.
2. Use the paired benchmark to show what framework durability solves and what
   still requires destination reconciliation.
3. Approach Pydantic AI Harness only after the contract and benefit evidence
   are stable.
4. Approach LangChain MCP Adapters only with a compact multi-server example
   that fills a documented gap.
5. Keep no more than two active workflow PRs across all frameworks.

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

1. Replace persistent connection overhead with conditional activation while
   preserving the `0.6.5` validation's observed duplicate prevention. The
   `0.6.8` compact probe still exceeded both 5% overhead references, so do not
   freeze a third always-connected preregistration. Prototype the current
   service through the skills and HTTP contracts, then preregister only if
   low-risk work incurs no connection.
2. Respond to review on Agno PR #9178; `Closes #9179` is present.
3. Monitor and maintain OpenHands PR #418.
4. Monitor the Docker and two curated-list submissions without opening more
   listing PRs.
5. Publish Reliability Sidecar Contract v1 and its conformance fixtures.
6. Wait for responses on Microsoft issues #949 and #115.
7. When one integration slot opens, coordinate x402 fixtures through issue
   #831.
8. After the next slot opens, approach `lastmile-ai/mcp-agent`.
9. Promote only merged integrations and published evidence.

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
