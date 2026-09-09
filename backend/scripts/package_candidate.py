"""Create an explicit source-only Docker build context. Does not build or deploy.

An allowlist is read directly; ignored/secret/unrelated directories are never
walked. The tar and manifest are exclusive outputs outside the checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile

SOURCES = (
    "Dockerfile.candidate", "Dockerfile.candidate.dockerignore",
    "backend/requirements-candidate.txt", "backend/constraints-candidate.txt",
    "backend/auth.py", "backend/candidate_app.py", "backend/claims_api.py",
    "backend/combine_api.py", "backend/combine_context.py", "backend/combine_help_api.py",
    "backend/combine_model.py", "backend/combine_requirements.py", "backend/combine_results.py",
    "backend/model_usage.py", "backend/profile_api.py", "backend/workspace_bootstrap.py",
    "backend/start_candidate.py",
)


def package(root: Path, output: Path) -> dict:
    return _package_sources(root, output, sources=SOURCES, kind="candidate_source_context")


def _package_sources(root: Path, output: Path, *, sources: tuple[str, ...], kind: str) -> dict:
    """Shared tar writer; only fixed, separately selected entry modules call it."""
    root = root.resolve(strict=True)
    if not output.is_absolute() or output.suffix != ".tar":
        raise ValueError("Use an absolute new .tar path outside the checkout")
    if output.is_symlink() or output.with_suffix(".manifest.json").is_symlink():
        raise ValueError("Package outputs must be new regular files, never symlinks")
    output = output.resolve()
    manifest = output.with_suffix(".manifest.json")
    if output.is_relative_to(root) or output.exists() or manifest.exists() or manifest.is_symlink():
        raise ValueError("Package outputs must be new and outside the checkout")
    if not output.parent.is_dir():
        raise ValueError("Create the artifact directory before packaging")
    payloads = {}
    for name in sources:
        source = root / name
        if any(part.is_symlink() for part in (source, *source.parents) if part != root.parent):
            raise ValueError("Candidate source paths cannot be symlinks")
        if not source.resolve(strict=True).is_relative_to(root) or not stat.S_ISREG(source.lstat().st_mode):
            raise ValueError("Candidate source must be a regular file inside the checkout")
        payloads[name] = source.read_bytes()
    report = {
        "kind": kind, "built": False, "deployed": False,
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)} for name, data in payloads.items()},
        "limits": "Source packaging only; no container engine, Linux installation or image digest has been verified.",
    }
    # Preflight every file before creating either output. Never overwrite receipts.
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, data in payloads.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o644
                member.mtime = 0
                archive.addfile(member, io.BytesIO(data))
    report["archive_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    with manifest.open("x") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = package(Path(__file__).resolve().parents[2], args.output)
    print(json.dumps({"files": len(report["files"]), "archive_sha256": report["archive_sha256"], "built": False}))


if __name__ == "__main__":
    main()
