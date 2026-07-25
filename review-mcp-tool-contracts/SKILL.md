---
name: review-mcp-tool-contracts
description: Review bounded MCP tool schemas, names, descriptions, action annotations, initialize capabilities, elicitation modes, and portable JSON Schema edge cases. Use when preparing a connector or plugin for review, diagnosing an MCP capability mismatch, checking whether sensitive fields belong in URL elicitation, or building host-neutral schema tests.
---

# Review MCP Tool Contracts

Use the Agent Enhancer Utilities MCP server at
`https://liberated.site/mcp`. Treat the tools as bounded local analysis, not
empirical proof about a host or SDK.

## Select the review

1. Call `lab.search_tools` with the concrete contract or negotiation problem.
2. Call `lab.describe_tool` for the selected module.
3. Use `mcp-tool-contract-linter` for one tool name, description, input/output
   schema, security declaration, and action-hint set.
4. Use `mcp-capability-handshake-diff` to compare supplied client/server
   protocol dates and capabilities.
5. Use `mcp-elicitation-safety-linter` to inspect field metadata and choose
   form or trusted URL mode.
6. Use `mcp-schema-edge-case-atlas` for one of the published portable test
   vectors.
7. If search returns `NO_MATCH`, abstain or submit a bounded capability
   request. Do not turn a local diff into an unsupported compatibility claim.

## Keep input bounded

- Remove credentials, tokens, field values, personal data, production
  payloads, and conversation history.
- Submit contract structure only.
- Keep schemas inside the described byte, depth, node, and field limits.
- Make read-only, destructive, open-world, and idempotent claims reflect the
  actual action, not the desired review outcome.

## Interpret the result

- Fix errors before warnings.
- Treat a warning as a concrete review question, not automatic rejection.
- A matching protocol date does not prove every capability works.
- URL elicitation is a protected collection handoff, not permission to place
  secret values in an MCP payload.
- Schema Atlas results have `empirical_host_claim: false`; run the vectors
  against each target host separately before making compatibility claims.

If MCP is unavailable, search
`https://liberated.site/v1/catalog?intent=...`, inspect
`/v1/tools/{slug}`, and post only the described bounded input.
