from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAMES = (
    "coordinate-parallel-agents",
    "test-http-failure-paths",
    "debug-x402-integrations",
    "review-mcp-tool-contracts",
    "guard-x402-retries",
    "measure-webhook-delivery",
)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


readme = (ROOT / "README.md").read_text(encoding="utf-8")
for name in SKILL_NAMES:
    folder = ROOT / name
    skill_path = folder / "SKILL.md"
    metadata_path = folder / "agents" / "openai.yaml"
    if not skill_path.is_file():
        fail(f"{name}: missing SKILL.md")
    if not metadata_path.is_file():
        fail(f"{name}: missing agents/openai.yaml")

    skill = skill_path.read_text(encoding="utf-8")
    frontmatter = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", skill, re.S)
    if not frontmatter:
        fail(f"{name}: invalid YAML frontmatter")
    fields = dict(
        re.findall(
            r"^([a-z_]+):[ \t]*(.+)$",
            frontmatter.group(1),
            re.M,
        )
    )
    if set(fields) != {"name", "description"}:
        fail(f"{name}: frontmatter must contain only name and description")
    if fields["name"].strip() != name:
        fail(f"{name}: frontmatter name does not match its folder")
    if len(fields["description"].strip()) < 80:
        fail(f"{name}: description is too short to trigger reliably")
    if name not in readme:
        fail(f"{name}: README does not list the skill")

    metadata = metadata_path.read_text(encoding="utf-8")
    if 'value: "agent-enhancer-utilities"' not in metadata:
        fail(f"{name}: MCP dependency name is stale")
    if 'url: "https://liberated.site/mcp"' not in metadata:
        fail(f"{name}: MCP dependency URL is stale")

print(f"validated {len(SKILL_NAMES)} skills")
