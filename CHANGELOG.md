# Changelog

## Unreleased

- Deploy backend `0.6.5` with a three-tool core MCP profile that can still
  discover and invoke all 24 modules.
- Publish the failed backend `0.6.4` metered validation summary instead of
  turning it into a favorable claim.
- Publish the backend `0.6.5` core-profile validation: harmful events fell
  from six to zero and verified completion rose from 80% to 90%, but
  connection-only token and latency overhead still failed the fixed gates.
- Keep the 200-run publication phase blocked while a smaller host-visible MCP
  surface is designed and preregistered.

## 1.7.0 - 2026-07-31

- Require `workflow-checkpoint` for material duplicate-sensitive writes that
  can overlap, retry, or run on a schedule; keep simple locks for lower-risk
  ownership and read coordination.
- Add the durable `external_attempt_started` runtime transition, typed
  `write_execution_in_progress` claim disposition, and uncertainty-preserving
  expiry recovery.
- Add a compact on-demand `execution_recipe` with preflight, attempt boundary,
  verification, recovery, and prohibited blind-retry guidance.
- Publish Reliability Sidecar Contract v1 schema revision 2 without changing
  the contract version or the 37-tool connector count.

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
