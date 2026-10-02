# Computer-use roadmap (OpenAI Agents API) — 2026-10-02

Joey 2026-10-02: liked idea 2+3 (spec'd first), idea 4 (film import) and the GMTM ideas 5-7. Each gets its own spec
file after the first spec passes Fable review and phase 0 measures real cost and accuracy. Fable reviews each spec;
no Codex. Shared rails for all: per-origin allowlist answered by code, no stored screenshots, measured cost before any
batch, first failed paid attempt = stop and report.

| # | Idea | Who | Data out | Key design notes | Gate |
|---|------|-----|----------|------------------|------|
| 2+3 | College research (camps + team now) | Athletes | None | Spec: college-research-agent-2026-10-02.md | Phase 0 cost + accuracy |
| 4 | Film import (Hudl, YouTube) into GMTM | Athletes | Her own sign-in to her own account | The athlete starts it and types her password in OpenAI's `browser_authentication` box (values never reach the model; 5-minute expiry; no passkeys/QR). Agent lists her clips, she picks, files land in GMTM storage under her account. Minor + third-party account = parent notice update first. Check each site's terms on automated access before build. Prefer an official export/API where one exists (YouTube links already work in GMTM). | Joey + parent-notice wording; terms check |
| 5 | Coach contact refresh | GMTM ops | None | Same per-program job as 2+3; adds staff-page check. Changes go to a review queue, not straight to athletes. | After 2+3 is live |
| 6 | Daily GMTM.com walkthrough tests | GMTM ops | A dedicated test account only | Signed-in flows on gmtm.com and sparq.gmtm.com with a test account (never a real athlete). Report to Fable/Joey; no fixes by the agent. | Test account from Joey |
| 7 | Club/federation event leads | GMTM sales | None | Read-only lists of upcoming combines/events from public sites into a sheet for Front Office. No outreach by the agent. | Joey names target sports/regions |
