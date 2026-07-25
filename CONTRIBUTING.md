# Contributing

Contributions should improve one concrete agent workflow without adding
credentials, private data, copied backend contracts, or speculative tool
instructions.

## Before opening a pull request

1. Keep each skill's folder name and frontmatter `name` identical.
2. Put trigger conditions in the frontmatter `description`.
3. Keep `SKILL.md` concise and use imperative instructions.
4. Use progressive MCP discovery: search, describe, then invoke.
5. Preserve bounded inputs, idempotency rules, abstention, privacy, and typed
   recovery behavior.
6. Update `agents/openai.yaml` when a skill's purpose or dependency changes.
7. For cross-plugin sidecar recipes, document the external capability
   assumptions, verification step, guarantee label, and residual risk. Never
   derive exactly-once external execution from a lock, stamp, lease, or baton.
8. Run:

   ```sh
   python scripts/validate.py
   ```

For a new workflow, open an issue first with the user job, expected service
modules, sensitive-data boundary, and a realistic success/failure example.

## Pull requests

Keep one logical change per pull request. Explain the user problem, the skill
behavior changed, and the validation performed. Do not include generated
marketing copy or unrelated files.
