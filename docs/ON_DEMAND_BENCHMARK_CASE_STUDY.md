# Case study: skills-first reliability sidecar

## Question

Does one repo-scoped reliability skill improve a real multi-step Codex
workflow without the persistent MCP overhead measured in earlier validation?

The benchmark compares identical disposable tasks with and without the skill.
Neither condition exposes MCP. The guarded condition may call Agent Enhancer
through direct HTTP only after the local selector classifies the task as
risk-bearing.

## Frozen protocol

- Codex CLI `0.144.0-alpha.4`
- `gpt-5.6-sol` with medium reasoning
- 20 publication pairs per scenario
- randomized condition order
- identical prompts, capabilities, destination state, and injected failures
- condition-blind machine-state evaluation
- owned automation excluded from public service usage metrics

The preregistration, evaluator, fixture, protocol hashes, run-level rows, and
infrastructure exclusions are public under
[`examples/on-demand-agent-benchmark`](../examples/on-demand-agent-benchmark/).

## Result

The complete publication sample contains 200 valid runs and passes every
preregistered gate.

| Scenario | Acceptance without → with | Affected runs | Unresolved outcomes | Paired token p50 / p90 | Paired latency p50 / p90 | Decision |
|---|---:|---:|---:|---:|---:|---|
| Ambiguous create | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | +572% / +777% | +365% / +455% | Do not claim a benefit |
| Overlapping workers | 8 → 19 / 20 | 12 → 1 / 20 | 0 → 0 | +257% / +404% | +202% / +266% | Use when workers can overlap |
| Shared rate limit | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | +284% / +462% | +150% / +192% | The fixture does not justify the overhead |
| Scheduled refresh | 18 → 20 / 20 | 2 → 0 / 20 | 0 → 0 | +240% / +342% | +140% / +281% | Use when stale duplicate work matters |
| Low-risk control | 20 → 20 / 20 | 0 → 0 / 20 | 0 → 0 | -34% / +1% | -33% / -1% | Keep selection local; make no remote call |

Across the four risk scenarios, runs with at least one confirmed duplicate,
conflict, or rejection fell from 14/80 without the sidecar to 1/80 with it, a
92.857% reduction. The frozen `verified` field is an acceptance result from a
condition-blind evaluator, not a measure of how often the evaluator looked.
Acceptance rose from 66/80 to 79/80; the evaluator ran and a final response
was present for all 160 retained risk-scenario rows.

Unresolved outcomes were 0 in both conditions. The original pooled 26-to-2
counter result therefore did not mix unknown outcomes into confirmed harm in
this sample. It did, however, pool correlated categories: 12 unguarded overlap
runs each contributed one duplicate-mutation and one conflicting-action
counter, and one guarded overlap run contributed both. The pooled total is
preserved as secondary evidence, not presented as 26 independent incidents.

This is a post-hoc descriptive reanalysis of the already published rows. It
does not alter the preregistration, rows, gates, or causal claim. The
reproducible output is
[`publication-reanalysis.json`](../examples/on-demand-agent-benchmark/results/publication-reanalysis.json).

## Cost of the guard

The guarded condition used substantially more model tokens and wall-clock time
in every risk-bearing scenario. Median paired input-token differences ranged
from +240% to +572%, with p90 differences from +342% to +777%. Median latency
differences ranged from +140% to +365%, with p90 differences from +192% to
+455%. The sidecar is therefore not justified for every task.

Low-risk guarded runs showed lower median tokens and latency, but the selector
made zero adapter and remote calls. The difference is ordinary host-run
variance and is not attributed to Agent Enhancer.

ChatGPT-managed Codex authentication exposed token counts but no defensible
per-run dollar rate, so model cost remains `null`.

## Exclusions and limitations

Three guarded shared-rate attempts timed out during the first publication
pass. The resume path discarded one partial counterpart and reran all three
pairs without changing the protocol. The four excluded rows remain in the
report.

The destination and failures are synthetic. One model, one reasoning setting,
and one host cannot establish universal behavior. The skill is advisory and
cannot enforce a transaction inside another MCP.

## Product decision

Keep the skills-first path as the recommended integration:

1. abstain locally for ordinary one-time low-risk work;
2. activate for overlapping workers, consequential scheduled refreshes, and
   other demonstrated duplicate-sensitive conditions;
3. disclose the token and latency cost before recommending broader use; and
4. require external design-partner evidence before adding another stateful
   module or enabling paid capacity.

The next proof is a 14-day reproduction with five external design partners,
not another synthetic module expansion.
