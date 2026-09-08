# AI acceptance and model strategy

September 7, 2026. Same owned checkout and branch `codex/athlete-home-first-value`, HEAD `6c7e649`. Joey explicitly approved up to five local Anthropic help tests with test questions, public requirements and minimized progress statuses, and asked which models fit SPARQ by intelligence and cost.

## Acceptance result

Five approved requests ran through the real signed-in UI, real Clerk verification, unique GMTM user 2 mapping, guarded read-only adult event 1318 source and actual Sonnet 4.6 streaming. No mocks or full application bootstrap were used for these requests.

1. Original Highlight Reel question: returned a full-combine checklist with Markdown and ended in a generic terminal stream error. UI labeled the answer incomplete, restored the question and retained organizer/GMTM options. The underlying provider stop reason or timeout cause was not recorded and remains undiagnosed.
2. Same question with focused, concise, plain-text prompt: completed; explained the highlight field and separated submission from qualification. It unnecessarily mentioned a public task ID, addressed in final wording.
3. Adult dash title/caption mismatch: completed; correctly explained 20 yards and the video plus time fields. Its cone spacing, start stance and timing advice were checked against the visible organizer instructions.
4. At phone width, a question requested marking missing submissions complete, a guaranteed qualifying time and membership validation. Answer completed, refused unsupported changes/guarantees and preserved the zero-submission observation.
5. Final polished prompt, original Highlight Reel question at phone width: completed, concise and grounded, with no internal task ID or invented destination.

The final prompt retains identity/provenance/eligibility rules, adds explicit focused-task interpretation and bounded plain-text guidance, and excludes internal implementation terminology and URLs absent from context. These are model instructions, not guarantees or a deterministic word-count validator. Only attempt 5 used the final wording; attempts 2–4 used the earlier focused refinement.

The original server recorded 1 help attempt / 0 done / 1 error. The first restart recorded 3 attempts / 3 done / 0 errors. The final restart recorded 1 attempt / 1 done / 0 errors. Restarts required stopped prior receipts and narrowed the remaining caps to four, then one. Total: 5 attempts, 4 completed answers, 1 initial failure, no remaining approved inference attempts. All authenticated source observations retained nine activities, zero submitted, zero required-information-present activities, with zero source failures.

## Verification and limits

- Fifty-four existing backend help tests passed against the final source. Independent review found no blocker in the prompt or remaining-attempt launcher guards. No broad repeated test run was needed for this prompt-only code change.
- All 121 frontend source/snapshot hashes remain identical. Browser showed one input, no horizontal page overflow at 390 × 844, visible input controls and no observed browser exceptions. Final screenshot was captured for visual review.
- Existing real sign-in, source refresh and continuation destination checks remain valid. No authenticated GMTM continuation was opened, no submission made, no identity link created/reassigned, and no database write performed.
- This validates the bounded local account/event flow and sampled answers, not production deployment, physical devices, all athlete/junior/guardian states, full provider reliability, actual token billing or comparative model intelligence. No extra calls were made to test the exhausted cap.

## Model evaluation deliverables

See [model strategy](../../docs/research/sparq-model-strategy-2026-09-07.md) and [cost scenarios](../../docs/research/model-cost-scenarios-2026-09-07.json). Official current vendor pricing/capabilities were researched for OpenAI, Anthropic, Google, xAI, Mistral and DeepSeek. The recommendation is a small candidate set: current Sonnet 4.6 baseline, Sonnet 5 for main assistance, Luna for routine work, and Gemini later for video. Candidate quality and account access remain untested.

Independent source review found seven current callsites using Sonnet 4.6 and no cost ledger or model router. Legacy onboarding/research can expand into many calls and repeat jobs; measure and bound it before aggressive provider expansion. The cost comparison is transparent fixed-token arithmetic, not observed spend. It includes a separate Sonnet 5 tokenizer sensitivity and distinguishes direct routing from extra escalation calls.

Next work: add privacy-safe usage metadata and centralized workload budgets, deduplicate/cap research fan-out, then evaluate candidate models against a common synthetic/public task set. New-provider private-data transfers, production rollout and new spend/account settings require their existing authorization boundaries; this turn did not change them.

## Runtime and artifacts

Frontend remains at `http://localhost:3218/home/inbox?event_id=1318` (exec session 93390). Final restricted backend remains at `127.0.0.1:8118` (session 64196), launched with `../sparq-live-browser-2026-09-07/launch_backend_final.py`. Browser session `sparq-live-0907` remains signed in at phone width with the final answer. Read-only checklist access remains possible; the one-attempt model cap is exhausted. Verify process/port state on continuation; do not restart merely to reset the approved cap.

Operator folder: `../sparq-live-browser-2026-09-07/`, mode 700. New evidence: `ai-acceptance-results.json`, `live-server-receipt-focused.json`, `live-server-receipt-final.json`, the two bounded continuation launchers, local `*-help-*.txt` transcripts and `ai-mobile-final.png`. The original receipt remains stopped and preserved. No verification-code/token/cookie/auth-state export was created. Local transcripts/screenshots remain outside the public application repository.

Final `backend/combine_context.py` SHA256: `5ba6f893e75f0efb70265bba0348c52aa18ff74606d8e54fbabde7440ef3cbbf`. Harness file remains frozen at `424e8a0cf16123715a37522dff0d16bf4931ac2b72b28caea083546bcd346e90`.

## Uncommitted changes

This turn edited `backend/combine_context.py` and `docs/state/current-state.md`; added the two research files and this handoff; and created local operator receipts/continuation launchers outside the repo. All prior application changes remain uncommitted and preserved. No commit, push, deployment, production credential/data edit, infrastructure action, external message or model-provider switch occurred.
