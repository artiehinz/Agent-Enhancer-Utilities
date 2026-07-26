from pathlib import Path
import os
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PATH = ROOT / "agent-enhancer-utilities-skills.zip"
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


def included_files(skill_root: Path) -> list[Path]:
    return sorted(
        path
        for path in skill_root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def portable_source_bytes(source_path: Path) -> bytes:
    data = source_path.read_bytes()
    if source_path.suffix.lower() in PORTABLE_TEXT_SUFFIXES:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


temporary = tempfile.NamedTemporaryFile(
    prefix=".agent-enhancer-utilities-skills-",
    suffix=".zip",
    dir=ROOT,
    delete=False,
)
temporary_path = Path(temporary.name)
temporary.close()

try:
    with zipfile.ZipFile(
        temporary_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for skill_name in SKILL_NAMES:
            skill_root = ROOT / skill_name
            for source_path in included_files(skill_root):
                relative = source_path.relative_to(skill_root).as_posix()
                archive_entry = zipfile.ZipInfo(
                    filename=f"skills/{skill_name}/{relative}",
                    date_time=(2020, 1, 1, 0, 0, 0),
                )
                archive_entry.compress_type = zipfile.ZIP_DEFLATED
                archive_entry.create_system = 3
                archive_entry.external_attr = 0o100644 << 16
                archive.writestr(
                    archive_entry,
                    portable_source_bytes(source_path),
                    compresslevel=9,
                )
    os.replace(temporary_path, ARCHIVE_PATH)
finally:
    temporary_path.unlink(missing_ok=True)

print(f"built {ARCHIVE_PATH.name} with {len(SKILL_NAMES)} skills")
