# Mac mini Hermes provider access

September 7, 2026. Joey asked to check the Mac mini for existing Hermes API credentials, especially OpenAI for Luna. This was a read-only inventory and authentication check, preserving the existing SPARQ checkout on `codex/athlete-home-first-value` at `6c7e649`.

## Completion contract and result

Identify relevant Hermes credential sources, distinguish reusable API keys from subscription OAuth, validate suitable keys without inference, and record redacted results. This contract is complete; deployment configuration and generation tests remain separate work.

Existing SSH access succeeded over Tailscale with the dedicated Mac mini identity and strict verification against the existing host-key alias. No SSH configuration or key was changed. Passive inspection was limited to Hermes's default `.env`, `config.yaml` structure, `auth.json` credential-presence fields and named-profile directory presence. No named profiles were found. Independent local Hermes source review established expected provider/auth schemas; differing installed versions or alternate runtime configurations were not reconciled.

| Source on Mac mini | Verified result |
| --- | --- |
| Hermes `OPENAI_API_KEY` | Official OpenAI `GET /v1/models/gpt-5.6-luna` returned HTTP 200 with the matching model ID. This credential authenticates for Luna model metadata. |
| Hermes `OPENROUTER_API_KEY` | Authenticated `GET /api/v1/key` returned HTTP 200 with a valid data object. This was the authenticated key endpoint, not the public model catalog. |
| Hermes `ANTHROPIC_API_KEY` | Official Anthropic Sonnet 4.6 model metadata returned HTTP 401 with `authentication_error`. This result concerns this mini environment entry only; the separately verified Railway Anthropic key works. |
| Hermes OpenAI Codex and xAI OAuth stores | Access/refresh token presence observed. Tokens were not used, refreshed or copied, and are not treated as reusable production API keys. |

No direct Gemini or xAI API-key binding was found among the inspected Hermes environment variables. The earlier Railway Gemini credential remains separately verified for metadata access. Pool records without `access_token` do not establish absence of all credentials in a different Hermes version; the live results above came from the explicit environment entries.

Each credential stayed on the Mac mini and went only to its provider's fixed HTTPS endpoint. Redirects were disabled. Only whitelisted statuses, presence booleans and a matching-model-ID boolean were printed. No raw credentials, account labels, account balances, error bodies, prompts or athlete data were returned. No generation call occurred; quota, billing, throughput and response quality remain unverified. The earlier five-attempt Anthropic inference allowance remains exhausted.

## Next action

There is an existing authenticated OpenAI credential available for a future authorized Luna test; Joey does not need to obtain another solely to establish API access. SPARQ's existing Railway OpenAI binding is still invalid, and no OpenAI adapter exists in the app. No credential was transferred, Railway variable replaced, production configuration changed or deployment performed by this task. A dedicated SPARQ credential would separate production usage from Hermes when configuring deployment. Local provider adapters, usage accounting and bounded synthetic evaluation remain the technical next steps under the model strategy.

Redacted receipt: `../sparq-live-browser-2026-09-07/mini-provider-access-inventory.json` (mode 600). Endpoint references: [OpenAI model retrieval](https://developers.openai.com/api/reference/resources/models), [OpenRouter authenticated current-key metadata](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key).

Uncommitted changes from this turn: this handoff, the current-state provider pointer and the model report's access note; the redacted receipt is outside the repository. No application edits or new runtime tests were needed for this inventory. Documentation links and whitespace were checked. Other existing uncommitted application work remains outside this turn's scope.
