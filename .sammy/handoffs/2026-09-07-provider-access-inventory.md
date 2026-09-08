# Existing provider access

September 7, 2026. Joey asked which APIs are already accessible for the proposed SPARQ model strategy. Read-only inspection retained the existing Codex checkout, branch `codex/athlete-home-first-value`, HEAD `6c7e649` and all application edits.

## Verified result

- The exact SPARQ Railway production backend service has nonempty `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `GEMINI_API_KEY`. Values were captured only in process memory; no key was printed or saved. No matching provider keys were present in the current local process environment.
- Anthropic model-information GETs returned 200 for `claude-sonnet-4-6`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`, `claude-opus-5` and `claude-fable-5-1`. Sonnet 4.6 generation was separately demonstrated in the prior five-attempt local acceptance. Other Anthropic models were not used for generation.
- OpenAI model-information GETs returned 401 for Luna, Terra, Sol and Astra. A bounded diagnostic confirmed there is no outer whitespace in the stored key and the provider's error category is `invalid_api_key`. No raw error body or key was exposed. The OpenAI credential needs replacement through the normal secure configuration process before an adapter can use it. No replacement was attempted.
- Gemini model-information GETs returned 200 for `gemini-3.8-flash` and `gemini-3.5-flash-lite`. Credential/model metadata access is verified; paid-tier status, quota and actual generation remain unverified.
- No standard key bindings for xAI/Grok, Mistral, DeepSeek, OpenRouter or AI Gateway were found in this SPARQ backend. This is a project-scoped finding, not a claim that Joey has no account or key anywhere else.

Only model IDs and each provider's own credential were sent to that provider's fixed HTTPS endpoint. Redirects were disabled. No prompts, athlete data, generation calls or billing changes occurred; the previous five-attempt inference cap remains exhausted.

## Implementation distinction

Independent source review confirms Anthropic is the only implemented model provider across the current seven callsites. OpenAI is a declared Python dependency with no implemented request path. Gemini has no current adapter. Authentication success alone does not connect these providers to athlete flows or verify billing/throughput.

Other existing integrations: Clerk authentication; GMTM/Agent MySQL source and persistence adapters; Railway hosting/configuration; Vercel frontend; GitHub repository access. Codex's Gmail and other connector capabilities support this working session and are separate from production application integrations. SendGrid/Resend consumers exist in source, but their credentials and delivery were not checked here. MaxPreps code is page scraping, not proof of private API access.

## Evidence and next action

Redacted receipt: `../sparq-live-browser-2026-09-07/provider-access-inventory.json`, mode 600. It records key-presence booleans, OpenAI/Gemini metadata statuses and safe OpenAI authentication diagnostic, without secret values. Anthropic metadata responses are recorded in this turn's tool output and summarized above. Official endpoint documentation was checked: [OpenAI models](https://developers.openai.com/api/reference/resources/models), [Gemini models](https://ai.google.dev/api/models) and [Gemini authentication](https://ai.google.dev/api).

We can implement bounded Anthropic/Gemini adapters with existing credentials; candidate generation/data-transfer tests remain separate from this metadata inventory. Luna additionally needs a working OpenAI key in Railway. No provider switch, production write, infrastructure action, deployment, new subscription or application edit occurred.

Only this handoff, the current-state pointer and the model report's access note changed inside the repo; the redacted receipt was added outside it. All changes remain uncommitted. No tests were rerun because application code did not change. Documentation links/whitespace were checked.
