# Reviewed opportunity shortlist — September 10, 2026

Status: implemented and verified locally, including the real owner-2 read-only browser flow. Local checkpoint only; no push or deployment. The exact commit will be recorded outside Git in `../sparq-opportunities-2026-09-10/commit-receipt.json`.

## Completion contract and ownership

Following Joey's instruction to proceed autonomously, implement the first bounded opportunity collection and connect a sourced contact to an editable athlete introduction. Preserve existing work, avoid a second combine checklist, show official evidence and honest unknowns, and validate the full journey before claiming readiness. Scope is the Codex SPARQ checkout, branch `codex/athlete-home-first-value`, starting `fe265c1a7e7b3da19bea64b39d5c3420e0dce6c1`, remote `joeygrant55/GMTM-Agent-SDK`. The initial tree was clean.

Root owns integration, verification and the checkpoint. Assigned agents supplied the opportunity component/parser, independent source research/tests and GMTM authentication map/review. No external agent checkout was edited; Fable retains GMTM work.

## Result

- New authenticated `POST /api/athlete/opportunities` resolves the exact Agent owner pair and link revision. It returns private/no-store data, makes two ownership SELECTs and no GMTM reads, model calls or writes. The profile route/policy/package and read-only acceptance wrapper include only this new endpoint.
- A bounded reviewed collection returns up to three supported options. Two are currently defensible: published USA Football adult Digital Combine 2 details and a public High Performance inquiry. The [source review](../../docs/research/athlete-opportunities-2026-09-10.md) preserves dates, costs, cycle ambiguity, unknown deadline timezone, public department contact and excluded stale/test sources.
- Athlete-selected adult flag category/format produces deterministic relevance. Dates and every material fact carry reviewed source references. Expired evidence and past events disappear; no fit scores, selected-athlete outcomes or inferred eligibility.
- Compact Opportunities cards, explicit filters/search, full-fact source drawer, retained results across navigation and honest in-person empty state. Uses the existing SPARQ styling and logo.
- Prepare introduction uses the saved goal, selected current evidence and eligible featured footage plus a program-specific question. Existing text, including an erased buffer, requires explicit replacement. Preparing never saves/copies/sends automatically. The generic GMTM return opens a labeled new tab so an unsaved draft stays mounted.
- [GMTM authentication map](../../docs/state/gmtm-auth-handoff-map-2026-09-10.md) specifies a separate one-use-code handoff and identifies missing delegated parent/child provenance. It is a reviewed source map, not a live or implemented SSO bridge.

## Review and verification record

Artifacts are outside Git in sibling `sparq-opportunities-2026-09-10`, `sparq-opportunities-build-2026-09-10-*` and `sparq-opportunities-app-2026-09-10-*`. Raw attempts are retained. No empty test result counts as a pass.

- Initial focused backend suite: **182 passed** (opportunities, candidate route/package, acceptance wrapper and launcher). After adding the read-only opportunity POST assertion, the affected opportunity/acceptance suites: **114 passed**.
- The read-only wrapper test verifies the new POST performs no source queries or commits and keeps PATCH cap/attempts zero.
- Initial component run: **347 passed**. Production build then exposed a case-insensitive module-name collision and an ES5-target regex literal error. Renamed parser to `opportunityEvidence.ts` and retained Unicode semantics using a RegExp constructor; did not change tsconfig or waive type checking.
- Second actual production build/typecheck/start passed with real Clerk packages, synthetic configuration, no auth overlays and no outbound denials.
- First actual Next + ASGI fixture journey: **137 checks passed**, including two records, exact source URLs, no implicit writes/models/evidence refresh, contact purpose and athlete footage, keep/replace draft, mobile layout and new-tab return. It is synthetic identity/SQL and a fixture-only freshness overlay, not real source validation or a production deployment.
- Independent review found the same-tab GMTM return could discard unsaved text. Fixed with labeled new-tab navigation and actual-app regression; re-review found no additional actionable issues. Review also covered stale/source guards, owner/link isolation, busy-state feedback and package/launcher closure.
- Visual review prompted compact mobile filters and contact facts rather than irrelevant empty date/place/cost rows; all five facts remain in the drawer. Component run 02 failed an old expected count of these repeated unknown rows. The assertion now requires the assessment's unknown cost once; final run 03 passed all **347 component checks**.
- Policy tests: **108 passed**. Initial invocation lacked the required dependency variable and did not run tests; corrected invocation is the accepted result.

Final verification: production run **03** passed compile/typecheck and unauthenticated same-artifact start; actual-app run **02** passed **137 journey checks plus five safety assertions**. Component run **03** passed **347 checks** and policy passed **108**. Final screenshots show desktop and 390-pixel phone cards/source drawers/introduction without overflow. All fixture/build/component owned groups are dead and ports closed; no outbound denials. Current frontend sources match all accepted manifests, the actual-app receipt verifies unchanged backend sources, and the real acceptance snapshot passes its offline hash check. See `source-reconciliation.json` in the sibling artifact directory.

## Real-owner acceptance and temporary preview

At 16:54 UTC, the actual Clerk session loaded Joey's owner-2 profile and existing saved version **3**, featured footage and goal. An explicit Opportunities search returned both current reviewed records. The High Performance source drawer showed the public department contact and exact official reference. Prepare introduction correctly opened **Keep your current draft?**; root chose **Keep my draft**. No real replacement, save, external link, provider or message action was performed. Browser error log was empty.

The receipt records **4 personal requests, 10 connection attempts, 24 SELECT attempts, zero PATCH attempts, PATCH cap 0, zero commits and no denials**. These are wrapper reservation counts, not wire-level database auditing. The founder run proves current identity/source wiring and safe exploration, not recruiting relevance or successful participant completion. New text generation/replacement is covered by the synthetic full-app journey.

`/private/tmp/sparq-opportunities-real-2026-09-10-01` owns the private snapshot/before-state and live ledger. Secrets were not persisted or printed. The browser tab is a deliverable at `http://localhost:64493/home/inbox`, showing Opportunities. The read-only frontend/backend are intentionally still running under their finite supervisor until **1:06 PM EDT September 10 (17:06 UTC)**. Their cleanup is not yet claimed; inspect `supervisor.json` and ports 64493/64494 after expiry. No other heavy job should overlap this live preview. Never reuse or reset its ledger. Count-only `live-readonly-receipt.json` is in the sibling artifact directory.

## Boundaries and remaining work

No deployment, push, GMTM mutation, outreach, registration, payment, provider call, AWS change or new save allowance. The prior three-save live allowance remains exhausted. Any current founder acceptance uses read-only mode with PATCH cap zero.

This is a reviewed collection, not autonomous web discovery or personalized recruiting advice. Sources expire September 17, 2026 at 16:30:06 UTC unless re-reviewed; no recurring freshness process was activated. No upcoming adult in-person event was confirmed in this bounded research. No wider market absence is claimed. A combine entry is reference context for existing participants, not an instruction to repeat submission.

Results/selected opportunity are not persisted across full reload. Prepared text can use the existing explicit Save draft; generic Rebuild may replace the specific program question. No multiple-draft or automatic sending feature was added.

Next product work: richer goal/eligibility/location/travel constraints and bounded discovery of more genuinely useful current opportunities behind this evidence contract. Next integration work: confirm current GMTM serving commits and Clerk bootstrap capabilities with owners, then implement and test the narrowly specified authenticated entry. Founder read-only acceptance is not genuine participant GMTM-save-to-SPARQ-refresh proof or paid demand; those require the adult pilot and release gates.
