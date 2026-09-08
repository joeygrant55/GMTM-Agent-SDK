# Safe app startup and database cleanup guidance

September 7, 2026 Eastern. Joey asked to continue product work and for an opinion on `family-test` and `pre-prod` deletion. Codex implemented the first bounded [safe-composition package](../../docs/state/safe-app-composition-contract-2026-09-07.md), with independent schema implementation and source/test review. Infrastructure execution remains Fable's lane; no deletion or release instruction was sent.

## Product outcome and verification

The real `main:app` and its lazy enrichment worker no longer implicitly load dotenv files or attempt schema preparation. Removed the three eager route-module initializers; their eleven CREATE statements and three non-conversation ADD COLUMN operations now live in an explicit, default-dry-run Agent preparation command. Required existing conversation prerequisites and incompatible unique Clerk indexes fail clearly before DDL. Nothing initializes or repairs a live database automatically. See the [operator guide](../../docs/state/agent-schema-preparation-2026-09-07.md).

All **481 offline backend tests pass**, including 55 preparation tests and three fresh-process app tests with installed application dependencies. The only warning is an upstream Starlette/AnyIO deprecated alias. Import, the actual composed lifespan, registered routes and authentication/ownership rejection are tested under recording external-access blockers. Local synthetic RS256/JWKS and Agent interfaces exercise real authentication code; they do not establish real Clerk or database acceptance. No model, database, network or email service was contacted.

The pre-change app successfully imported while attempting **nine dotenv loads and three DB connections**; database errors were swallowed. The final startup probe rejects the saved original source. Corrected composition records zero attempted external work or application background starts. The full suite ran with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1` and the installed Python 3.13 environment at `/Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python`.

Independent review and static verification confirm all remaining application AST nodes across seven changed modules match their frozen pre-package versions after excluding only docstrings, dotenv import/calls and the removed schema helpers/calls. Request handlers, authentication, prompts and routes are unchanged. All 14 retained DDL statements match the original definitions and order after whitespace normalization. All 42 tested backend Python hashes still match. Of 147 captured backend/frontend files, nine changed and 138 remain unchanged; no frontend file changed in this package.

Receipts are in [`work/sparq-safe-startup-2026-09-07`](../../../sparq-safe-startup-2026-09-07): `source-before.json`, `before/`, `import-baseline.json`, `original-app-regression.json`, `backend-suite.json`, `backend-suite.txt`, `verification.json`, `incremental-existing-files.patch` and `git-status.txt`. These receipts describe the current package; they do not overwrite older live acceptance or budget receipts.

## Database opinion

The [cleanup recommendation](../../docs/state/database-cleanup-recommendation-2026-09-07.md) supports `family-test` deletion first once its source snapshot remains available and no newer work depends on it. Its 14-check real-database test and fixture cleanup are complete. It contains restored production data, not merely synthetic fixtures. Preserve the existing source snapshot and external test artifacts; another snapshot is unnecessary if the instance contains no unique work.

Delete `pre-prod` after the retained final snapshot and current consumer configuration are checked, including an authorized meaningful GMTM-backed read. Fable's September 6 receipt records the final snapshot available; the approximate stopped time places the seven-day restart around Sunday September 13 at 12:20 p.m. Eastern. Confirm actual state/time before scheduling; Saturday is a conservative target. Current health 200 or an unsuccessful database login is not sufficient consumer evidence.

Fable's local deployment receipt `~/Desktop/gmtm-code-research/deploy-73-20260908T024032Z.md` records PR 73 merged at `93c18b14`, exact reviewed-function hashes, successful PM2 reloads on staging and both production hosts, and stable follow-up health/workers around 03:14 UTC September 8. Codex read that receipt, not fresh host/AWS state. The authenticated distinguishing probe is still absent. This supersedes earlier pre-deploy status pointers without claiming behavioral coverage the receipt lacks.

## Uncommitted scope and next action

Branch remains `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`. Existing dirty work is preserved. No commit, push or SPARQ deployment occurred.

Changed existing files for this package:

- `backend/main.py`, `agent_api.py`, `profile_api.py`, `artifacts_api.py`, `claims_api.py`, `reports_api.py`, `enrichment_worker.py`: remove implicit dotenv/schema work; update applicable comments.
- `backend/tests/conftest.py`, `backend/tests/README.md`, root `README.md`: explicit configuration/setup and verification scope.
- `docs/state/current-state.md`, `docs/state/adult-candidate-next-package-2026-09-07.md`: status and next package.

New files:

- `backend/prepare_agent_schema.py`, `backend/tests/test_prepare_agent_schema.py`, `backend/tests/test_app_startup.py`.
- `docs/state/safe-app-composition-contract-2026-09-07.md`, `docs/state/agent-schema-preparation-2026-09-07.md`, `docs/state/database-cleanup-recommendation-2026-09-07.md`, this handoff.

Next bounded product work: separate successful combine claim/workspace creation from automatic college matching, then enforce explicit isolated candidate configuration and supported frontend/backend routes. Safe backend composition does not make every legacy request safe to exercise. The frontend's live-backend fallback, broader workspace API calls, missing Docker `agents/` source path, actual schema compatibility, current-source live identity acceptance, real saved-submission return/refresh and guardian/organizer acceptance remain open. No existing live-read/model allowance was reset or used; no new service/server was left running.
