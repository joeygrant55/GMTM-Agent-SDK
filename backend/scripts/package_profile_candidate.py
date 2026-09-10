"""Create the explicitly selected profile source context; never build or deploy.

The exact list includes the profile handler/import closure. Some combine modules
are shared imports; their routes are not mounted by profile_candidate_app:app.
No schema preparation command, legacy entry, tests or environment files ship.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .package_candidate import _package_sources
else:
    from package_candidate import _package_sources


SOURCES = (
    "Dockerfile.profile-candidate", "Dockerfile.profile-candidate.dockerignore",
    "backend/requirements-candidate.txt", "backend/constraints-candidate.txt",
    "backend/auth.py", "backend/candidate_app.py", "backend/claims_api.py",
    "backend/combine_api.py", "backend/combine_context.py", "backend/combine_help_api.py",
    "backend/combine_model.py", "backend/combine_requirements.py", "backend/combine_results.py",
    "backend/model_usage.py", "backend/profile_api.py", "backend/workspace_bootstrap.py",
    "backend/profile_candidate_app.py", "backend/athlete_evidence.py", "backend/athlete_materials.py",
    "backend/athlete_workspace.py", "backend/profile_debrief.py", "backend/profile_pathways.py",
    "backend/source_scope.py", "backend/start_profile_candidate.py",
    "backend/athlete_opportunities.py", "backend/opportunity_catalog.py", "backend/opportunity_engagement.py",
)


def package(root: Path, output: Path) -> dict:
    return _package_sources(root, output, sources=SOURCES, kind="profile_candidate_source_context")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = package(Path(__file__).resolve().parents[2], args.output)
    print(json.dumps({"files": len(report["files"]), "archive_sha256": report["archive_sha256"], "built": False}))


if __name__ == "__main__":
    main()
