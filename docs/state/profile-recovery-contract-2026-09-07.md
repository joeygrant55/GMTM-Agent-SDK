# Read-only profile recovery and junior acceptance

Joey explicitly asked to proceed with account-recovery hardening, followed by tracing the real junior-account journey. Work remains local in the owned checkout.

Completion requires:

- Keep GET `/api/profile/by-clerk/{clerk_id}` caller-scoped and read-only. Remove workspace bootstrap/model/write behavior, bound forward/reverse ownership lookups, and reject ambiguous or malformed mappings instead of selecting the first row.
- Preserve the existing success response shape for a unique legacy link, an existing workspace without a legacy link, and a confirmed no-match. Database failure is an error, not a negative lookup.
- Have existing frontend consumers validate the response and handle lookup failures explicitly. Recovery must preserve the selected event and offer retry without bypassing an ambiguous lookup or silently becoming “no athlete.” Keep account/event cancellation and existing response compatibility.
- Recovery review exposed retained outreach state and an onboarding browser cache with no account owner. Scope Quick Scan and outreach sessions to the current identity, use the existing caller-authorized workspace response for outreach fields, and suppress delayed copy/log continuations after an account change. Leave unrelated onboarding and outreach delivery behavior for separate work.
- Run relevant offline route and actual-component tests, TypeScript, independent review and source-preservation checks. No model calls or old allowance resets are needed.
- Trace junior entry, existing-account and family-switching behavior through Fable's current source bundle. Record what can be confirmed with Joey's own account and the precise remaining evidence needed for real guardian/child ownership. Do not fabricate a policy or impersonate a junior athlete.
- Write a dated handoff, update current state, and list uncommitted changes.

No production data/configuration change, deployment, new account, schema migration, guardian delegation, token mint/redeem, provider call, message, commit or push is authorized by this contract. The full app must not be started against production databases for verification. Pure synthetic tests and source inspection do not establish deployed-route or live junior acceptance.
