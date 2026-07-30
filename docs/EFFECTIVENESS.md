# Effectiveness evidence

Agent Enhancer Utilities separates four questions:

1. **Contract correctness:** Does each input/output schema, limit, annotation,
   and error behave as published?
2. **Runtime health:** Does every public module pass its bounded production
   self-test on the deployed module version?
3. **Observed reliability:** For real external requests, what share of valid
   executions complete, fail, replay safely, or miss coverage, and how long do
   they take?
4. **User outcome:** Did the utility actually help the agent finish its larger
   job?

The first three are machine-verifiable. The fourth requires explicit,
privacy-safe user feedback and cannot be inferred from HTTP success alone.

Current public evidence:

- [`/v1/status`](https://liberated.site/v1/status) publishes module versions,
  release state, self-test status/time/latency, and dataset freshness.
- [`/v1/effectiveness`](https://liberated.site/v1/effectiveness) publishes the
  methodology, coverage totals, and sufficiently large aggregated usage
  samples after the external-use baseline is activated.
- The service release workflow executes every direct Claude and ChatGPT tool,
  negative-selection cases, replay cases, migrations, and PostgreSQL/Valkey
  state before publication.

Public usage aggregates exclude raw inputs, identifiers, IP addresses, user
agents, and low-volume per-module samples. Internal monitoring must be
cryptographically marked and removed from the baseline before observed
reliability is displayed.

Backend `0.6.4` established the clean public baseline at
`2026-07-28T19:07:18.657Z`. The prior mixed automation window is retained
internally as aggregate counts only; its raw discovery and module observations
were removed and are excluded from public evidence. A full marked production
acceptance afterward invoked every direct tool on both connector surfaces and
left the public observation count at zero.

Planned outcome evidence is a one-use, receipt-linked rating with fixed
categories and no free text. It must be abuse-resistant and optional before it
can be treated as product-effectiveness evidence.

## Cross-plugin sidecar outcomes

For guarded external-plugin workflows, report evidence from the larger
workflow separately from Agent Enhancer tool success:

- a denied lock is direct evidence that an overlapping worker was blocked, but
  not that the external operation completed;
- a seen-stamp hit is evidence of prior sidecar state, not proof that an
  external record still exists;
- a verified destination marker is evidence that the external record was
  observed, subject to the destination's consistency guarantees;
- a rate-gate denial is evidence that shared quota consumption was bounded;
- a barrier release is evidence of the configured unique arrivals, not the
  quality of their work.

A future workflow checkpoint must return `external_proof: false` even for a
`caller_verified` stage. It can preserve the class of evidence reported by the
caller, but the service does not independently inspect or attest to the
external plugin.

Aggregate guarded-batch outcomes may count attempted, already seen, blocked,
throttled, verified, uncertain, failed, and awaiting-review items. Do not
retain source records or infer duplicate prevention without an observed
conflicting attempt. Every material outcome should include one standard
guarantee label from the sidecar reliability contract.

## Paired reliability benchmark

The public
[`sidecar-benchmark`](../examples/sidecar-benchmark/)
pre-registers five deterministic scenarios, executes five excluded harness
validation pairs, then publishes 20 pairs per scenario with randomized
condition order.

The first evidence tier is deliberately model-free. It measures injected
failure behavior, external attempts, duplicate mutations, conflicting
actions, provider rejections, unresolved ambiguity, and sidecar calls. Its
model-token and model-cost fields are `null`; it cannot demonstrate better
reasoning, token savings, or lower real-agent cost.

The committed
[`results/latest.json`](../examples/sidecar-benchmark/results/latest.json)
contains the sanitized run-level rows, aggregates, thresholds, evaluation,
and limitations. The ambiguous-success fixture commits a write, drops the
response, and demonstrates that the guarded condition reconciles through a
stable marker without replaying the mutation.

The first real-agent validation is preserved in
[`validation-0.6.4.json`](../examples/sidecar-agent-benchmark/results/validation-0.6.4.json).
Across 25 pairs, the six-tool sidecar profile reduced none of the eight
harmful overlap events. It preserved aggregate verified completion and made
zero sidecar calls on the low-risk task, but connecting it still added 10.466%
median input-token overhead and 28.431% median latency overhead on that task.
The validation therefore failed three of five preregistered gates. This is a
negative product result, not evidence of user benefit.

Backend `0.6.5` responded with a three-tool core profile and stronger
server-side selection guidance. Its completed
[`validation-0.6.5-core.json`](../examples/sidecar-agent-benchmark/results/validation-0.6.5-core.json)
sample kept the model, prompts, evaluator, fixtures, metrics, exclusions,
sample size, and thresholds fixed.

That product change produced a real but incomplete improvement:

- harmful events fell from six unguarded to zero guarded;
- verified completion rose from 80% unguarded to 90% guarded;
- low-risk sidecar calls remained zero;
- low-risk median input-token overhead was 10.779%; and
- low-risk median latency overhead was 27.341%.

The validation therefore passed the harm, completion, and abstention gates but
failed both overhead gates. The two validation samples are not pooled. No
200-run publication sample or broad effectiveness claim is justified yet.
The next product iteration must reduce host-visible MCP metadata while
preserving access to all modules and the observed overlap protection.

The 136 module observations recorded during the validation window are treated
as mixed owned automation, not external beta usage. The original dotted-key
override quoted the HTTP header name, so Codex rejected the marker while
continuing the MCP session. Backend `0.6.7` advances the public cutoff while
retaining the privacy-bounded historical rows and auditing their aggregate
counts. Future runs start only after Codex receives
`owned_automation_excluded=true` on a small catalog search, and every sidecar
invocation is independently checked for
`execution.owned_automation_excluded=true`.

An explicitly exploratory five-pair compact-profile probe then produced ten
valid low-risk rows and zero sidecar calls. Median input-token overhead was
10.561% and median latency overhead was 38.523%, against the same 5%
references. This is not confirmatory evidence. It shows that shrinking the
persistent MCP schema alone does not justify another always-connected
validation; the next candidate must avoid connecting on low-risk work.

## Skills-first publication evidence

The independent
[`on-demand-agent-benchmark`](../examples/on-demand-agent-benchmark/)
removes persistent MCP from both conditions. Only the guarded condition
receives one repo-scoped skill, which selects locally and calls direct HTTP
only for risk-bearing work. Its five-pair validation passed before the
publication sample began.

The complete
[`publication-latest.json`](../examples/on-demand-agent-benchmark/results/publication-latest.json)
contains 200 valid runs, 20 pairs per scenario, with randomized condition
order and condition-blind machine-state evaluation. Across the four risk
scenarios:

- harmful counters fell from 26 unguarded to 2 guarded, a 92.308% reduction;
- verified completion rose from 82.5% to 98.75%;
- correct activation was 100%; and
- all 20 low-risk guarded runs correctly abstained with zero adapter and
  remote calls.

The result is not a general speed or cost claim. Overlapping-worker protection
produced the strongest benefit, and scheduled refresh produced a smaller
benefit. Ambiguous-create and shared-rate controls were already 20/20 without
the sidecar. Every risk-bearing guarded scenario used substantially more
tokens and wall-clock time.

Low-risk median input tokens and latency were lower in the guarded condition,
but the skill made no adapter or remote call. Those differences are treated as
host variance, not Agent Enhancer savings. Model cost remains unavailable
because ChatGPT-managed Codex authentication did not expose a defensible
per-run dollar rate.

Three initial guarded shared-rate attempts timed out. Their failed rows and
one discarded partial counterpart remain as four infrastructure exclusions;
all three pairs were rerun under the unchanged frozen protocol. The report
therefore preserves negative, neutral, excluded, and successful evidence.

See the
[publication case study](./ON_DEMAND_BENCHMARK_CASE_STUDY.md)
for the scenario-level interpretation and product decision.
