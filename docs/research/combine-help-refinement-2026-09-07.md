# Combine-help refinement — September 7, 2026

## Decision

Luna remains a promising routine-help pilot candidate. This refinement removes a redundant Sonnet context request and improves field-format guidance, but the live review found a material progress-state error in a Luna answer. Do not treat this as athlete-facing acceptance or authorize a production switch from these results.

This is a separate, targeted follow-up to the [original six-case comparison](luna-combine-evaluation-2026-09-07.md), not a replacement benchmark. Original answers, metrics and review artifacts remain intact.

## Implemented behavior

Both providers now answer from the already authorized, freshly loaded combine context in one SDK request. No tools, repeated snapshot retrieval, automatic retry or model fallback are offered. Source ownership checks, bounded streaming, cancellation, usage accounting and per-athlete admission remain in place.

Public required-field types and exact titles are included even when personal progress is unavailable. The model receives no submitted answer values or metric-template metadata. Video fields remain explicitly video; labels alone do not establish units, standards or eligibility. Legacy missing definitions remain unknown. The frontend's existing parser accepts the additive source field without a frontend change.

Eight additional synthetic fixtures cover malicious URLs/format instructions, stale history, junior ownership uncertainty, deadlines, shuttle directions, video-only squat, truncated descriptions and absent metadata. Fixture and deterministic context tests are offline checks; only two of these eight new cases were sent to a provider in this follow-up.

## Five targeted live checks

The adult dash-label case ran once on each model. Luna also answered the existing unlinked-junior case and the new malicious-description and truncated-instructions cases. These tests used the actual streaming adapter with synthetic source data, without Clerk or database access.

| Model | Answers completed | Provider calls | Completion time | Estimated total cost |
| --- | ---: | ---: | --- | ---: |
| Luna | 4/4 | 4 | Median 2.39 seconds | $0.0030262 |
| Sonnet 4.6 | 1/1 | 1 | 6.18 seconds, one observation | $0.012894 |

All five ended successfully with no remaining in-flight calls. Total estimated inference cost was $0.0159202. Costs use observed token usage and the application's dated pricing table; they are not an invoice.

For the repeated Sonnet dash case, provider calls fell from two to one, observed cost from $0.02649 to $0.012894, and response time from 9.50 to 6.18 seconds. Prompt/context changes and one observation per version prevent attributing all timing or cost differences to the removed call. Luna's repeated dash answer was slower than its original sample, so this is not evidence of a universal latency improvement.

The durable original allowance now records 23 total calls and $1.8792244 in conservative reservations, below its original 24-call/$2 limit. The first 18 call records and first 12 case records were preserved. This addendum's five-call limit is exhausted; no additional live call is authorized by its contract. Reservations were neither refunded nor reset.

## Answer review

Two independent reviewers graded provider-blinded answers against their actual source context. Both dash answers now clearly required a 20-yard time plus video. The malicious URL was ignored; missing clip specifications were not invented. All five answers stayed within 220 words.

Both reviewers nevertheless found that Luna's dash answer said “Your saved attempt” when the source explicitly said no submission was visible. This is a material correctness failure even though it was outside the original case's enumerated hard-failure clauses. Another Luna answer correctly reported no submission, then incorrectly suggested submission status itself was unestablished. Public-checklist help was explained without the explicit offer requested by the prompt, and one highlight answer omitted the known playing-footage detail.

These examples remain in the results and review adjudication. They must not be reclassified as a clean pass because the provider streams completed or the narrow rubric missed them. The follow-up correction and its verification are recorded in the [handoff](../../.sammy/handoffs/2026-09-07-combine-help-refinement.md). That correction has no additional live model validation in this batch.

The final local correction adds explicit, server-derived meanings for no saved attempt, saved field presence and unavailable progress, while keeping organizer acceptance independently unknown. It replaces the ambiguous instruction that encouraged treating missing labels as proof of a saved attempt. All 361 backend tests pass, including 97 focused status/context/help checks; independent review found no blocker. The exact live-evaluated predecessor is preserved with its matching hash. Local semantic tests do not prove that the revised model wording will pass the next live run.

## Evidence and limits

Live artifacts are local-only under `work/sparq-help-refinement-2026-09-07/`, alongside the checkout: frozen source hashes, request hashes, answers, model mapping, metrics, two blinded reviews, adjudication, allowance preservation and verification. The live-evaluated source passed 348 backend tests and the runner passed 13 independent offline tests. All 121 captured frontend hashes matched. Original comparison artifacts were unchanged; only its durable attempt file gained the five permitted reservations.

The test runtime was recreated under `/private/tmp/sparq-refinement-runtime-2026-09-07` because SDK files in the Documents-based environment had been offloaded to cloud storage. Provider SDK versions remained pinned. Credentials were captured only into process memory; no key files, Railway configuration, databases, production routes or deployment changed. The earlier authenticated browser harness was not reloaded and does not validate this source revision.

Next acceptance should exercise precise progress wording, junior account uncertainty and public-help availability with the corrected source. Before an athlete pilot, separately close the remaining real-account/guardian and release gates. Durable multi-worker usage budgets and production OpenAI configuration remain open work.
