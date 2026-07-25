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
