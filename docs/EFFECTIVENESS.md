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

A later measured-agent tier must keep the host, model version, reasoning
setting, prompts, workspace, tools, timeouts, and failure injection fixed.
Publish that tier separately rather than combining its claims with the
deterministic fixture.
