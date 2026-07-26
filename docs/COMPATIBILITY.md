# Compatibility

Last verified: 2026-07-25

Compatibility means more than the presence of a manifest. The tables separate
checks reproduced in this repository from host installations that still need
to be run after the `v1.5.0` tag is public.

## Reproduced checks

| Surface | Version or protocol | Evidence | Result |
| --- | --- | --- | --- |
| Progressive MCP | MCP `2025-03-26`, backend `0.6.2` | Both runnable examples initialized `https://liberated.site/mcp`, searched, described, and invoked the expected free modules | Passed |
| Codex plugin package | Codex CLI `0.144.0-alpha.4` | `.codex-plugin/plugin.json` passed the local OpenAI plugin validator; all referenced skills, MCP config, and image assets exist | Package passed |
| Claude Code plugin | Claude Code `2.1.220` | `claude plugin validate .` accepted the manifest, all seven skills, and companion MCP configuration | Passed |
| GitHub Copilot CLI plugin | Copilot CLI `1.0.75` | An isolated local install accepted `plugin.json` and reported version `1.5.0` with seven installed skills | Passed |
| Agent Skills archive | Package `1.5.0` | Repository validator checks all seven frontmatter blocks, host metadata, supporting files, and deterministic ZIP contents | Passed |
| Python examples | Python `3.12.0` | General sidecar and two-contender checkpoint examples completed against production | Passed |
| Goose recipe | Goose CLI `1.44.0` | Official recipe validation and parameter rendering passed; live discovery and the checkpoint race completed against backend `0.6.2` | Passed |

The live checkpoint check admitted exactly one of two concurrent contenders,
recorded one synthetic domain action, reached `caller_verified`, and continued
to report `external_proof: false`.

## Prepared host packages

| Host | Package entry point | Release validation still required |
| --- | --- | --- |
| ChatGPT and Codex | `.codex-plugin/plugin.json` | Install the public `v1.5.0` package in a clean host session, confirm seven skills, connect the MCP server, and run both example prompts |
| Claude Code | `.claude-plugin/plugin.json` | Manifest validation passed; load the public tag in a clean host session and execute one skill plus MCP call |
| GitHub Copilot CLI | `plugin.json` | Isolated local installation passed; repeat from the immutable public tag and execute one skill plus MCP call |
| Gemini CLI | `gemini-extension.json` | Install the tagged GitHub release, restart Gemini CLI, and verify seven skills plus the Streamable HTTP server |
| Generic MCP clients | `.mcp.json` | Confirm the client supports remote Streamable HTTP and prompts the user before first use |

Prepared means that the artifact follows the host's documented layout; it is
not a claim that an unavailable client was tested. Record successful host
installs here with the exact host version and date.

Packaged connections use the privacy-safe source tag
`?source=github-plugin`, and the examples use their own stable source tags.
The untagged `https://liberated.site/mcp` endpoint is functionally equivalent.
Source tags measure aggregate activation only; they must not be combined with
prompt or argument logging.

Current packaging references:

- [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Claude Code plugins](https://code.claude.com/docs/en/plugins)
- [GitHub Copilot CLI plugins](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)
- [Gemini CLI extensions](https://geminicli.com/docs/extensions/reference/)

## Release acceptance

Before publishing a package:

1. run `python -B scripts/build_archive.py`;
2. run `python -B scripts/validate.py`;
3. run both examples from [`examples/`](../examples/);
4. test clean installation in every host marked compatible;
5. replace a prepared status with a passed status only after recording the
   exact host version and observed result; and
6. keep real USDC settlement disabled until its separate production gate is
   complete.

Do not send prompts, tool arguments, credentials, wallet addresses, or
provider records as compatibility telemetry.
