# Architecture

Agent Enhancer Utilities is a reliability sidecar. An agent deliberately adds
it to a workflow; it does not intercept, proxy, or gain control over another
agent or plugin.

```text
user task
   |
   +-- domain agent or plugin ---- performs and verifies domain work
   |
   +-- Agent Enhancer skill ----- selects a safe reliability recipe
             |
             +-- progressive MCP
                   search -> describe -> invoke
                             |
                             +-- bounded deterministic utility
```

## Public package

The public repository contains:

- seven inspectable skills under `skills/`;
- host manifests for Codex/ChatGPT, Claude Code, GitHub Copilot CLI, and Gemini
  CLI;
- one no-auth Streamable HTTP MCP connection definition;
- deterministic local reference code, schemas, evaluations, documentation,
  and runnable examples; and
- the correct public icon, license, contribution policy, and security policy.

The hosted implementation is operated separately and is not represented as
open-source code in this repository.

## Runtime boundaries

The progressive MCP surface at `https://liberated.site/mcp` exposes compact
discovery tools. Agents search for a capability, inspect its exact schema and
safety metadata, and invoke it only when it matches.

The sidecar receives bounded capability facts or opaque identifiers. The
domain agent keeps provider credentials, private records, business payloads,
and the authority to perform external actions. A checkpoint records
coordination state and caller-reported verification; it never constitutes
independent proof that another provider completed an action.

All public modules are currently free. The manifests request no API key and
enable no wallet, signing, settlement, or transfer capability.

## Reliability guarantees

Guarantees are selected from the weakest supportable boundary:

- `provider-idempotent` requires a provider idempotency key or atomic
  uniqueness primitive;
- `duplicate-resistant` requires destination search or read-back evidence;
- `concurrency-safe` coordinates participating workers but cannot constrain an
  unguarded writer;
- `rate/concurrency-bounded` limits participating load; and
- `best-effort` is used when an uncertain external result cannot be resolved.

Agent Enhancer state never upgrades an external provider's guarantee by
itself.
