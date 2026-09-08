# SPARQ candidate release-readiness handoff

Owner: Codex. Joey asked to keep executing. Baseline was clean `53470702d32ace95fdf02f340f2012b34d8686bf`, branch `codex/athlete-home-first-value`, origin `joeygrant55/GMTM-Agent-SDK`. Repo AGENTS, current state and Control Tower leadership/operating contract/registry were read; no repo CLAUDE was present. Existing checkout and ownership lanes were preserved. This work follows the [completion contract](../../docs/state/candidate-release-readiness-contract-2026-09-08.md).

## Changes

- `backend/profile_api.py`: both shared connectors use `connect_timeout=5, read_timeout=10, write_timeout=10`, matching combine connectors. Credentials, target defaults, SQL and auth/ownership behavior are unchanged. The new actual-driver tests cover connect, stalled handshake, query read/write and cleanup using synthetic sockets. Socket limits do not bound DNS, multiple addresses, total request time or server query execution.
- `frontend/app/connect/page.tsx`: removed the top-level default destructuring argument, which caused the generated Next production PageProps check to reject the function. Optional searchParams and route behavior remain intact.
- `frontend/next.config.js`: candidate-only `optimizeFonts:false` removes the production build's Google-font download dependency. Browser font stylesheets remain; default legacy configuration is unchanged. Policy tests cover both modes.
- New `frontend/tests/check-production-build.cjs`: allowlisted external production snapshot, real Next and Clerk packages, synthetic settings, denied external service/environment access, actual build/start, six signed-out HTTP smoke assertions, source/manifests/runtime/cleanup receipts. No auth alias or product fixture escape hatch.
- Separate `Dockerfile.candidate` and companion ignore file, eight direct requirements and 26 exact dependency constraints, fixed `start_candidate.py`, deterministic allowlisted `package_candidate.py` and packaging regressions. Twelve reachable candidate modules plus launcher/dependency/Docker files form exactly 17 archive members. No main entry, secrets, test fixtures or schema tool is packaged. The launcher strips `UVICORN_*`, fixes one worker/asyncio/h11/lifespan and logging/proxy options, validates PORT and uses execve. The image source declares a non-root user; actual image execution is unverified.
- Candidate runbook, backend test README, current-state and commit/release plan updated; new [release packet](../../docs/state/candidate-release-packet-2026-09-08.md) records exact context, config and remaining gates. Current `agents/__init__.py` exists; older missing-Docker-input notes were corrected without changing legacy manifests.

## Verification and receipts

All artifact paths below are siblings of this checkout under `work/`; no generated artifact is staged.

| Artifact folder | Evidence |
| --- | --- |
| `sparq-profile-timeouts-2026-09-08/` | Eight actual PyMySQL regression failures at baseline and eight passes after timeout keywords; source hashes; AST comparison confirms no other executable connector change |
| `sparq-candidate-dependencies-2026-09-08/` | Installed dependency metadata: 26 distributions, 37 edges, Linux x86_64/aarch64 markers, no version conflicts/missing entries; not a resolver/install/image result |
| `sparq-production-build-2026-09-08-run1/` | Retained failure: generated Next PageProps validation, plus a denied font optimization request; no app input mutation or server start |
| `sparq-production-build-2026-09-08-run2/` | Actual successful build/start, 24 static pages, six route checks, real Clerk/no aliases; 121 source hashes, six generated manifest hashes, build/server groups exited and port closed; 175 account and 68 policy checks |
| `sparq-release-readiness-2026-09-08/` | Final 17-file tar + manifest, root verification/source hashes and post-run harness amendment, final local commit receipt |

Root ran the full backend suite with `/Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python -m pytest -q backend/tests`: **605 passed, one upstream Starlette/AnyIO deprecation warning, 70.81 seconds**. No service calls or live allowances were used. Focused packaging checks passed **19** before that full run. Python is 3.13.7; Next 14.2.35, React 18.3.1, Clerk 6.37.1 and Node 24.19.0 are recorded in the production runtime receipt. These are installed-environment results, not fresh dependency-install proof.

Independent review identified and resolved a typo in the first extracted-source test (initial focused run: 16 pass/1 fail), dangling output/manifest symlinks, inherited Uvicorn CLI environment options, and the Docker-ignore descendant rule. Tests now cover all these cases. Extracted-source startup records zero connect/DNS/DB/provider/dotenv/thread attempts and no lifespan create_task dispatch. This is application-level instrumentation, not OS/network isolation proof.

After the successful production run, review recommended rejecting snapshot-input mutation rather than only recording it. Root added that one failure predicate and ran Node syntax checking. The run2 receipt already records zero mutations; original evidence/harness is retained. The amendment is separately hashed, and all production application inputs still match the successful build. No repeat build was needed for this harness-only stricter acceptance predicate.

Independent final reviews approve packaging source/launcher/closure and the stated production compile plus signed-out smoke claims. All 121 frontend source/snapshot hashes and six generated manifest hashes were independently checked; no listener remains. Root verified application diffs, test output, source package hashes and staged scope before the local commit.

## Remaining boundaries and next action

No usable local container engine was available; no daemon was started, package downloaded or image built. The Docker source uses the tested Python family but requires a resolved immutable image digest and real Linux install/runtime verification. The retained frontend production build uses nonexistent synthetic service settings and cannot be deployed. Real Clerk/JWKS, exact live schema/ownership, provider delivery and actual GMTM save/return remain distinct acceptance gates.

The release packet makes the remaining work concrete: verify chosen-platform clean installs/image, run a newly scoped real athlete acceptance, then review exact paired SPARQ targets/artifacts and rollback before Joey's explicit deployment decision. Model limits are per process and reset across process restarts; no durable quota is claimed. Previous live test budgets remain exhausted. No schema apply, account/password change, production data operation, RDS/IAM/API action, Fable release or deletion instruction, external message, push or deployment occurred here.

Changes are intended for one reviewed local checkpoint. Exact final commit, parent, staged hashes and clean-status result belong in `sparq-release-readiness-2026-09-08/commit-receipt.json`, written after the commit. Historic docs may contain internal operational/portfolio context and must be reviewed before any future branch sharing. Fable and Audit/portfolio checkouts remain under their existing owners.
