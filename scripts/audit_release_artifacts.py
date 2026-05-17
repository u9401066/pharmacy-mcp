"""Audit built release artifacts for packaging hygiene."""

from __future__ import annotations

import argparse
import sys
import tarfile
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

FORBIDDEN_PARTS = {
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    "__pycache__",
    "dist",
    "htmlcov",
}

FORBIDDEN_PREFIXES = (
    ".asset-aware-mcp/",
    ".claude/",
    ".cline/",
    ".clinerules/",
    ".codex/",
    ".github/",
    "data/.uv-cache/",
    "data/exports/",
    "data/jobs/",
    "data/tables/",
    "scripts/hooks/",
)

REQUIRED_WHEEL_SUFFIXES = (
    "pharmacy_mcp/data/formulas/trusted_pk_ddi.json",
    "pharmacy_mcp/data/formulary.json",
    "pharmacy_mcp/data/renal_adjustments.json",
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_NAME = "pharmacy-mcp"
ARTIFACT_STEM = "pharmacy_mcp"


def main() -> int:
    """Run the artifact audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path, nargs="?", default=Path("dist"))
    parser.add_argument("--max-sdist-bytes", type=int, default=1_000_000)
    parser.add_argument("--max-wheel-bytes", type=int, default=500_000)
    args = parser.parse_args()

    expected_version = _expected_project_version()
    dist_dir = args.dist_dir
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    wheels = sorted(dist_dir.glob("*.whl"))
    errors: list[str] = []

    if len(sdists) != 1:
        errors.append(f"expected exactly one sdist, found {len(sdists)}")
    if len(wheels) != 1:
        errors.append(f"expected exactly one wheel, found {len(wheels)}")

    for sdist in sdists:
        expected_name = f"{ARTIFACT_STEM}-{expected_version}.tar.gz"
        if sdist.name != expected_name:
            errors.append(f"unexpected sdist name: {sdist.name}; expected {expected_name}")
        if sdist.stat().st_size > args.max_sdist_bytes:
            errors.append(f"sdist too large: {sdist} ({sdist.stat().st_size} bytes)")
        with tarfile.open(sdist) as archive:
            names = archive.getnames()
            metadata = _read_sdist_metadata(archive, names)
        errors.extend(_forbidden_name_errors(sdist.name, names, strip_root=True))
        errors.extend(_metadata_errors(sdist.name, metadata, expected_version))

    for wheel in wheels:
        expected_prefix = f"{ARTIFACT_STEM}-{expected_version}-"
        if not wheel.name.startswith(expected_prefix):
            errors.append(
                f"unexpected wheel name: {wheel.name}; expected prefix {expected_prefix}"
            )
        if wheel.stat().st_size > args.max_wheel_bytes:
            errors.append(f"wheel too large: {wheel} ({wheel.stat().st_size} bytes)")
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            metadata = _read_wheel_metadata(archive, names)
        errors.extend(_forbidden_name_errors(wheel.name, names, strip_root=False))
        errors.extend(_metadata_errors(wheel.name, metadata, expected_version))
        for suffix in REQUIRED_WHEEL_SUFFIXES:
            if not any(name.endswith(suffix) for name in names):
                errors.append(f"wheel missing required package data: {suffix}")

    if errors:
        for error in errors:
            print(f"artifact audit error: {error}", file=sys.stderr)
        return 1

    print("Release artifact audit passed")
    return 0


def _expected_project_version() -> str:
    """Read the package version from pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        data = tomllib.load(file)
    return str(data["project"]["version"])


def _read_sdist_metadata(
    archive: tarfile.TarFile,
    names: list[str],
) -> dict[str, str]:
    """Read package metadata from an sdist PKG-INFO file."""
    candidates = [name for name in names if name.endswith("/PKG-INFO")]
    if len(candidates) != 1:
        return {}
    member = archive.extractfile(candidates[0])
    if member is None:
        return {}
    message = Parser().parsestr(member.read().decode("utf-8"))
    return dict(message.items())


def _read_wheel_metadata(
    archive: zipfile.ZipFile,
    names: list[str],
) -> dict[str, str]:
    """Read package metadata from a wheel METADATA file."""
    candidates = [
        name for name in names if name.endswith(".dist-info/METADATA")
    ]
    if len(candidates) != 1:
        return {}
    message = Parser().parsestr(archive.read(candidates[0]).decode("utf-8"))
    return dict(message.items())


def _metadata_errors(
    artifact_name: str,
    metadata: dict[str, str],
    expected_version: str,
) -> list[str]:
    """Return package name/version metadata findings."""
    errors: list[str] = []
    if not metadata:
        return [f"{artifact_name} missing package metadata"]
    if metadata.get("Name") != PROJECT_NAME:
        errors.append(
            f"{artifact_name} metadata name mismatch: {metadata.get('Name')}"
        )
    if metadata.get("Version") != expected_version:
        errors.append(
            f"{artifact_name} metadata version mismatch: "
            f"{metadata.get('Version')} != {expected_version}"
        )
    return errors


def _forbidden_name_errors(
    artifact_name: str,
    names: list[str],
    *,
    strip_root: bool,
) -> list[str]:
    """Return forbidden path findings for an archive."""
    errors: list[str] = []
    for name in names:
        normalized = name.replace("\\", "/")
        if strip_root and "/" in normalized:
            normalized = normalized.split("/", 1)[1]
        parts = set(normalized.split("/"))
        if parts & FORBIDDEN_PARTS:
            errors.append(f"{artifact_name} contains forbidden path: {name}")
            continue
        if normalized.startswith(FORBIDDEN_PREFIXES):
            errors.append(f"{artifact_name} contains non-runtime asset: {name}")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
