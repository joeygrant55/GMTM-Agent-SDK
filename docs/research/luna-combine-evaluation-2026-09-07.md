# Luna versus the current Sonnet combine-help flow

September 7, 2026. The local Luna integration works end to end through the application's actual streaming adapter. Luna is the leading candidate for a routine combine-help pilot: in this small synthetic test it completed every answer, was more concise and cost less than the current Sonnet 4.6 flow. This does not establish a production rollout or a universal model ranking.

## Measured result

| Measure | GPT-5.6 Luna, low reasoning | Current Sonnet 4.6 flow |
| --- | ---: | ---: |
| Completed answers | 6 / 6 | 6 / 6 |
| Provider calls | 6 | 12 |
| Median time to first text | 1.26 seconds | 3.56 seconds |
| Median complete-answer time | 3.42 seconds | 9.89 seconds |
| Mean answer length | 89 words | 150.5 words |
| Reported input tokens | 12,885 | 43,738 |
| Reported output tokens | 907 | 1,584 |
| Estimated cost for all six answers | $0.0036654 | $0.154974 |
| Calls with unreported/unpriced usage | 0 | 0 |

Total estimated inference cost was **$0.1586394**. Eighteen provider calls were used; the durable runner reserved $1.7119986 conservatively against its 24-call/$2 estimated ceiling. No failed answer was silently rerun. All answers stayed under 220 words. Luna's reported output includes 152 reasoning tokens; these were charged once as part of output, not added again. No cache hits were reported.

Costs multiply provider-reported tokens by standard prices checked September 7: [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing). These are price-based estimates, not reconciled invoices or provider account balances.

## Why the cost and latency gap is large

This compares the implemented assistance paths, not isolated model calls with identical tool configuration. Both received the same application system prompt, synthetic context and questions. Luna answered directly from the server-loaded snapshot. Sonnet used its existing no-argument context tool on every case, retrieving the same data it already had and requiring a second model turn. The measured roughly 42-fold cost difference includes that redundant context round trip, different tokenization and output length, as well as model prices. Removing the redundant Sonnet call is a separate optimization; this experiment does not prove the same ratio would survive it.

## Cases and quality

The six cases used public combine requirements and fabricated progress/history: highlights with no results; the 20-yard/40-yard caption mismatch; all required fields present without established eligibility/membership/selection; unavailable junior/guardian progress; injected organizer/history instructions; and a saved push-up video missing its count. No real athlete identity, submitted answer values or source database queries were used. Rubrics and case IDs were withheld from both providers. Provider order alternated by case.

Two independent provider-blinded reviews found no critical rubric failure in any of the 12 answers. Both models preserved the main distinctions: unknown progress is not zero, saved fields are not qualification, chat cannot save submissions, and untrusted text cannot change ownership or reveal secrets. The reviews agreed on three partial-coverage answers: both junior answers omitted an explicit offer of public-checklist help, and Sonnet's push-up answer omitted the video-validation caveat. Completion should not be described as perfect rubric coverage. One reviewer queried whether the optional background-form highlight field was supported; root verified that fact is explicitly present in the shared application system prompt, so it is not an unsupported claim.

Luna's dash answer said “video or evidence field,” which is needlessly ambiguous about the required video. Its junior answer did not explicitly offer continuing public-checklist help in chat. Two answers placed the correct deadline after the action link. Sonnet was generally longer, sometimes mentioned implementation details, and made unsupported statements about workflow ownership or the provenance of a prior assistant message. None of these observed answers disclosed a secret, followed the attacker destination or claimed that the athlete qualified.

## Decision and next work

Keep the local opt-in Luna adapter and use it as the next routine-help pilot candidate. Preserve deterministic source facts and the existing default until the pilot has its own acceptance. Tighten the video-field wording and explicit help availability for unlinked athletes; expand the evaluation beyond six cases, particularly ambiguous source descriptions, longer history and junior accounts. Remove Sonnet's redundant snapshot lookup before drawing a broader economic comparison. Evaluate higher-capability models only on tasks where the cheaper path demonstrably fails.

The new ledger covers combine assistance only. Research fan-out, durable cross-worker usage limits and other model callsites remain separate work. No new API subscription is needed for the next local development step. Production still needs its invalid OpenAI binding corrected through secure configuration before Luna could run there; this test did not change it.

## Evidence

- Contract: [local evaluation limits](../state/luna-evaluation-contract-2026-09-07.md).
- Settings and limits: [combine model configuration](../state/combine-model-configuration.md).
- Synthetic fixtures: [six evaluation cases](../../backend/tests/fixtures/combine_model_eval_2026_09_07.json).
- Private local receipts outside the repo: `../sparq-model-eval-2026-09-07/results.json`, `attempts.json`, `metrics.json`, `blinded-answers.json`, `answer-model-map.json` and the blinded reviewer files.
- Full offline backend suite: 315 passed. Focused adapter/accounting suite: 96 passed (included in the full suite). Separate durable-runner suite: 15 tests and three subtests passed. No frontend source was edited for this batch.

Results are local, synthetic and based on one attempt per case per model. Real-account end-to-end Luna acceptance, generation quotas at scale, real athlete outcomes and production readiness remain unverified. OpenAI was requested with `store=False`; credentials were held only in isolated process memory. No deployment or remote credential/configuration change occurred.
