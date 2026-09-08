# Offline backend tests

Use an isolated Python environment with backend/requirements-test.txt installed. From the repository root:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest backend/tests -q -p no:cacheprovider
```

conftest.py installs guards before test collection: dotenv does not load local credentials; real database and model clients fail closed; outbound DNS and TCP connections are blocked. Each behavior test supplies its own fake service interfaces. A lightweight runner without PyMySQL or Anthropic uses fail-closed import shims, not implementations of those services.

The suite covers token validity and ownership conflicts, rollback/interleaving with transactional fakes, legacy linking, conversation ownership and typed model data access, and pure combine result helpers. It does not establish live MySQL locking/schema behavior, real Clerk/Anthropic integration, provider delivery or production readiness.

`test_app_startup.py` additionally exercises fresh-process composition of the actual `main:app` with installed application dependencies, recording and rejecting attempted DB, dotenv, model, network and background work. It then exercises lifespan and actual registered endpoints under synthetic interfaces. This is backend composition coverage, not a running Next/frontend integration or container-build test. `test_prepare_agent_schema.py` covers explicit preparation using fake database interfaces; no DDL is executed against MySQL.

`test_combine_requirements.py` also verifies the authenticated current-combine endpoint and deterministic field-presence projection using the September 6 public junior/adult configurations. It covers public requirements before linking, unique owner scope, zero/partial submissions, video-only and highlight activities, both shuttle directions, exact saved form keys, latest visible attempts, malformed source data and failures. The fake database checks query structure and returns synthetic records; it does not execute MySQL or establish deployed schema/index performance.

Never use production-connected app startup as a substitute for these checks. Database-backed concurrency/schema acceptance belongs in an explicitly isolated integration environment.

## Synthetic family handoff

Run `backend/tests/test_family_handoff.py` with the same offline command and guards. The fixture uses invented parent, child, sibling and same-name duplicate profiles. Actual claim/connect/recovery/combine/help handlers share the fake mapping/submission state. Cases verify parent links are not repurposed, independently linked athletes receive only their own progress, unknown links remain unknown, and malformed/case-colliding/conflicting ownership stops before GMTM or model access. The child Clerk identity and all transactions are fake; this does not create test accounts in Clerk/GMTM or implement guardian delegation.

The September 7 family rehearsal also executes pinned GMTM child-list/switch/removal source in an isolated Node VM with synthetic service interfaces. Its runner and unapplied core patch are local sibling artifacts referenced in the [family rehearsal handoff](../../.sammy/handoffs/2026-09-07-family-rehearsal-and-ownership-fix.md). They are not automatically included in pytest, shared to the core repo or suitable as live database/middleware proof.

## Combine onboarding and explicit research

`test_workspace_bootstrap.py` exercises the actual creation-only helper, identity projection, and registered claim/combine handlers. Recording fakes check zero research/provider/background dispatch during bootstrap, exact ownership, duplicate creation, preserved metrics, optional failure and safe retry. A mutable synthetic submission fixture changes the adult checklist from zero to one submitted activity while excluding junior/other-athlete records. No GMTM submission endpoint or real database is used.

`test_explicit_matching.py` checks that an owned explicit request with usable stored sport data constructs one worker, while missing/malformed sport or conflicting ownership dispatches none. The worker is a recording fake and never executes; stored sport text is not independently verified sport eligibility. Real transaction concurrency, participant sign-in, provider delivery and submission-return acceptance remain separate checks.
