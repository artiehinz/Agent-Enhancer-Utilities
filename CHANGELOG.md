# Changelog

## Unreleased

- Deploy backend `0.6.5` with a three-tool core MCP profile that can still
  discover and invoke all 24 modules.
- Publish the failed backend `0.6.4` metered validation summary instead of
  turning it into a favorable claim.
- Pre-register a fresh validation against the smaller core profile without
  changing the prompts, fixtures, evaluator, metrics, exclusions, or gates.

## 1.6.0 - 2026-07-28

- Publish the vendor-neutral Reliability Sidecar Contract v1 and closed schema
  definitions for capability facts, plans, checkpoints, evidence, and reports.
- Add local and optional remote checkpoint adapters.
- Add a pre-registered deterministic paired benchmark with five scenarios,
  five excluded validation pairs, 20 published pairs per scenario, sanitized
  run-level evidence, and explicit non-claims for unavailable model usage.
- Deploy backend `0.6.4` with a database-backed clean public-metrics cutoff;
  marked full production acceptance writes zero public observations.
- Add an upstream-schema-validated Goose reliability-sidecar recipe using the
  free, no-auth progressive MCP endpoint.

## 1.5.0 - 2026-07-25

- Package the repository for Codex/ChatGPT, Claude Code, GitHub Copilot CLI,
  Gemini CLI, and generic Streamable HTTP MCP clients.
- Move all seven skills into the canonical `skills/<name>/` layout.
- Add a general reliability-sidecar example and a live two-worker checkpoint
  example.
- Add explicit compatibility evidence and architecture documentation.
- Keep every public module free and keep real USDC settlement disabled.

Existing `v1.4.1` links remain available through that immutable tag. Consumers
that track the default branch must update direct skill paths to include the
`skills/` prefix.
