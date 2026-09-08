# Luna integration and bounded synthetic evaluation

September 7, 2026. Joey explicitly approved the proposed local Luna integration, usage tracking/request limits and synthetic comparison. The [completion contract](../../docs/state/luna-evaluation-contract-2026-09-07.md) is complete. The owned checkout remains `work/sparq-agent-review`, branch `codex/athlete-home-first-value`, HEAD `6c7e649`.

## What changed

Combine help now supports opt-in `COMBINE_HELP_MODEL=gpt-5.6-luna`, preserving Sonnet 4.6 as the default. The existing authenticated source loader, request validation, deterministic owner/event/task projection and SSE behavior remain. Luna uses one Responses request with low reasoning and no tools; Sonnet retains at most three turns of its existing same-snapshot tool. Requests pin official endpoints, disable proxies/redirects/retries and cap output/time/stream size. OpenAI uses `store=False`.

The new bounded process ledger records every attempted call including tool continuations and failures, with safe status, duration and nullable token/cost metadata. Configuration freezes on first use; explicit test mode requires finite call/concurrency limits. Aborted usage stays unknown. This is not durable or multi-worker accounting, and other recruiting/research calls are not covered. The [configuration document](../../docs/state/combine-model-configuration.md) explains the exact limits and remaining scope.

## Verification and live result

- 96 focused adapter/accounting tests passed, including existing help regressions, cancellation/cleanup, completion/refusal/incomplete handling, unknown usage and atomic call limits.
- The full offline backend suite passed **315 tests** using fail-closed DB/provider/network guards. The 96 focused tests are included in that total.
- Independent synthetic-runner tests passed **15 tests and three subtests**. Review caught and fixed async Responses wrapping, close-failure recording, resumed usage persistence and explicit stop-on-budget-exhaustion before paid execution.
- Independent application review found no remaining blocker before the run. All three reviewed app source hashes matched when executed and after the run. All 121 frontend file hashes matched.
- Two independent provider-blinded answer reviews found no critical rubric failures. They agreed on three partial-coverage answers and documented minor wording/provenance issues. Root resolved one queried background-highlight fact against its explicit inclusion in the unchanged shared system prompt.
- Actual app adapter: **12 complete answers**, six per model, using **18 provider calls**. No answer retry or automatic fallback occurred. Every call returned usable token metadata and the process ended with zero in-flight calls.
- Luna: six calls, median 3.42 seconds, estimated $0.0036654. Sonnet: twelve calls, median 9.89 seconds, estimated $0.154974. Total $0.1586394, under the $2 conservative allowance. Durable reservations totaled $1.7119986; they were not released/reset to manufacture more test budget.

See the [evaluation report](../../docs/research/luna-combine-evaluation-2026-09-07.md) for quality findings and the essential comparison caveat: Sonnet made a redundant snapshot-tool lookup for every question, while Luna answered directly. The roughly 42-fold cost gap is for these implemented flows, not a general model price or intelligence ratio.

## Receipts and runtime

Local artifact directory outside the repo: `../sparq-model-eval-2026-09-07/` (mode 700). Redacted/synthetic receipts are mode 600: `results.json`, persistent `attempts.json`, `metrics.json`, `verification.json`, `frontend-preservation.json`, `blinded-answers.json`, `answer-model-map.json` and reviewer files. `run_eval.py` uses an exclusive process lock, starts each model/case once, reserves each SDK transmission durably and preserves unknown reservations across restarts. `prepare_review.py` prepares blinded answers and arithmetic summaries. Only synthetic generated answers are stored; usage records contain no prompt or identity.

An isolated Python 3.11 environment at `../sparq-model-eval-venv/` ran OpenAI 2.24.0, Anthropic 1.4.0, httpx 0.28.1, FastAPI 0.133.1 and Pydantic 2.13.5. It did not alter Hermes's Python environment. SDK-native HTTP clients were used because this Anthropic version uses httpx2. Constructors were checked before the run. No full application backend or source database was started by this evaluation.

Existing OpenAI and Anthropic keys were fetched through the authorized SSH/Railway access and held only in captured subprocess/current-process memory. No values were printed, written to disk or placed in command arguments. Only fabricated progress/history and public program requirements were sent to each provider. This was a separate synthetic authorization; the earlier five-attempt real-athlete harness was not reset or reused.

## Next action and boundaries

Luna is the next routine-help pilot candidate. Tighten the observed ambiguous video-field wording and explicit public-help availability, broaden the test set, and remove redundant Sonnet snapshot retrieval before a wider comparison. Durable usage and research deduplication remain open. No new provider purchase is needed for the next local development step.

No production variable, deployment, remote credential file, database, infrastructure resource or other checkout was changed. Railway's OpenAI key remains invalid; local success does not make it deployment-ready. Real-account Luna acceptance, junior ownership behavior, scale quotas and production behavior remain unverified.

## Uncommitted changes in this batch

- Application: `backend/combine_help_api.py`; new `backend/combine_model.py` and `backend/model_usage.py`.
- Offline boundaries/tests: `backend/tests/conftest.py`; new `test_combine_model.py`, `test_model_usage.py`, `test_combine_eval_fixtures.py` and `fixtures/combine_model_eval_2026_09_07.json`.
- Documentation: this handoff; current-state and model-strategy updates; new evaluation contract, model-configuration guide and evaluation report.
- Outside repo: isolated runtime and synthetic runner/receipts/reviews noted above.

No commit or push occurred. Existing unrelated uncommitted work remains outside this batch's scope.
