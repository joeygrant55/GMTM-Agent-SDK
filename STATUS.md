# SPARQ Agent — Status (Snapshot 2026-05-13)

## What's running in prod

- **Frontend:** https://sparq-agent.vercel.app (editorial landing + /demo + /onboarding + /home/inbox workspace)
- **Backend:** https://focused-essence-production-9809.up.railway.app
- **Model:** Claude Sonnet 4.6 (`claude-sonnet-4-6`) via Anthropic SDK. Tools: native `web_search_20260209` + custom read-only `query_database`.
- **Auth:** Clerk
- **Email send:** SendGrid via `backend/email_sender.py` (requires `SENDGRID_API_KEY` + `SPARQ_FROM_EMAIL`). If unconfigured, outreach approvals transition to `queued` instead of `sent` per outbound trust ladder.

## What's working

- **Landing & onboarding**
  - Editorial landing, scripted hero demo, bento features
  - `/demo` — streaming agent with tool-call feed, 3-question free gate
  - `/onboarding/search` — MaxPreps SSR scraping (dedup, parallel stat fetch, school colors)
  - `/onboarding/confirm` — MaxPreps stats, sport-aware
  - `/onboarding/welcome` — percentile + season stats + college count reveal

- **V2 cowork canvas** (shipped 2026-05-08)
  - `/home/inbox` — triage queue, replaces dashboard cards as the morning ritual
  - `/home/artifact/[id]` — artifact viewer with autosave, scopes the right-rail chat to artifact iteration (Mode B)
  - Dedicated artifact views: `OutreachDraftView`, `ResearchBriefView`, `HonestAssessmentView` (shipped 2026-05-13). `GenericArtifactView` is fallback for unbuilt types.
  - `WorkspaceAIPanel` Mode B — type-aware quick iterations ("Make it shorter", "Why this verdict?", "Push back on me") iterate the artifact in place via `iterate-via-agent`.
  - Backend artifact REST: inbox, badges, get, approve, discard, edit, iterate, iterate-via-agent, draft-outreach, seed-demo.

- **Outreach send loop** (shipped 2026-05-13)
  - `Approve & Send` on outreach_draft posts to SendGrid; reply-to set to athlete's Clerk email so coaches reply to the athlete directly.
  - States: `sent` (real send), `queued` (no infra configured — logged in outreach_log for manual send), `send_failed` (SendGrid/network error — retryable). UI shows inline notice for queued/failed.
  - Mirrors sent + queued outreach into `outreach_log` so `/home/outreach` reflects activity.

- **College matching (improved 2026-05-13)**
  - `ai_match_programs_sync` now uses Claude WITH the `web_search_20260209` tool, requires each program to include a `source_url` from search results, and drops any candidate without a plausible URL.
  - Source URLs are written to `college_targets.research_data.matching_source_url` for downstream provenance.
  - Sport+gender match still enforced via system prompt (Girls Basketball ≠ Men's Basketball).
  - **Caveat:** Web search reduces hallucinations but doesn't eliminate them — Claude can still cite plausible-looking URLs that don't truly verify a current roster. Phase 2 (below) hardens this with structured data.

- **Workspace + recruiting features**
  - `/home/colleges/[id]` — per-college deep research, "Draft outreach" CTA generates a real outreach_draft artifact
  - College matches tiered Reach/Target/Likely, Refresh Matches button
  - Workspace AI panel with session forking ("What If" scenarios)
  - Proactive AI prompts on Colleges page + per-college load
  - `/athlete/[id]` — public athlete dashboard with expandable college cards, terminal thinking feed, share cards
  - `/report/[token]` — shareable public reports with OG meta
  - `/quick-scan` — public athlete Quick Scan with waitlist capture
  - Enrichment worker — background Claude call generates `fit_score` + `fit_reasons` on profile creation

## What's known-broken / unbuilt

- **College matching: Phase 2** — current implementation relies on web search + URL plausibility. Hardened version: scrape the school's athletics site, confirm a current roster exists for the athlete's sport+gender. Or: integrate an NCAA member-institution + EADA dataset for structured filtering before LLM ranking.
- **Stripe / paywall** — not wired. Premium tier is aspirational.
- **15 of 17 agents from `AGENT_CAPABILITIES.md`** — not built (vision doc). Drafter, Analyst, Scout are the implemented three.
- **Video pipeline** — `video/` has Remotion installed but is not called by anything.
- **Inbound replies** — coaches reply to the athlete's email directly (SendGrid reply_to). SPARQ does not yet ingest or thread responses.
- **Coordinator / managed-agents orchestration** — Phase 3 vision. Today the agents are invoked one-off via specific endpoints, not by an orchestrating manager.

## Recently shipped (2026-05-08 → 2026-05-13)

- **2026-05-13** — Outreach send via SendGrid + queued/send_failed states + outreach_log mirror
- **2026-05-13** — Dedicated `ResearchBriefView` + `HonestAssessmentView` (V2 P2)
- **2026-05-13** — College matching uses web_search + source_url verification (replaces training-data hallucination)
- **2026-05-08** — Real Mode B wiring (`iterate-via-agent`) + on-demand `draft-outreach`
- **2026-05-08** — V2 cowork canvas (Inbox + artifact viewer + Mode B chat)
- **2026-05-08** — GenericArtifactView labeled-value bar rendering fix
- **2026-05-08** — Legacy GMTM users land in workspace, not /athlete/[id]
- **2026-05-08** — Public route list cleaned up

## Historical status docs

Pre-May snapshots are stale (model choices changed, features shipped). Do not trust them for current state:
- `PRODUCT_STRATEGY.md` — correct on vision/pricing, off by a model generation
- `AGENT_CAPABILITIES.md` — vision doc, not a status doc
- `PHASE1_IMPLEMENTATION.md` — February roadmap, not tracked
