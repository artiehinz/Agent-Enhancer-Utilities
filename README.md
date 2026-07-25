# Agent Enhancer Utilities

Three narrow Agent Skills for reliable autonomous-agent workflows:

- `coordinate-parallel-agents`
- `test-http-failure-paths`
- `debug-x402-integrations`

Each skill uses the public, account-free Agent Enhancer Utilities service. The
progressive-discovery MCP endpoint is `https://liberated.site/mcp`; the
Claude-specific direct-tool endpoint is `https://liberated.site/mcp/claude`.

Inspect every skill before installation. GitHub's native commands require
GitHub CLI 2.90 or later:

```sh
gh skill preview artiehinz/agent-utility-skills coordinate-parallel-agents
gh skill install artiehinz/agent-utility-skills coordinate-parallel-agents
```

The cross-agent alternative is:

```sh
npx skills add artiehinz/agent-utility-skills
```

Service release 0.4.0 contains 14 free production-beta modules. Its
machine-readable catalog, schemas, limits, side effects, retention, and typed
errors are published at `https://liberated.site/v1/catalog` after promotion.

No skill asks for credentials, wallet private keys, personal data, or full
conversation history. Public service terms, privacy, acceptable-use, security,
support, and status information are linked from `https://liberated.site`.

## Roadmap

- **Cross-host acceptance:** Clean-install and exercise all three skills on
  Codex, Claude, and Copilot after the 0.4.0 backing service is live.
- **Adoption evidence:** Link each skill to a host-specific 60-second
  quickstart, add an opt-in issue template for discovery/install failures, and
  measure successful workflows and repeat use at the service rather than adding
  hidden install telemetry.
- **Claude Connectors Directory:** Anthropic's
  [current submission guidance](https://claude.com/docs/connectors/building/submission)
  requires a Team or Enterprise organization and Directory management access
  for remote-server submissions. The isolated free endpoint, annotations,
  public policies, limits, and negative-case tests are ready. Purchase the
  minimum suitable plan, submit the free connector, and keep the organization
  active through review. Before cancelling, confirm with
  `mcp-review@anthropic.com` whether the listing persists and which health,
  usage, feedback, and listing-management functions remain available after the
  plan expires.
- **New workflow packages:** Add focused skills after their backing modules are
  live and externally validated. Current candidates are MCP contract and
  capability-handshake compatibility, webhook delivery measurement, x402
  requirement drift, facilitator compatibility, quote fingerprints, and
  offer/receipt verification.

## License

MIT
