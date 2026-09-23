# Profile pilot admission and catalog refresh — September 23, 2026

Owner: Codex in the existing September 4 SPARQ implementation lane. Checkout `work/sparq-agent-review`; branch `codex/athlete-home-first-value`; starting HEAD `159869c775fe51e0f4b4884bc6760f6009b2369d`; remote `joeygrant55/GMTM-Agent-SDK`. Current Control Tower role, operating contract, registry and repo instructions were read. Existing September 14 state/priority/handoff edits were preserved and are included in the local checkpoint. No unrelated writer or checkout changed.

## Completion contract and result

Deliver the bounded adult-pilot access milestone from September 14, refresh the existing opportunity collection from official evidence, independently review the integration, and verify it offline. This local implementation contract is complete; hosted acceptance and commercial validation are separate, unfinished work.

- `profile_admission.py`: pure configuration validation, bounded private schema-1 file, explicit reviewed adult self-owned attestation, exact subject/user/link-row/revision binding, validity interval and revocation. No admission is inferred from email or combine age category. Disabled mode only accepts canonical loopback UI origins; hosted origins require explicit admission. The file must be process-owned, mode 0600, regular, single-link and resolved without symlinks. Config/import does not provision accounts or database state.
- `candidate_app.py`: explicit profile-only admission boundary before handlers; gated claim preview/redemption blocked before their side effects; health/startup check the private policy without disclosing its contents. CORS preflight remains public. Request context resets in a finally block and configuration drift fails closed.
- `profile_owner.py` plus existing owner seams: evidence/materials/debrief/recovery resolve the full link row; workspace/opportunities/engagement recheck pinned ownership. PATCH rechecks current admission before commit and rolls back denial. Debrief checks before and after model work; measurement checks before emitting. Admission errors retain denied/unavailable status. In-flight work is bounded by these checks; this is not an atomic transaction across a filesystem policy and the database.
- Exact profile Docker/ignore/source-package closure includes both new modules. Original combine source set stays unchanged. Read-only source receipts include the new dependency files; the founder acceptance harness guards the new connection alias. No founder acceptance run or renewed save allowance occurred.
- Four continuing event/contact records freshly verified; ended USA Football Combine 2 stays excluded. Orlando review expires September 25 00:00 UTC; other renewed records September 30. See the source review note for dates, team entry, fees and uncertainty. No registration or eligibility guarantee.

Parallel bounded work: Parfit refreshed the catalog/research/tests; Pauli implemented and reviewed the admission policy/tests; Heisenberg prepared the paired release manifest and independently reviewed root integration. All are finished. Root owns integration and final verification.

## Verification and review disposition

Final run: **983 passed in 17.99 seconds** across 16 affected backend test files. Supervisor elapsed 19.73 seconds, exit 0, process reaped, input hashes unchanged. Tests use synthetic JWTs, files, SQL stores and model interfaces. Existing offline guards block DNS, real database/provider calls. No real identity, hosted network, payment, athlete conversion or Linux container claim.

Independent review found three closure issues: missing package members, incomplete reviewed source digest and unguarded new acceptance connector alias. All were corrected. Final independent admission/integration review found no material issue. The broad run also identified one outdated exact package-list assertion, updated to reflect the intentional two-module addition.

Earlier attempts are retained honestly: the old Python 3.11 environment stalled during SDK imports and was terminated by its 240-second supervisor before tests; a temporary Python 3.13.7 environment initially lacked PyMySQL and requests (959 passed, 24 failed, including the package assertion). Both dependencies and pytest were installed offline from cache into `/private/tmp/sparq-verify-20260923`, without modifying production/repo dependencies. The complete same affected test set then passed. No source failure was waived.

Raw artifacts live outside Git at the sibling `../sparq-pilot-gate-2026-09-23/`:

- `focused-pytest.log` / `focused-pytest-receipt.json`: old-runtime timeout.
- `focused-02.log` / `focused-02-receipt.json`: initial new-runner failures and unchanged source receipt.
- `focused-03.log`, `focused-03-receipt.json`, `focused-03-input-hashes.json`: final successful run and exact inputs.
- `profile-candidate-source.tar` and `.manifest.json`: 29 exact source files; archive SHA-256 `7a1a689ea4aa2289d2a432097ef74813f9e751c43aba47f7550f90e7f1c7b8c4`. This is source packaging, not a Linux image or release.

No preview/server is left running; test requests were in-process, with subprocess import probes completed. Local runtime checks were finite after identifying and terminating one root-owned initial import probe. UI code was unchanged; prior UI/build checks remain historical and were not replayed as current evidence.

## Next delivery and revenue boundary

Use `docs/state/profile-pilot-release-manifest-2026-09-23.md` to identify and verify paired hosted targets, immutable backend/frontend artifacts, origins, private admission mounting and rollback. Concrete deployment approval remains with Joey. Do not point to pre-prod, replay workspace migrations, expose legacy main routes as the pilot, provision claims as an ungated exception, or reset the exhausted founder save allowance. Initial AI debrief and measurement stay off until their own reviewed configuration/acceptance.

Then verify the hosted journey for a small explicitly admitted, already-linked adult cohort: existing footage/profile → current relevant opportunity → useful editable introduction → save/reload → return use. Full GMTM SSO and billing/entitlements remain separate. Develop one organization-paid league/program pilot through Charles alongside that work; buyer, price, budget and agreement remain unconfirmed. No sale, pilot uptake or affiliate revenue is established by these tests.

No push, deployment, AWS/RDS/IAM change, actual database mutation, model call, admission record provisioning, billing action, registration or external message was performed. Source changes, new tests, September 23 documents and the preserved September 14 planning documents form this local commit; exact commit/clean-state receipt is recorded outside Git after committing to avoid a self-referential hash.
