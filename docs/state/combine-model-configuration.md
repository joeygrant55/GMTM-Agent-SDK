# Combine-help model configuration

This local implementation supports `claude-sonnet-4-6` (default) or `gpt-5.6-luna` through the server-only `COMBINE_HELP_MODEL` variable. The matching `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` must exist in the backend process. Model names and provider endpoints are allowlisted in code; clients cannot choose them through the help request. Do not put credentials in frontend variables, tracked files or command arguments.

The authenticated route reloads the caller's deterministic combine context before any model call. Both providers answer from that same system prompt and bounded snapshot in one request, with no tools or repeated context lookup. Luna uses the Responses API with low reasoning and `store=False`; Sonnet uses a direct Messages request. Both disable automatic retries and redirects. No automatic model fallback occurs.

The snapshot includes public required-field types and exact titles even when personal progress is unavailable. Submitted values and metric-template metadata are excluded. Missing legacy definitions remain unknown; a field label alone does not establish units, passing standards or eligibility. Public instructions and personal progress remain separate.

Internal model context also derives `status_observation` from each source activity. No visible attempt, a saved attempt with incomplete or unknown field presence, and unavailable personal progress are distinct; organizer acceptance stays unknown. This is an interpretation of observed status, not semantic validation of an athlete's answers. The post-evaluation correction is locally tested but still requires live wording acceptance.

## Limits and usage

Existing per-athlete request/admission limits remain. Each model call reserves one slot from a shared process ledger before SDK invocation. Four model calls may be in flight by default. Set `COMBINE_HELP_MAX_CONCURRENT_CALLS` to a positive integer up to 16 to override. `COMBINE_HELP_MAX_MODEL_CALLS`, when configured, bounds total calls during that process lifetime; normal mode has no default lifetime call cap.

For a bounded local test, set `COMBINE_HELP_TEST_MODE=1` plus explicit positive `COMBINE_HELP_MAX_MODEL_CALLS` and `COMBINE_HELP_MAX_CONCURRENT_CALLS`. Invalid or missing test limits fail closed. Configuration freezes when the ledger is first used; changing environment variables does not reset its counters. No automatic fallback or retry extends an allowance. Each response has a 1,200-token maximum (including Luna reasoning), a 30-second model deadline and a 16,000-character stream limit.

`model_usage.get_usage_snapshot()` is an internal Python interface, not a public API. It exposes process counters and the most recent 256 call records: provider/model, terminal status, duration, validated token counts and price-based cost estimates. It excludes prompts, answers, athlete/Clerk IDs, credentials and provider response IDs. Missing usage is unknown, not zero; an unpriced cache write remains unknown rather than being charged as ordinary input. Pricing is dated September 7, 2026 and is not invoice reconciliation.

These limits and usage records are process-local and reset on restart. They are not a durable multi-worker billing ledger or account-wide quota. The [synthetic evaluation contract](luna-evaluation-contract-2026-09-07.md) additionally uses a locked persistent attempt/reservation file outside the repo to enforce its combined 24-call/$2 estimated allowance across restarts. No application endpoint exposes that evaluation runner.

## Scope and release

This implementation covers current-combine assistance only. Other recruiting/research calls retain their existing behavior and do not use this ledger. Durable usage accounting, research deduplication and wider model routing remain separate work.

The local model comparison does not change deployed environment variables or authorize a production model switch. Retain source/authentication, real-account/guardian, failure/latency and production acceptance gates before rollout. Current Railway OpenAI configuration remains invalid until separately corrected through secure configuration.
