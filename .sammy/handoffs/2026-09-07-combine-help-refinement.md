# Combine-help refinement handoff — September 7, 2026

## Scope and lane

Joey asked Codex to continue after Luna integration and the first synthetic comparison. Work stayed in the existing `work/sparq-agent-review` checkout, branch `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`. Follow the [completion contract](../../docs/state/combine-help-refinement-contract-2026-09-07.md) and [results report](../../docs/research/combine-help-refinement-2026-09-07.md).

All changes remain local and uncommitted. No push, deployment, production data/configuration change, credential persistence, AWS operation or external message occurred. Existing uncommitted work and the earlier browser harness were preserved; the harness was not reloaded for this revision.

## Implementation

- Both models use one direct SDK request from the existing authorized snapshot; no redundant Sonnet context tool. Preserve failure, cancellation, stream cleanup and observed usage even if final SDK message retrieval fails.
- Add bounded public required-field types/titles to the source projection and model context, including for unlinked users. Do not transmit submitted values or metric-template metadata; retain unknown formats and exact source labels.
- Refine instructions for video requirements, public assistance, unknown junior ownership, untrusted URLs/history, incomplete organizer guidance and final GMTM next steps.
- Add eight synthetic edge fixtures and focused context/field checks.

## Live evaluation and retained failures

Five synthetic answers completed with five provider calls: four Luna, one Sonnet. Estimated combined cost $0.0159202. Luna median completion time 2.39 seconds; one Sonnet observation 6.18 seconds. This was a targeted follow-up, not a balanced model benchmark.

The runner reused the original locked durable allowance. It retained all first 18 calls and 12 cases, froze source/public definitions/request hashes, preflighted all five reservations before loading keys, permitted one SDK call per case, and persisted rejection stops. Final original allowance: 23 calls, $1.8792244 reservations. Original result/review/metric files remained unchanged. This addendum's five-call allowance is exhausted; do not clear state, retry its cases or enlarge its plan.

Provider-blinded reviews agreed on a material Luna error: it described a saved attempt although none was visible. A second answer blurred known submission status with unknown organizer acceptance. Public-help and highlight-description omissions also remained. Preserve these findings; successful streams and zero narrow rubric flags do not mean all answers passed correctness acceptance.

## Receipts and verification

Sibling directory `work/sparq-help-refinement-2026-09-07/` contains the runner, its 13 passing offline tests, exact preflight hashes, `results.json`, `metrics.json`, blinded answers/mapping, both reviews, `review-adjudication.json`, `allowance-preservation.json` and `verification.json`. These files are local-only. The latter verification describes the live-evaluated revision: 348 backend tests passed, all eight frozen source hashes matched and all 121 captured frontend hashes matched, with zero in-flight calls after completion.

The isolated live runtime is `/private/tmp/sparq-refinement-runtime-2026-09-07`; provider SDKs are OpenAI 2.24.0 and Anthropic 1.4.0. The Documents-based environment stalled because macOS had offloaded SDK source files; no checkout was moved. Credentials were captured from the already authorized mini/Railway sources into process memory only. No database or real athlete source was used for these five calls.

## Changed files in this continuation

Application: `backend/combine_model.py`, `backend/combine_help_api.py`, `backend/combine_requirements.py`, `backend/combine_context.py`.

Tests: `backend/tests/test_combine_model.py`, `test_combine_help.py`, `test_combine_requirements.py`, new `test_combine_context_fields.py`, new `test_combine_edge_fixtures.py`, and new `fixtures/combine_edge_eval_2026_09_07.json`. The bounded post-review status correction adds `test_combine_status_wording.py` and its evidence below.

Documentation: the refinement contract/report, this handoff, `docs/state/combine-model-configuration.md`, and `docs/state/current-state.md`. Evaluation scripts, preserved source copies and synthetic receipts stay outside the repository in the sibling artifact directory. Other dirty/untracked files reported by Git predate this continuation and were not reset or staged.

## Final local status correction

The ambiguous prompt sentence about missing fields in a saved attempt was replaced with explicit independent meanings. Each model-context activity now receives a recomputed `status_observation`: whether a visible saved attempt exists (`false`, `true`, or unknown), whether required-field presence was assessed, and organizer acceptance always unknown. Missing requirement labels alone never establish that an attempt exists. A saved but unreadable payload keeps the observed attempt while field presence remains unknown. Public definitions stay available with unavailable personal progress; the prompt requests an explicit offer of help here.

The final source passed 97 focused status/context/help tests and all 361 backend tests, with clean whitespace and independent source/test review. Tests cover no attempt versus empty saved attempt, partial/invalid-looking saved values, malformed payloads, unknown progress and field formats, injected observations, privacy and the context bound. Maximum context plus prompt/separator is 39,383 characters, below the adapter's 40,000-character bound.

`post-fix-verification.json` records final hashes. The only evaluated application source changed after live calls is `backend/combine_context.py`, now SHA-256 `50c677f023da07a20612abd23d33fbf7f9ff411bd021ef04abc2da5871eced54`. Its exact live-evaluated predecessor was preserved as `live-evaluated-combine_context.py`, SHA-256 `2d20610140bb14648a5bfe12362b189e0c367d1c15722f8e2c8528ff595863ca`, matching `results.json`. No live answers, reviews or attempt counters were rewritten. This is a locally verified correction; no subsequent model call or browser acceptance validates the revised prompt.

## Next gate

Keep Luna as the routine-help candidate, not an approved athlete rollout. Verify the final status correction with a separately authorized, bounded acceptance run before relying on its model wording. Real junior/guardian behavior, production OpenAI configuration, durable multi-worker accounting and deployment acceptance remain separate gates. The old real-athlete five-attempt allowance remains exhausted as well.
