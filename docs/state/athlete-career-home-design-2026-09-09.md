# Athlete career home design and first-build contract

Date: 2026-09-09. Status: product direction accepted; three visual concepts displayed; visual selection pending. No application implementation in this design turn.

## Product decision

Joey accepted a full private athlete career home focused on their featured portfolio, chosen goal, one useful adaptive next move, and real continuity. This develops the September 8 [profile-value direction](profile-value-direction-2026-09-08.md). It supersedes treating the introduction composer or a second combine checklist as every athlete's default next action.

The home should make existing work feel valuable and help the athlete use it toward a goal. The core return-visit promise is: my goal, featured work and unfinished work are still here, and the next action is relevant. Long explanations, source details and questions open on demand.

## Evidence and boundaries

Current local application baseline is commit `5d54cd195d26a50b1dff24edde7b1145741add32` on `codex/athlete-home-first-value`. It already has bounded public-source footage previews, eligible film-reference selection, existing results, an editable introduction/summary and a gated debrief. Goals and drafts are not durably saved.

A public desktop inspection of [Blake Boswell's GMTM profile](https://gmtm.com/athletes/1392317/blake-boswell/feed) showed substantial footage across Feed/Media, six dated public stats, and an empty Career section. This was public-profile evidence, not signed-in owner acceptance, verified measurements, trend analysis, film analysis or scout outcomes. The design should make that existing material useful without asking athletes to reconstruct their combine.

Source captures and audit are retained outside Git in sibling `gmtm-athlete-design-audit-2026-09-09/`. The inspected current local SPARQ sample screen is in sibling `sparq-media-app-2026-09-08-04/desktop-initial.png`.

## Visual record

Three independent ImageGen concepts were displayed once, in this exact order:

| Displayed choice | Direction | Retained file |
| --- | --- | --- |
| 1 | Athlete Studio | `01-athlete-studio.png` |
| 2 | Next Chapter | `02-next-chapter.png` |
| 3 | Athlete Story | `03-athlete-story.png` |

Files, exact prompts, attached reference paths and SHA-256 hashes are retained outside Git in sibling `sparq-career-home-design-2026-09-09/manifest.json`. Original generated files are preserved. Target desktop dimensions were 1440x1024; actual images are 1487x1058 and have not been stretched.

All concepts use fictional Ava Reed data and generated sports imagery, with a sample label. They preserve the existing black/lime SPARQ identity while varying hierarchy and composition. Generated durations, playback controls, saved states and navigation are design proposals, not evidence of current features. In implementation, omit unknown runtimes; offer playback only for a supported real media source; never use sample imagery as an athlete's fallback. A profile view or copied draft must never imply coach interest or outreach sent.

The Product Design ideation workflow requires visual selection before implementation. The next selected choice must resolve to the displayed order above. Combining choices or selecting with refinements calls for a revised visual before code. Build in the existing owned SPARQ checkout; a design exploration does not authorize a new app, deployment or service.

## First-build completion contract

This is the proposed next implementation slice, to finalize after visual selection.

1. **Chosen goal:** one editable, persistent goal in the athlete's own words, with optional target recipient/program and timeframe. Do not infer eligibility, division or recruiting intent. Keep the goal visible outside its editor.
2. **Featured work:** explicitly feature one eligible existing clip. Persist the source reference and revalidate ownership and availability on restore. Preserve truthful missing/broken-poster states. Featuring on the private home does not publish or change GMTM.
3. **Useful next move:** use explainable deterministic rules first. Resume an unfinished draft; prepare an introduction when a recipient and relevant evidence are known; use an appropriate reviewed pathway when available; otherwise clarify intent once. Show a short reason and a working action. Do not run AI on load or send every athlete into coach outreach.
4. **Opportunity honesty:** distinguish not reviewed, needs refresh, and an actual reviewed result. Real recommendations require sources, checked date, eligibility information and current deadline/status. Do not display invented matches, empty counts, invites or closed camps as open. A truthful unreviewed state is sufficient for the first slice.
5. **Recent work:** record only supported product events such as a saved draft or featured source. Copy success is not sending; profile viewing is not applying; saving a goal is not athletic improvement. User-reported outcomes remain labeled. No invented streaks, readiness score, ranking or selection probability.
6. **Owned saved state:** persist goals, featured source references, working drafts and bounded activity only in the Agent database. GMTM remains canonical/read-only; do not duplicate profile/media snapshots. Resolve the current owner on the server. Include explicit save/remove, visible errors and conflict handling. Account or linked-athlete changes must not restore another person's data; source failures must preserve authored drafts without claiming freshness.

### Acceptance

The same athlete can reload and recover the goal, featured source and exact edited draft; change the goal without losing edits; safely switch accounts; recover from a save or source failure; and complete one useful output on desktop and phone. Every visible primary action works. A suggested action is not measured as a completed outcome.

Run source, isolation and complete-journey checks proportionate to the change, under the existing finite verification and cleanup contract. Synthetic checks do not establish live signed-in acceptance, model quality or willingness to pay.

### Sequence

1. Select/refine the visual.
2. Specify and implement owner-scoped private saved-state schema/API in the isolated Agent environment.
3. Implement the chosen responsive home and persistent editor, reusing current source adapters.
4. Add deterministic next-move behavior and honest recent-work states.
5. Verify an actual athlete goal-to-useful-output journey within a separately scoped live acceptance run.
6. Later: reviewed opportunities and attributable outcomes, then a small willingness-to-pay experiment.

Do not add a social feed, broad opportunity crawler, video analysis, automatic outreach or private scout data in this slice. Current pending application-model evaluation authorization, release packaging and real thumbnail acceptance remain separate. Fable's infrastructure/security and Audit's machine organization lanes are unchanged.
