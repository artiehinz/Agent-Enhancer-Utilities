# Metered Codex sidecar benchmark

This second evidence tier runs the same isolated task through Codex with and
without the production Agent Enhancer MCP. Unlike the deterministic protocol
fixtures in [`../sidecar-benchmark`](../sidecar-benchmark/), it records real
host token usage, tool calls, latency, agent behavior, and machine-verified
destination outcomes.

The preregistration fixes:

- Codex CLI `0.144.0-alpha.4`;
- model `gpt-5.6-sol` at medium reasoning;
- exactly two requested subagents in the parallel scenarios;
- the prompt, workspace, failure injection, timeout, and evaluator;
- five excluded validation pairs and 20 publishable pairs per scenario; and
- the success thresholds and exclusions.

The first completed validation against backend `0.6.4` and its six-tool
facade failed. Its sanitized summary is retained in
[`results/validation-0.6.4.json`](./results/validation-0.6.4.json). Backend
`0.6.5` introduced a three-tool core profile and stronger server instructions.
Its completed summary is retained in
[`results/validation-0.6.5-core.json`](./results/validation-0.6.5-core.json).
The task prompts, fixtures, evaluator, metrics, exclusions, sample sizes, and
thresholds were unchanged, and old and new rows were never pooled.

The core validation passed harm reduction, verified completion, and
abstention, but failed input-token and latency overhead. Do not run the
publication command below against this preregistration. A future iteration
must first reduce connection-only metadata cost and freeze a new
preregistration.

Every report hashes the preregistration, prompt/runner, blind evaluator,
fixture, and final-response schema together. A changed protocol cannot resume
into an older sample. Parallel scenarios also require an observed Codex
collaboration event; destination success from a single-agent shortcut is not
accepted.

The task prompt is identical inside each pair. The only condition difference
is whether the `agent_enhancer` MCP is connected. User and project Codex
configuration are ignored, Codex Apps are disabled in both conditions,
sessions are ephemeral, and every production MCP request must carry the
private owned-automation marker. A run that calls any unexpected MCP server is
automatically excluded as infrastructure contamination.

This Windows Codex build blocks the fixture interpreter under
`workspace-write`, so preregistered runs use `danger-full-access` only inside a
new disposable directory containing the public synthetic fixture. The prompt
forbids web access and work outside that directory.

## Run validation

Set `AGENT_ENHANCER_INTERNAL_METRICS_TOKEN` in the process environment from a
local secret store. Never put its value in this repository.

Before any measured run starts, the harness makes one small catalog search
through Codex and requires production to return
`owned_automation_excluded=true`. A missing, stale, or dropped marker fails
the run before the benchmark schedule begins. Every later sidecar invocation
is checked again under `execution`.

The earlier dotted-key command-line override quoted the HTTP header name
itself, so Codex rejected that header while continuing the MCP session. The
current harness uses one TOML inline map for each header collection and tests
the exact generated arguments.

Before freezing another confirmatory plan, the non-publishable compact
engineering probe runs only the five low-risk pairs:

```powershell
python -B examples/sidecar-agent-benchmark/probe_compact.py
```

Its ignored local report cannot support a product claim. It answers only
whether the one-tool compact connection is likely to justify another full
preregistration. The completed probe did not: all ten rows were valid and made
zero sidecar calls, but median input-token overhead was 10.561% and median
latency overhead was 38.523%, above the same 5% references.

```powershell
python -B examples/sidecar-agent-benchmark/run.py --phase validation
```

The runner checkpoints after every host run and resumes automatically. Local
validation output and retained debug workspaces are ignored by Git.

The preregistration records the setup-only amendments discovered before the
five-pair validation sample. Failed CLI launches and the first executable
catalog-discovery pilot are retained locally as exclusions; they are not
publishable outcome rows.

After all validation pairs complete, review only harness or infrastructure
defects. Start publication only if every preregistered gate passes. Freeze any
later product or harness change in another preregistration. Do not tune prompts
based on which condition won.

```powershell
python -B examples/sidecar-agent-benchmark/run.py --phase publication
```

Publication writes sanitized rows to `results/latest.json`. That file contains
opaque run IDs, metrics, and aggregate controls. It does not include prompts,
event transcripts, credentials, destination payloads, or personal data.

## Honest interpretation

The benchmark may find a reliability benefit, no difference, or extra
overhead. Codex can independently apply good retry and coordination practices,
so an unguarded run may already avoid some failures. All valid neutral and
negative results remain in the report.

ChatGPT-managed Codex auth reports input, cached-input, output, and reasoning
tokens, but it does not provide a defensible per-run dollar price. Cost stays
`null`; this benchmark does not manufacture a cost-saving claim.
