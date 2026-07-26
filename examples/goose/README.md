# Goose reliability-sidecar recipe

This local example gives [Goose](https://github.com/aaif-goose/goose) its normal
workspace tools and adds Agent Enhancer as a free, no-auth MCP reliability
sidecar. Goose still performs the task. The sidecar prepares the guard plan,
coordinates one opaque checkpoint for duplicate-sensitive effects, and records
the evidence class Goose reports after destination read-back.

The recipe deliberately stops instead of blindly retrying an ambiguous
external create, send, delete, or other harmful action. A checkpoint coordinates
cooperating callers; it is not a transaction and its `external_proof` field
always remains `false`.

## Run it

Install a current Goose CLI or Desktop build, then validate the recipe:

```sh
goose recipe validate examples/goose/agent-enhancer-reliability-sidecar.yaml
```

Open it in Goose Desktop:

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

The recipe includes Goose's built-in `developer` extension for workspace work.
For a task in GitHub, Slack, a database, or another service, add the appropriate
domain extension before use and retain the same preflight/read-back rules. The
domain tool—not Agent Enhancer—must supply the actual result and evidence.

## What to expect

For every task, Goose first invokes the deterministic
`workflow-guard-planner`. An ordinary one-time low-risk operation may receive a
`no-sidecar` decision. For a guarded duplicate-sensitive effect, Goose:

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

The recipe follows Goose's current `1.0.0` recipe schema and uses its
`streamable_http` extension type. The authoritative format and validation
command are documented in the
[Goose recipe reference](https://goose-docs.ai/docs/guides/recipes/recipe-reference/).
