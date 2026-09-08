# Goal-based profile debrief

Joey approved continuing from local `bb2871c`. Codex owns the current SPARQ lane. Build one explicit AI debrief answering an athlete's question, using current owner evidence and reviewed official pathway facts, then recommend one concrete action. The first curated program is USA Football's adult pathway. Other tracks support profile understanding and an introduction for a recipient the athlete already knows; this is not a broad opportunity search.

## Product and API contract

`POST /api/athlete/debrief` exists only in the explicit profile surface. Request is exactly `{track: "national_team" | "profile" | "outreach", question: string}` with a trimmed nonempty question of at most 1000 characters. No athlete ID, pasted profile, source text, model, URL, caller history or arbitrary action is accepted. Query parameters are rejected.

The server resolves the strict forward/reverse owner link once, then loads existing identity/measurement/material helpers for that same owner and closes all connections before model use. No new SQL or live source path is added to the adapters. A fresh source failure prevents a model call; it is not an empty-profile claim. Debrief admission holds a timed-out SQL worker's lease until that worker actually finishes, so retries cannot accumulate source work. One request per actor is in flight; per-process rate and call/concurrency caps are finite. Durable multi-worker limits remain a release gate.

Provider context contains the athlete's question/track, numbered supported numeric facts, generic footage-record facts/dates/counts, explicit coverage limitations, concise reviewed official facts, and server-defined allowed action IDs. Omit names, contact information, location, school, DOB, Clerk/GMTM identifiers, private/ineligible materials, footage titles/descriptions/URLs, raw answers and scout records. The UI may display separately resolved original source labels and canonical public links. Text is untrusted quoted data, not instructions. No film is downloaded, played or analyzed.

Use one buffered model call, no tools, fallback or hidden retry. Do not render any model text until the complete response passes strict JSON/schema and reference/action validation. The model returns:

```json
{
  "answer": {"text": "...", "refs": ["f1"]},
  "insights": [{"text": "...", "refs": ["f1"]}],
  "unknowns": [{"text": "...", "refs": ["coverage"]}],
  "action": {"id": "prepare_summary", "reason": {"text": "...", "refs": ["f1"]}}
}
```

Each paragraph is at most 700 characters with 1–6 unique refs from the request's server registry; answer is required, insights 0–3 and unknowns 0–2. Exactly one allowed action. Text cannot add clickable destinations; URLs and email addresses are server-only source/action fields, never accepted from model text. Schema/ref validation does not prove semantic entailment; evaluate unsupported benchmarks, film-content claims, selection certainty and irrelevant advice separately.

Response is exactly `{state:"ready", track, question, answer, insights, unknowns, next_action, references, fetched_at}`. Paragraphs retain `{text,refs}`. `next_action` is `{id,kind,label,href,reason}`, with kind `prepare_summary|prepare_introduction|open_source`; `href` is null for local actions and an exact reviewed official HTTPS source for external actions. `references` resolves opaque IDs to `{id,kind,label,detail,href,checked_at}`; kind `evidence|coverage|official`, nullable href/date. Only referenced facts and the selected action's official source are returned. The UI renders escaped text and explicit plain anchors, never model HTML/Markdown or prefetching links.

The primary panel accepts the track and actual question and submits only on Ask SPARQ. Show the answer, up to three observations, material unknowns and one action; sources are expandable. Keep manual text preparation available. An action can open the existing composer with eligible existing facts; it cannot overwrite edited text without an explicit rebuild. Source/account refresh cancels and clears private debrief state. Question/track changes mark an old answer stale; errors preserve the old answer as belonging to the earlier request and leave the profile/composer usable. No persistent conversation or automatic follow-up.

## Model and source boundaries

Separate `PROFILE_DEBRIEF_ENABLED`, `PROFILE_DEBRIEF_MODEL`, `PROFILE_DEBRIEF_MAX_MODEL_CALLS`, `PROFILE_DEBRIEF_MAX_CONCURRENT_CALLS` configuration and ledger; disabled unless explicitly enabled with finite positive limits. Reuse the reviewed provider transport with an injected ledger, preserving combine defaults. Model choices remain the existing server allowlist, default Sonnet. This does not renew the earlier combine test allowance. Initial implementation verification uses synthetic provider responses and SQL only. A later live model evaluation needs its own concrete minimized prompts, finite allowance and durable receipts; no real athlete data is sent under this build contract.

Official pathway facts are curated, dated and expire. On expiry the national-team debrief fails with a specific source-refresh message rather than serving an old opportunity. The September 8 source review found no verified upcoming adult camp or 2027 Trials date. Do not repurpose closed 2025/2026 camps, historical selection procedures, junior invitations or an unavailable nomination form into current adult recommendations. Review support is an official published contact route, not a privileged recruiting channel. No booking, payment, message or source refresh is automatic.

## Verification and finish

Use proportionate behavioral tests for source ownership/minimization, strict model output, source expiry, admission/timeout/cancellation, unknown references/actions, model-disabled/error behavior and current-source citations. Extend the current bounded component/full-app journey for explicit submit, errors, stale accounts and action-to-composer behavior. One heavy job at a time with the existing external supervisor and verified process/port cleanup. Review actual desktop/phone screenshots. Record real-model quality separately from fixture mechanics, then write current state/handoff and make a local commit. No push, deployment, production mutation, live database read, provider call, infrastructure change or outreach is implicitly added.
