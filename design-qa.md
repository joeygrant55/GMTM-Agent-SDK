# Athlete career home design QA — 2026-09-09

final result: passed

## Visual truth and capture

- Source: `../sparq-career-home-build-2026-09-09/selected-career-home.png`, 1487 × 1058 pixels, selected portfolio-first home with strong athlete identity.
- First implementation comparison: `../sparq-career-home-app-2026-09-09-02/desktop-career-saved.png` and `phone-career-saved.png`.
- Browser CSS viewports: 1487 × 1058 desktop and 390 × 844 phone, density 1. The first captures are full-page (desktop 1487 × 1192); the source depicts one desktop viewport. Comparison considered the corresponding first viewport; the next capture will retain an explicit viewport-only desktop image.
- State: signed-in synthetic athlete; saved goal “Explore college flag football,” no recipient; confirmed featured film; no draft; next action “Create my summary.” Actual source records remain synthetic test data, not a real athlete acceptance claim.
- Source and both implementation images were opened together in the same comparison input. The whole desktop design is legible at original size, including labels and actions; no separate zoom was necessary.

## Findings and first iteration

- **P2 — Duplicate top padding weakens hierarchy.** The athlete name begins around y144 and hero around y302, versus y97 and y238 in the reference. Removed the career-home's second top padding, reduced the outer desktop padding, and tightened the identity-to-content gap. This also moves the phone's main action further into reach.
- **P2 — Desktop frame is unnecessarily narrow.** The actual left edge is x103 versus x70 in the source. Expanded the existing shell to 1424 pixels and adjusted its columns to 1.8:1 so the portfolio remains dominant without squeezing the next action.
- **P2 — Center crop clips the athlete's head in the sample poster.** Changed the actual image fit to top-aligned cover, preserving the source's upper focal area. This is an image presentation change, not a claim of video playback.
- **P2 — Phone recent work forms an awkward narrow middle column.** Changed the mobile footer to a vertical stack while retaining the desktop row.
- **P2 — Main desktop action lacks the target's weight.** Increased its desktop minimum height, horizontal padding and font size while preserving a full-width phone button.
- Removed the passive “Previews only” line; the source link and explicit image semantics already distinguish a stored poster from playback. Alternative source tiles retain their concise selection instruction when actual alternatives exist.

## Required fidelity surfaces

- **Typography:** uses existing SPARQ display tokens. The isolated browser blocks external font loading, so the captured fallback is the tested baseline. Strong name and next-action hierarchy are present. Labels remain concise; the CTA was strengthened above.
- **Layout:** the identified padding, width and mobile footer fixes require a new capture before acceptance.
- **Colors:** existing charcoal/white/lime tokens preserve the chosen direction. Borders are subdued and the primary action remains the strongest color.
- **Images:** real source thumbnail rendering is used in app code; the synthetic harness supplies one permitted test poster. Missing media has an honest fallback. The fixture has one eligible film, so the two alternate tiles shown in the concept must be absent rather than fabricated. The top crop requires visual confirmation.
- **Copy/content:** fixture name, position abbreviation, film title and result labels reflect actual response data. No fabricated activity, opportunity result, measurements, coach interest or selection state appears. Unreviewed opportunities are accessible in their navigation view. Goal, featured state and recent work correspond to saved actions.

## Post-fix comparison

Source and the following revised screenshots were opened in the same comparison input:

- `../sparq-career-home-app-2026-09-09-05/desktop-career-saved-viewport.png` — exactly 1487 × 1058 pixels, CSS viewport 1487 × 1058, density 1, no scaling or crop normalization required.
- `../sparq-career-home-app-2026-09-09-05/phone-career-saved.png` — full-page phone capture, width 390 pixels; CSS viewport 390 × 844, density 1. The first 844 pixels are the initial visible region.

The saved-goal/featured-film/no-draft interaction state matches the target. Fixture content differs intentionally: one eligible source film, response-derived name/position and source labels. No fake alternate media or athlete facts were added to achieve a closer screenshot.

All first-iteration P2 findings are resolved. The athlete heading now begins near y100 and the left edge near x72; featured footage and the goal/action area align as one primary region. The image preserves the athlete's head. The desktop CTA has appropriate weight. The phone action ends around y831 inside the initial 844-pixel viewport; the recent-work list reads as a clean stack without a squeezed center column. No horizontal overflow, overlapping controls or hidden primary action was observed.

Typography, line wrapping, charcoal/lime tokens, poster sharpness, source labels and state-dependent copy were inspected in both full-size views. The existing `Space Grotesk / Inter / system-ui` stack is retained; the isolated capture uses system fallback because remote font requests are intentionally blocked. Identity and next-action hierarchy remain clear. The absence of decorative metric/activity icons and redundant arrow glyphs is an intentional use of the existing product's text controls, not replacement artwork. Standard focus outlines, native dialogs, real buttons/links, explicit labels and a 44-pixel minimum secondary hit target remain intact.

Residual P3 differences: small type/line-height differences from the generated reference, a slightly taller hero fitted to the actual source image, and more compact results because the fixture has only one eligible clip. These do not change the selected hierarchy or block use. Real-media focal points and loading with the production font remain separate live acceptance checks; the top-aligned fit is the conservative current default.

## Interaction evidence and remaining handoff gate

The final component run passes **311 checks**, including unavailable-storage ownership mismatch regressions. The final actual Next/ASGI browser run passes **116 checks plus five safety assertions**, including goal/feature/draft persistence across reload, exact edited-text preservation, explicit source selection, navigation, responsive controls, one buffered synthetic debrief and no real provider. Receipts: `../sparq-career-home-build-2026-09-09/component-05.json` and `../sparq-career-home-app-2026-09-09-05/receipt.json`. Browser errors and unexpected network denials are empty; ten expected remote-font requests were blocked. All owned test groups and ports closed.

### Narrow desktop follow-up

The actual in-app browser at 903 × 804 exposed one additional P2: below the old 1024-pixel column breakpoint, the wide one-column poster pushed the primary action out of the first viewport. Changed the existing home grid at 768 pixels to a 1.4:1 portfolio/action split with 24-pixel gaps; the large desktop 1.8:1 split and phone order remain intact. A matching 903 × 804 browser capture and explicit CTA/overflow checks are pending. No application data or action logic changed in this iteration.

The first production build passed with all owned groups/ports closed; the responsive-only change will receive a final build. The actual in-app preview confirmed goal/feature saves, local summary preparation, draft save and recovery. One reload displayed a recoverable source-load error while retaining the exact saved draft; Try again restored the profile and Continue my draft. Its cause was not established and the behavior is retained as an acceptance observation, not silently counted as an uninterrupted journey. Preview01 also exposed an isolated localhost/127.0.0.1 origin mismatch; the external launcher now uses one localhost origin for its synthetic authorized party, CORS and browser URLs while keeping both server binds on 127.0.0.1. No product origin allowlist was broadened. Preview01 and Preview02 were stopped with confirmed group/port cleanup before further verification.

The final narrow-desktop comparison opens the same selected source together with `../sparq-career-home-app-2026-09-09-06/desktop-career-saved-viewport.png`, `tablet-career-saved.png` and `phone-career-saved.png`. Desktop remains exactly 1487 × 1058; tablet is exactly 903 × 804; phone is the 390-pixel full-page capture at CSS 390 × 844; all are density 1. State remains the same saved goal, featured film and no draft. The tablet now places the CTA around y503–560, comfortably inside its first viewport, and has no overflow or overlap. Desktop and phone preserve the previously accepted hierarchy. All earlier actionable visual findings are resolved; only the recorded P3 type/crop/live-media polish remains.

Final post-tablet component verification passes **311 checks** and actual-app verification passes **118 checks plus five safety assertions**, including the new explicit tablet CTA/overflow checks. All owned test groups and ports closed, with no browser errors or unexpected network denials. Receipts are `../sparq-career-home-build-2026-09-09/component-06.json` and `../sparq-career-home-app-2026-09-09-06/receipt.json`.

## Final acceptance

The final actual production compile/typecheck/start passed at `../sparq-career-home-production-2026-09-09-02/receipt.json`; real Clerk packages, synthetic configuration, empty denials and closed owned groups/port. Current source hashes match backend04, component06, app06 and production02 receipts.

The corrected final preview (`../sparq-career-home-build-2026-09-09/preview-03/ready.json`) was opened and visually inspected in the Codex in-app browser at 903 × 804. Its visible synthetic-data banner, loaded source poster, new responsive split, saved featured footage and saved goal were confirmed. A fresh reload restored goal and footage directly with the primary Create my summary control fully visible; the earlier transient source error did not recur in this check. Browser warning/error logs returned no entries. The previous synthetic preview also exercised preparation, draft save and exact draft recovery, while app06 formally verifies the complete journey.

The tab is retained as a user deliverable. It is a finite local session with synthetic identity, SQL and model answers; its saves disappear when the supervised fixture closes. The production workspace implementation has not been applied to real accounts. No live athlete, database, model-quality or release acceptance is implied.

No actionable P0/P1/P2 visual finding remains. Follow-up is limited to the P3/live-media/type observations above and separate real-account acceptance.
