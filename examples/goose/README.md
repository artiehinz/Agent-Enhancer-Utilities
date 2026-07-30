# goose reliability-sidecar recipe

This local example gives [goose](https://github.com/aaif-goose/goose) its normal
workspace tools and adds Agent Enhancer as a free, no-auth MCP reliability
sidecar. goose still performs the task. The sidecar prepares the guard plan,
coordinates one opaque checkpoint for duplicate-sensitive effects, and records
the evidence class goose reports after destination read-back.

The recipe deliberately stops instead of blindly retrying an ambiguous
external create, send, delete, or other harmful action. A checkpoint coordinates
cooperating callers; it is not a transaction and its `external_proof` field
always remains `false`.

## Run it

Install a current goose CLI or Desktop build, then validate the recipe:

```sh
goose recipe validate examples/goose/agent-enhancer-reliability-sidecar.yaml
```

Open it in goose Desktop:

```sh
goose recipe open examples/goose/agent-enhancer-reliability-sidecar.yaml
```

Desktop displays a task field before starting. From the CLI, pass the task
explicitly and keep the session interactive when approvals or missing safety
facts may need clarification:

```sh
goose run \
  --recipe examples/goose/agent-enhancer-reliability-sidecar.yaml \
  --params task="Update the local changelog, run its tests, and verify the diff" \
  --interactive
```

The recipe declares goose's built-in `developer` extension and the Agent
Enhancer extension. Because that recipe list replaces profile extensions for a
new session, a task in GitHub, Slack, a database, or another service must supply
the appropriate domain extension separately through goose CLI or launch
metadata. If the session lacks a tool that can perform the action and read the
destination back, stop and relaunch with that extension. The domain tool—not
Agent Enhancer—must supply the actual result and evidence.

## What to expect

For every task, goose first invokes the deterministic
`workflow-guard-planner`. An ordinary one-time low-risk operation may receive a
`no-sidecar` decision. For a guarded duplicate-sensitive effect, goose:

1. derives opaque per-run identifiers without sending task content;
2. claims `workflow-checkpoint` before a destination preflight;
3. stands down if another caller owns the claim;
4. performs the authorized domain action once;
5. reads the result back from the destination; and
6. records `caller_verified`, or records `external_result_uncertain` and stops
   when the outcome cannot be established safely.

The endpoint adds the privacy-safe aggregate source tag `goose-recipe`. It
requires no Agent Enhancer account or API key. Do not put credentials, personal
data, external response bodies, or raw task content into sidecar requests.

The recipe follows goose's current `1.0.0` recipe schema and uses its
`streamable_http` extension type. The authoritative format and validation
command are documented in the
[goose recipe reference](https://goose-docs.ai/docs/guides/recipes/recipe-reference/).
