<p align="center">
  <img src="./assets/agents.png" width="128" height="128" alt="Agent Enhancer Utilities broken-chain icon">
</p>

<h1 align="center">Agent Enhancer Utilities</h1>

<p align="center">
  Six inspectable Agent Skills backed by a free, account-free MCP service for
  coordination, API failure testing, and MCP/x402 contract analysis.
</p>

<p align="center">
  <a href="https://liberated.site/status">Service status</a> ·
  <a href="https://liberated.site/effectiveness">Effectiveness</a> ·
  <a href="https://liberated.site/tools">22-module catalog</a> ·
  <a href="https://glama.ai/mcp/connectors/site.liberated/agent-utility-lab">Glama verified</a> ·
  <a href="./LICENSE">MIT license</a>
</p>

## Skills

| Skill | Use it for |
| --- | --- |
| `coordinate-parallel-agents` | Locks, deduplication, one-use batons, semaphores, shared rate gates, barriers, and freshness leases |
| `test-http-failure-paths` | Bounded status/failure sequences, webhook delivery attempts, Retry-After behavior, and synthetic fixtures |
| `debug-x402-integrations` | Evidence-linked x402 error diagnosis, requirement drift, and facilitator compatibility checks |
| `review-mcp-tool-contracts` | Tool schema, annotation, capability-handshake, elicitation, and edge-case review |
| `guard-x402-retries` | Detect changed payment requirements and bind one retry identity to one normalized quote |
| `measure-webhook-delivery` | Collect one-use, hash-only evidence about bounded webhook delivery attempts |

Every skill is a small Markdown workflow. Inspect its `SKILL.md` before
installation.

## Install

GitHub's native skill commands require GitHub CLI 2.90 or later:

```sh
gh skill preview artiehinz/Agent-Enhancer-Utilities coordinate-parallel-agents
gh skill install artiehinz/Agent-Enhancer-Utilities coordinate-parallel-agents
```

Cross-agent installation:

```sh
npx skills add artiehinz/Agent-Enhancer-Utilities
```

Agents can also connect without installing a skill:

| Surface | Endpoint | Shape |
| --- | --- | --- |
| Progressive MCP | `https://liberated.site/mcp` | Search, describe, invoke, and capability request |
| Claude | `https://liberated.site/mcp/claude` | 32 direct action-specific tools |
| ChatGPT | `https://liberated.site/mcp/chatgpt` | The same 32 direct tools |
| HTTP/OpenAPI | `https://liberated.site/v1/openapi.json` | Generated contracts for all 22 modules |

All public modules are currently free. Real USDC settlement is disabled.

## Directory listings

- [Official MCP Registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=site.liberated%2Fagent-utility-lab)
- [Glama](https://glama.ai/mcp/connectors/site.liberated/agent-utility-lab) — ownership verified
- [Smithery](https://smithery.ai/servers/artemhinz2/Agent-Enhancer-Utilities)

These listings point to the live service. The implementation is not published
in this skills repository.

## Trust and effectiveness

The service publishes:

- current per-module self-test results and dataset freshness at
  [`/status`](https://liberated.site/status);
- privacy-safe methodology and usage evidence at
  [`/effectiveness`](https://liberated.site/effectiveness);
- schemas, limits, side effects, retention, and typed errors in the
  [catalog](https://liberated.site/v1/catalog);
- privacy, acceptable-use, security, support, and pricing policies from the
  [service homepage](https://liberated.site).

The skills contain no hidden install telemetry. Do not send credentials,
wallet private keys, personal data, customer records, or conversation history
to the service.

## Repository scope

This public repository contains the reusable skills, their host metadata, and
project-level validation/documentation. The hosted service implementation is
operated separately. A skill must use progressive discovery and must not copy
private schemas, credentials, or backend source.

See [CONTRIBUTING.md](./CONTRIBUTING.md), [SECURITY.md](./SECURITY.md), and
[docs/EFFECTIVENESS.md](./docs/EFFECTIVENESS.md).

## License

MIT
