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
defects. Freeze any justified changes in a new preregistration before starting
publication. Do not tune prompts based on which condition won.

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
