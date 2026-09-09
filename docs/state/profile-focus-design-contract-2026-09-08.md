# Focused athlete workspace — completion contract

Joey's current correction: too much text; simplify the interaction and elevate the design. This continues the existing profile product in the current Codex checkout. The existing black/lime brand and source-backed behavior remain the foundation.

## Outcome

An athlete reaches the question and Ask SPARQ in the first phone viewport, receives a clear takeaway with one next action, and can open a dedicated text editor. Profile records and source explanations are available on demand rather than competing with the question. Do not fabricate athletic potential, scouting, film analysis or opportunity data to make the screen attractive.

## Interaction contract

- Compact identity and View profile control; records open in a native modal sheet with keyboard dismissal and focus restoration. Opening/closing it does not reload data or call AI.
- One focused question surface, three intent starters, explicit Ask SPARQ. A starter selects the intended focus and fills a useful editable question without submitting.
- A successful answer collapses the form into its actual question and an Edit question control. Keep actionable uncertainty visible; supporting observations, action reasoning and sources remain accessible on demand.
- A local answer action or manual writing entry opens a dedicated composer. Preserve answer, selections and draft when moving between views. Rebuilding remains explicit; Copy uses the athlete's exact edited text. Draft details collapse after generation.
- Preserve account-key resets, cancellation, request limits, strict response parsing, error recovery and stale-answer action guards. No server contract changes, provider calls, production reads, sharing or deployment in this slice.

## Verification

Adapt existing component and actual-app checks to exercise disclosures, keyboard/focus, draft preservation, no automatic requests, stale answers and account isolation. Inspect actual compiled-app desktop and 390px phone initial/answer/editor/sheet states. Ask must be within the first 844px phone viewport, and hidden tools must not remain keyboard reachable. Run finite supervised browser/production checks serially and retain owned process/port cleanup evidence. Write a dated handoff and update current state before the local checkpoint.
