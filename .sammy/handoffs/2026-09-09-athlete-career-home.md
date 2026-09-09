# Athlete career home — local implementation handoff

Date: 2026-09-09. Owner: Codex, existing SPARQ lane. Checkout: `/Users/joey/Documents/Codex/2026-09-04/higgsfield-plugin-app-6a3293e129088191abf0875820e839da-openai-curated/work/sparq-agent-review`. Branch: `codex/athlete-home-first-value`; remote: `joeygrant55/GMTM-Agent-SDK`. Started at `bd7fcc9de87a9f0fea67fdd6e0b82a4305aceba4` with a clean tree. Local commit receipt is retained outside Git in sibling `sparq-career-home-build-2026-09-09/commit-receipt.json` after the checkpoint. No push or deployment.

## Accepted slice and resulting behavior

Joey chose the first portfolio-first concept with stronger personal identity from the third. A combined selected visual was displayed before code. See the [completion contract](../../docs/state/athlete-career-home-design-2026-09-09.md) and [design QA](../../design-qa.md).

- Home foregrounds actual eligible footage, athlete identity, up to two recorded/submitted results, a chosen goal and one useful next action. Missing posters/source records have honest states; no generated image enters the production fallback.
- Goal, featured source reference and exact authored draft save explicitly to an owner-bound Agent workspace. Reload restores them. Recent work lists actual saved/removed events, not athletic improvement or coach interest.
- Next action resumes a draft, asks for a missing goal, opens an introduction when a recipient is supplied, or opens a summary. Preparing text is deterministic and explicit; AI does not run on arrival or saving. Ask SPARQ retains its separately gated debrief.
- Portfolio opens deeper source details on demand. Opportunities is explicitly unreviewed; Progress shows saved work. No redundant digital-combine checklist was reintroduced.

## Storage and isolation

New query-free profile-only GET/PATCH workspace route; Agent table preparation is separate and dry-run by default. No live schema was applied. GMTM remains the canonical read-only source; no profile/media snapshot duplication.

Exact forward/reverse ownership checks, row locking, link revision and optimistic version checks protect saves. Changes preserve omitted fields; no-op writes create no event. A feature change revalidates an existing eligible public source and rechecks ownership inside the write transaction. Saved goal/draft recovery does not depend on GMTM availability.

Evidence/materials/workspace/debrief carry comparison-only owner tags that never enter model context. Mismatched or unlinked sources clear old authored data; ordinary source outages preserve it. Direct profile/material comparison also works when saved storage itself is unavailable. Account changes remount private state. Save errors, uncertain timeouts and version conflicts preserve local edits and require explicit reconciliation; loading a competing saved version never silently replaces typing.

## Verification and exact receipts

Artifacts are sibling directories outside the checkout; no private data or generated media were added to Git.

| Verification | Result | Receipt |
| --- | --- | --- |
| Full backend suite | 1,092 passed | `sparq-career-home-backend-2026-09-09/backend-04.log` and `.supervisor.json` |
| Component/browser journey | 311 checks passed | `sparq-career-home-build-2026-09-09/component-06.json` |
| Candidate route policy | 103 checks passed | `sparq-career-home-build-2026-09-09/policy-01.json` |
| Actual Next/ASGI browser journey | 118 checks + 5 safety assertions passed | `sparq-career-home-app-2026-09-09-06/receipt.json` |
| Actual production build/typecheck/start | passed; real Clerk packages, synthetic config | `sparq-career-home-production-2026-09-09-02/receipt.json` |
| Current source reconciliation | no changed inputs | `sparq-career-home-build-2026-09-09/final-source-reconciliation.json` |

All heavy checks ran serially under finite external supervision. All owned verification browser/Next/backend groups and ports closed. Final actual-app run used one synthetic debrief, zero real providers and 11 synthetic workspace commits; all synthetic connections closed. Browser errors and Node network denials are empty. Ten expected font stylesheet requests were blocked in the browser; no unexpected denial was waived. Production compile/start used no auth overlay and verified an unauthenticated Clerk redirect plus route boundaries. This is not signed-in production acceptance or a deployment artifact.

Earlier failed runs remain retained: blocked initial Chromium startup, obsolete/ambiguous harness selectors, and a backend response-whitelist mismatch fixed before the passing suite. A first root reconciliation used the wrong component path prefix; corrected reconciliation confirms all bytes match. None of these failed attempts are counted as passes.

Independent review covered storage/ownership/schema guards and frontend concurrency/link isolation. The final found profile/material mismatch under unavailable saved storage was fixed and received two regression cases. Design comparison at 1487 × 1058 and phone 390 × 844 resolved duplicate padding, narrow frame, clipped poster focal point, weak CTA and cramped recent work.

## Interactive preview

Final preview03 was inspected in the Codex in-app browser at 903 × 804 and retained as a deliverable: `http://localhost:62720/__sparq-preview/start`. Goal and featured-footage saves were verified, then restored directly after reload with no browser error/warning entries. The primary summary action remains fully visible. Earlier preview02 also exercised preparation, draft save and exact saved-draft recovery; one reload showed a recoverable source-load error and Try again restored the profile. That transient was not explained or counted as an uninterrupted pass; it did not recur in preview03's reload. Formal app06 verifies the complete journey separately. See [visual QA](../../design-qa.md).

The external `sparq-career-home-build-2026-09-09/preview-launcher.cjs` requires a passed current app artifact, verifies source hashes and copies an immutable external snapshot. It supplies synthetic Clerk/SQL/AI plus a visible sample banner, local test poster and local explanations for external source links. Saves last only for that fixture session. No live credentials are inherited. Its parent/worker supervision stops only its owned group within ten minutes and records cleanup; the worker also terminates its own group on supervisor disconnect. Preview03 readiness/ownership and eventual cleanup receipts are in its sibling build directory. Do not treat its ready receipt as a later health/cleanup result. This is the only local preview intentionally running at handoff; earlier previews and all formal verification groups/ports were confirmed closed.

The launcher was independently reviewed, including external-link isolation and worker cleanup if its supervisor dies. A runtime-only origin adjustment aligns browser/token/CORS to localhost for the embedded browser while both servers still bind 127.0.0.1. The exact backend fixture overlay and source hashes are retained outside Git. No product allowlist or authentication was weakened. This launcher is local test infrastructure, not production code or a persistent service.

## Remaining work and boundaries

1. Joey's usefulness feedback on goal, featured portfolio, preparation and return to exact saved work.
2. Bounded real-account acceptance and separately reviewed Agent table preparation; current MySQL behavior and real Clerk/CDN/media loading are not verified by the synthetic app.
3. Application-model quality remains unverified. The earlier eight-case finite allowance is still unanswered; no real application-model call was made in this slice. No film analysis or scout/private-outcome inference.
4. Reviewed opportunity sources, durable provider quotas, profile release packaging and a small athlete willingness-to-pay experiment remain follow-on work.

Fable retains GMTM infrastructure/security and Audit retains cross-machine organization. No AWS/RDS/IAM/API deployment, production data change, external message, outreach or release is included. Existing combine behavior remains covered; new workspace routes are unavailable on that surface.
