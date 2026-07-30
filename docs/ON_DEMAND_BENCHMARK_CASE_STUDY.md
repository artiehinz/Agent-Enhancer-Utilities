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

| Scenario | Without sidecar | With sidecar | Decision |
|---|---:|---:|---|
| Ambiguous create | 20/20 verified, 0 harm | 20/20 verified, 0 harm | Do not claim a benefit |
| Overlapping workers | 8/20 verified, 24 harm counters | 19/20 verified, 2 harm counters | Use the sidecar when workers can overlap |
| Shared rate limit | 20/20 verified, 0 harm | 20/20 verified, 0 harm | Current fixture does not justify the overhead |
| Scheduled refresh | 18/20 verified, 2 duplicates | 20/20 verified, 0 duplicates | Use when stale duplicate work is consequential |
| Low-risk control | 20/20 verified | 20/20 verified, 20/20 abstained | Keep selection local and make no remote call |

Across the four risk scenarios, the frozen evaluator recorded 26 harmful
counters without the sidecar and 2 with it, a 92.308% reduction. Verified
completion rose from 82.5% to 98.75%. Activation and abstention were both
100%.

The harm metric is the preregistered sum of duplicate mutations, conflicting
actions, provider rejections, and unresolved ambiguous outcomes. It is a
counter total, not a claim that every counter is a distinct user incident.

## Cost of the guard

The guarded condition used substantially more model tokens and wall-clock time
in every risk-bearing scenario. Median paired input-token differences ranged
from +240% to +572%, and median latency differences ranged from +140% to
+365%. The sidecar is therefore not justified for every task.

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
