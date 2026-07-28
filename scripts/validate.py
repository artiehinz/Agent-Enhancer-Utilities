from pathlib import Path
import json
import re
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = "1.6.0"
SKILL_NAMES = (
    "coordinate-parallel-agents",
    "test-http-failure-paths",
    "debug-x402-integrations",
    "review-mcp-tool-contracts",
    "guard-x402-retries",
    "measure-webhook-delivery",
    "guard-external-plugin-workflows",
)
PORTABLE_TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".py",
    ".yaml",
    ".yml",
}


def portable_source_bytes(source_path: Path) -> bytes:
    data = source_path.read_bytes()
    if source_path.suffix.lower() in PORTABLE_TEXT_SUFFIXES:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


readme = (ROOT / "README.md").read_text(encoding="utf-8")
for name in SKILL_NAMES:
    legacy_folder = ROOT / name
    if legacy_folder.is_dir() and any(
        path.is_file() for path in legacy_folder.rglob("*")
    ):
        fail(f"{name}: legacy root skill directory must not coexist with skills/")
    folder = ROOT / "skills" / name
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

manifest_paths = (
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    "plugin.json",
    "gemini-extension.json",
)
manifests = {}
for relative_path in manifest_paths:
    path = ROOT / relative_path
    if not path.is_file():
        fail(f"release package: missing {relative_path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifests[relative_path] = manifest
    if manifest.get("name") != "agent-enhancer-utilities":
        fail(f"{relative_path}: plugin name is stale")
    if manifest.get("version") != PACKAGE_VERSION:
        fail(f"{relative_path}: version must be {PACKAGE_VERSION}")

for relative_path in (
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    "plugin.json",
):
    manifest = manifests[relative_path]
    if str(manifest.get("skills", "")).rstrip("/") not in {
        "./skills",
        "skills",
    }:
        fail(f"{relative_path}: skills must resolve to the canonical skills/")
    if str(manifest.get("mcpServers", "")).lstrip("./") != ".mcp.json".lstrip("./"):
        fail(f"{relative_path}: MCP companion path is stale")

mcp_config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
server_config = mcp_config.get("mcpServers", {}).get("agent-enhancer-utilities", {})
if server_config != {
    "type": "http",
    "url": "https://liberated.site/mcp?source=github-plugin&profile=core",
}:
    fail(".mcp.json: packaged remote server definition drifted")

gemini_server = (
    manifests["gemini-extension.json"]
    .get("mcpServers", {})
    .get("agent-enhancer-utilities", {})
)
if gemini_server != {
    "httpUrl": "https://liberated.site/mcp?source=github-plugin&profile=core"
}:
    fail("gemini-extension.json: Streamable HTTP definition drifted")

codex_interface = manifests[".codex-plugin/plugin.json"].get("interface", {})
for field in (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "websiteURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
):
    if not codex_interface.get(field):
        fail(f".codex-plugin/plugin.json: missing interface.{field}")
for asset_field in ("composerIcon", "logo"):
    asset_path = str(codex_interface.get(asset_field, "")).removeprefix("./")
    if not asset_path or not (ROOT / asset_path).is_file():
        fail(f".codex-plugin/plugin.json: missing {asset_field} asset")

for relative_path in (
    "docs/ARCHITECTURE.md",
    "docs/COMPATIBILITY.md",
    "examples/README.md",
    "examples/reliability-sidecar/README.md",
    "examples/reliability-sidecar/run.py",
    "examples/multi-agent-checkpoint/README.md",
    "examples/multi-agent-checkpoint/run.py",
    "examples/goose/README.md",
    "examples/goose/agent-enhancer-reliability-sidecar.yaml",
    "examples/sidecar-benchmark/README.md",
    "examples/sidecar-benchmark/preregistered-plan.json",
    "examples/sidecar-benchmark/adapters.py",
    "examples/sidecar-benchmark/benchmark.py",
    "examples/sidecar-benchmark/run.py",
    "examples/sidecar-benchmark/test_benchmark.py",
    "examples/sidecar-benchmark/results/latest.json",
    "examples/sidecar-agent-benchmark/README.md",
    "examples/sidecar-agent-benchmark/preregistered-plan.json",
    "examples/sidecar-agent-benchmark/final-response.schema.json",
    "examples/sidecar-agent-benchmark/fixture_cli.py",
    "examples/sidecar-agent-benchmark/evaluator.py",
    "examples/sidecar-agent-benchmark/benchmark.py",
    "examples/sidecar-agent-benchmark/run.py",
    "examples/sidecar-agent-benchmark/test_benchmark.py",
    "examples/sidecar-agent-benchmark/results/validation-0.6.4.json",
    "examples/sidecar-agent-benchmark/results/validation-0.6.5-core.json",
    "docs/RELIABILITY_SIDECAR_CONTRACT_V1.md",
    "docs/schemas/reliability-sidecar-contract-v1.schema.json",
    "docs/OPEN_SOURCE_INTEGRATION_PLAN.md",
):
    if not (ROOT / relative_path).is_file():
        fail(f"release package: missing {relative_path}")

for relative_path in (
    "examples/common/mcp_client.py",
    "examples/reliability-sidecar/run.py",
    "examples/multi-agent-checkpoint/run.py",
    "examples/sidecar-benchmark/adapters.py",
    "examples/sidecar-benchmark/benchmark.py",
    "examples/sidecar-benchmark/run.py",
    "examples/sidecar-benchmark/test_benchmark.py",
    "examples/sidecar-agent-benchmark/fixture_cli.py",
    "examples/sidecar-agent-benchmark/evaluator.py",
    "examples/sidecar-agent-benchmark/benchmark.py",
    "examples/sidecar-agent-benchmark/run.py",
    "examples/sidecar-agent-benchmark/test_benchmark.py",
    "scripts/smoke_live_mcp.py",
):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    compile(source, relative_path, "exec")

weekly_workflow = ROOT / ".github" / "workflows" / "weekly-owned-surface-smoke.yml"
if not weekly_workflow.is_file():
    fail("release package: missing weekly owned-surface smoke workflow")
weekly_text = weekly_workflow.read_text(encoding="utf-8")
if (
    "scripts/smoke_live_mcp.py" not in weekly_text
    or "examples/reliability-sidecar/run.py" not in weekly_text
    or "examples/multi-agent-checkpoint/run.py" not in weekly_text
    or "issues: write" not in weekly_text
):
    fail("weekly owned-surface smoke workflow is incomplete")
if any(
    third_party in weekly_text
    for third_party in (
        "docker/mcp-registry",
        "punkpeye/awesome-mcp-servers",
        "punkpeye/awesome-mcp-devtools",
    )
):
    fail("weekly workflow must never mutate third-party repositories")

goose_recipe = (
    ROOT / "examples" / "goose" / "agent-enhancer-reliability-sidecar.yaml"
).read_text(encoding="utf-8")
for required_fragment in (
    'version: "1.0.0"',
    "requirement: user_prompt",
    "type: streamable_http",
    'uri: "https://liberated.site/mcp?source=goose-recipe&profile=core"',
    "`lab.search_tools`",
    "`lab.describe_tool`",
    "`lab.invoke_tool`",
    "`workflow-guard-planner`",
    "`workflow-checkpoint`",
    "`external_proof: false`",
):
    if required_fragment not in goose_recipe:
        fail(f"goose recipe: missing {required_fragment}")

sidecar_skill = (
    ROOT / "skills" / "guard-external-plugin-workflows" / "SKILL.md"
).read_text(encoding="utf-8")
if "[TODO:" in sidecar_skill:
    fail("guard-external-plugin-workflows: unresolved TODO")

for relative_path in (
    "skills/guard-external-plugin-workflows/references/reliability-contract.md",
    "skills/guard-external-plugin-workflows/references/recipes.md",
    "docs/WORKFLOW_GUARD_PLANNER.md",
    "docs/guard-external-plugin-workflows-evals.json",
    "docs/schemas/workflow-guard-planner.input.schema.json",
    "docs/schemas/workflow-guard-planner.output.schema.json",
    "docs/SIDECAR_RECIPE_TESTS.md",
    "docs/OPAQUE_WORKFLOW_CHECKPOINTS.md",
    "docs/SHARED_CIRCUIT_BREAKER.md",
):
    if not (ROOT / relative_path).is_file():
        fail(f"missing sidecar artifact: {relative_path}")

evals = json.loads(
    (ROOT / "docs" / "guard-external-plugin-workflows-evals.json").read_text(
        encoding="utf-8"
    )
)
if evals.get("schema_version") != 1:
    fail("sidecar evals: unsupported schema_version")
if evals.get("skill") != "guard-external-plugin-workflows":
    fail("sidecar evals: skill name mismatch")
positive_cases = evals.get("positive_cases", [])
negative_cases = evals.get("negative_cases", [])
if len(positive_cases) < 6 or len(negative_cases) < 4:
    fail("sidecar evals: insufficient positive or negative coverage")

ids = [case.get("id") for case in positive_cases + negative_cases]
if None in ids or len(ids) != len(set(ids)):
    fail("sidecar evals: case ids must be present and unique")

guarantees = {
    "provider-idempotent",
    "duplicate-resistant",
    "concurrency-safe",
    "rate/concurrency-bounded",
    "best-effort",
}
for case in positive_cases:
    if case.get("expected_guarantee") not in guarantees:
        fail(f"sidecar evals: invalid guarantee in {case.get('id')}")
    if not case.get("required_concepts"):
        fail(f"sidecar evals: missing required concepts in {case.get('id')}")
    if not case.get("forbidden_claims"):
        fail(f"sidecar evals: missing forbidden claims in {case.get('id')}")
    for profile in case.get("expected_additional_profiles", []):
        if profile not in {
            "create-once",
            "update-safely",
            "send-at-most-once",
            "refresh-if-stale",
            "fan-out-bounded",
            "scheduled-run",
        }:
            fail(f"sidecar evals: invalid additional profile in {case.get('id')}")

for schema_name in (
    "workflow-guard-planner.input.schema.json",
    "workflow-guard-planner.output.schema.json",
):
    schema = json.loads(
        (ROOT / "docs" / "schemas" / schema_name).read_text(encoding="utf-8")
    )
    if schema.get("type") != "object":
        fail(f"{schema_name}: root must be an object schema")
    if schema.get("additionalProperties") is not False:
        fail(f"{schema_name}: root schema must be closed")
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    if not required or not set(required).issubset(properties):
        fail(f"{schema_name}: required properties are missing definitions")

planner_tests = subprocess.run(
    [
        sys.executable,
        "-B",
        str(
            ROOT
            / "skills"
            / "guard-external-plugin-workflows"
            / "scripts"
            / "test_plan_workflow.py"
        ),
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
if planner_tests.returncode:
    fail(
        "workflow guard planner tests failed:\n"
        + planner_tests.stdout
        + planner_tests.stderr
    )

benchmark_tests = subprocess.run(
    [
        sys.executable,
        "-B",
        str(
            ROOT
            / "examples"
            / "sidecar-benchmark"
            / "test_benchmark.py"
        ),
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
if benchmark_tests.returncode:
    fail(
        "reliability sidecar benchmark tests failed:\n"
        + benchmark_tests.stdout
        + benchmark_tests.stderr
    )

agent_benchmark_tests = subprocess.run(
    [
        sys.executable,
        "-B",
        str(
            ROOT
            / "examples"
            / "sidecar-agent-benchmark"
            / "test_benchmark.py"
        ),
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
if agent_benchmark_tests.returncode:
    fail(
        "metered agent benchmark tests failed:\n"
        + agent_benchmark_tests.stdout
        + agent_benchmark_tests.stderr
    )

benchmark_result = json.loads(
    (
        ROOT
        / "examples"
        / "sidecar-benchmark"
        / "results"
        / "latest.json"
    ).read_text(encoding="utf-8")
)
if (
    benchmark_result.get("evidence_class")
    != "deterministic-protocol-fixture"
    or benchmark_result.get("evaluation", {}).get("status") != "passed"
    or len(benchmark_result.get("published", {}).get("rows", [])) != 200
    or len(benchmark_result.get("published", {}).get("aggregates", [])) != 10
):
    fail("reliability sidecar benchmark evidence is incomplete")
if any(
    row[13] is not None or row[14] is not None or row[15] is not None
    for row in benchmark_result["published"]["rows"]
):
    fail("model usage must remain unavailable in the deterministic benchmark")

agent_validation = json.loads(
    (
        ROOT
        / "examples"
        / "sidecar-agent-benchmark"
        / "results"
        / "validation-0.6.4.json"
    ).read_text(encoding="utf-8")
)
if (
    agent_validation.get("evidence_class")
    != "metered-agent-host-validation-summary"
    or agent_validation.get("evaluation", {}).get("status") != "failed"
    or agent_validation.get("valid_rows") != 50
    or agent_validation.get("evaluation", {})
    .get("observed", {})
    .get("harm_reduction_percent")
    != 0.0
):
    fail("metered agent validation summary is incomplete or misleading")

core_agent_validation = json.loads(
    (
        ROOT
        / "examples"
        / "sidecar-agent-benchmark"
        / "results"
        / "validation-0.6.5-core.json"
    ).read_text(encoding="utf-8")
)
core_observed = core_agent_validation.get("evaluation", {}).get(
    "observed",
    {},
)
if (
    core_agent_validation.get("evidence_class")
    != "metered-agent-host-validation-summary"
    or core_agent_validation.get("evaluation", {}).get("status")
    != "failed"
    or core_agent_validation.get("valid_rows") != 50
    or core_agent_validation.get("setup_and_infrastructure_exclusions")
    != 0
    or core_observed.get("harm_reduction_percent") != 100.0
    or core_observed.get("low_risk_median_input_token_overhead_percent")
    != 10.779
):
    fail("core-profile validation summary is incomplete or misleading")

submission = json.loads(
    (ROOT / "chatgpt-app-submission.json").read_text(encoding="utf-8")
)
if (
    submission.get("$schema")
    != "https://developers.openai.com/apps-sdk/schemas/chatgpt-app-submission.v1.json"
):
    fail("chatgpt app submission: canonical schema URL is stale")
if submission.get("schema_version") != 1:
    fail("chatgpt app submission: schema_version must be 1")
if submission.get("portal_submission", {}).get("version") != PACKAGE_VERSION:
    fail("chatgpt app submission: portal package version is stale")
if len(submission.get("tools", {})) != 37:
    fail("chatgpt app submission: expected 37 release-candidate direct tools")
for required_tool in (
    "workflow_guard_planner",
    "workflow_checkpoint_claim",
    "workflow_checkpoint_transition",
    "workflow_checkpoint_status",
    "workflow_checkpoint_abandon",
):
    if required_tool not in submission["tools"]:
        fail(f"chatgpt app submission: missing {required_tool}")
app_info = submission.get("app_info", {})
if not str(app_info.get("display_name", "")).strip():
    fail("chatgpt app submission: display_name is required")
subtitle = submission.get("app_info", {}).get("subtitle", "")
if not subtitle.strip() or len(subtitle) > 30:
    fail("chatgpt app submission: subtitle must contain 1-30 characters")
description = submission.get("app_info", {}).get("description", "")
if (
    "reliability sidecar" not in description
    or "does not automatically intercept other plugins" not in description
):
    fail("chatgpt app submission: sidecar boundary is missing")
if len(description) > 4000:
    fail("chatgpt app submission: description exceeds 4000 characters")
if app_info.get("category") not in {
    "BUSINESS",
    "COLLABORATION",
    "DESIGN",
    "DEVELOPER_TOOLS",
    "EDUCATION",
    "ENTERTAINMENT",
    "FINANCE",
    "FOOD",
    "LIFESTYLE",
    "NEWS",
    "PRODUCTIVITY",
    "SHOPPING",
    "TRAVEL",
}:
    fail("chatgpt app submission: invalid category")

for tool_name, tool in submission["tools"].items():
    annotations = tool.get("annotations", {})
    for field in ("readOnlyHint", "openWorldHint", "destructiveHint"):
        if not isinstance(annotations.get(field), bool):
            fail(f"chatgpt app submission: {tool_name} missing boolean {field}")
    justifications = tool.get("justifications", {})
    for field in (
        "read_only_justification",
        "open_world_justification",
        "destructive_justification",
    ):
        if not str(justifications.get(field, "")).strip():
            fail(f"chatgpt app submission: {tool_name} missing {field}")

positive_submission_cases = submission.get("test_cases", [])
negative_submission_cases = submission.get("negative_test_cases", [])
if len(positive_submission_cases) != 5 or len(negative_submission_cases) != 3:
    fail(
        "chatgpt app submission: directory review requires exactly "
        "5 positive and 3 negative test cases"
    )
for case in positive_submission_cases:
    if not str(case.get("description", "")).strip():
        fail("chatgpt app submission: positive case missing description")
    if not str(case.get("user_prompt", "")).strip():
        fail("chatgpt app submission: positive case missing user_prompt")
    if not str(case.get("tools_triggered", "")).strip():
        fail("chatgpt app submission: positive case missing tools_triggered")
    for tool_name in case["tools_triggered"].split(", "):
        if tool_name not in submission["tools"]:
            fail(
                "chatgpt app submission: positive case references unknown tool "
                + tool_name
            )
for case in negative_submission_cases:
    if not str(case.get("description", "")).strip():
        fail("chatgpt app submission: negative case missing description")
    if not str(case.get("user_prompt", "")).strip():
        fail("chatgpt app submission: negative case missing user_prompt")

if not any(
    case.get("tools_triggered")
    == "swarm_semaphore_acquire, swarm_rate_gate_consume"
    for case in positive_submission_cases
):
    fail("chatgpt app submission: missing cross-plugin sidecar test")
if not any(
    case.get("user_prompt") == "Create this one Notion note for me."
    and case.get("tools_triggered") is None
    for case in negative_submission_cases
):
    fail("chatgpt app submission: missing one-time plugin abstention test")

archive_path = ROOT / "agent-enhancer-utilities-skills.zip"
with zipfile.ZipFile(archive_path) as archive:
    archive_entries = set(archive.namelist())
for skill_name in SKILL_NAMES:
    if f"skills/{skill_name}/SKILL.md" not in archive_entries:
        fail(f"skills archive: missing {skill_name}")
for required_entry in (
    "skills/guard-external-plugin-workflows/agents/openai.yaml",
    "skills/guard-external-plugin-workflows/references/reliability-contract.md",
    "skills/guard-external-plugin-workflows/references/recipes.md",
    "skills/guard-external-plugin-workflows/scripts/plan_workflow.py",
    "skills/guard-external-plugin-workflows/scripts/test_plan_workflow.py",
):
    if required_entry not in archive_entries:
        fail(f"skills archive: missing {required_entry}")
if any("__pycache__" in entry or entry.endswith(".pyc") for entry in archive_entries):
    fail("skills archive: generated Python cache files are not allowed")
with zipfile.ZipFile(archive_path) as archive:
    for skill_name in SKILL_NAMES:
        skill_root = ROOT / "skills" / skill_name
        for source_path in skill_root.rglob("*"):
            if not source_path.is_file():
                continue
            relative = source_path.relative_to(skill_root).as_posix()
            archive_entry = f"skills/{skill_name}/{relative}"
            if archive_entry not in archive_entries:
                fail(f"skills archive: missing source file {archive_entry}")
            if archive.read(archive_entry) != portable_source_bytes(source_path):
                fail(f"skills archive: stale source file {archive_entry}")

print(f"validated {len(SKILL_NAMES)} skills")
