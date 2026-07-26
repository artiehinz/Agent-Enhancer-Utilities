# Changelog

## Unreleased

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
