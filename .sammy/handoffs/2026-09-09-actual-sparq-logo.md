# Actual SPARQ logo — 2026-09-09

Owner: Codex, existing SPARQ checkout and `codex/athlete-home-first-value` branch. Started from clean `d11d686007816de0252e411cf220737ea1ca6a98`. Joey supplied `/Users/joey/Desktop/Sparq black.png` and asked to use the actual logo.

## Change

- Copied the original transparent 3266 × 547 PNG unchanged to `frontend/public/sparq-wordmark.png`. SHA-256: `70650e3513e3682bebf2dce06d3a21dd164fa7756f560aa1f54892870d3585f0`; 37,163 bytes. Visible pixels are black; alpha is preserved.
- Shared `SparqLogo` uses the asset at its natural aspect ratio. CSS `invert` renders white on the existing charcoal backgrounds; no image regeneration, pixel editing, crop or stretching.
- Replaced the career header's typed wordmark and the old square image on sign-in, sign-up, connect, claim landing/error and claim redemption screens. Header Home label/action is unchanged.
- Added only the exact new PNG to the restricted public-asset allowlist. GET/HEAD-only behavior and other route restrictions are preserved.
- Updated the existing component harness's source bundle, PNG MIME and asset hash so it can load the shared component. No new test cases or application dependencies.

## Verification

Seven TSX files transpile syntactically, the maintained component harness passes `node --check`, and whitespace checks pass. Fresh verification artifacts are in sibling `sparq-logo-2026-09-09/` outside Git:

- Existing route policy: 103 checks passed (`policy.json`).
- Actual Next/ASGI app: 118 checks plus five safety assertions passed (`app/receipt.json`). Browser errors and unexpected Node network denials are empty. Expected remote-font requests remain blocked.
- Real Next production compile/typecheck/start, with real Clerk packages and synthetic configuration: passed (`production/receipt.json`). No source drift or denied network attempts. Both test supervisors exited successfully, all their owned process groups died, and their ports closed.
- All 133 frontend source hashes match both runs, including the exact new asset and shared component. The component harness was syntax-checked, not rerun; earlier 311-check results are historical, not a fresh result for this logo change.
- Original artwork and actual desktop/phone renders were visually compared. The exact white silhouette is clear at the header's 112/128-pixel widths, without a box, distortion or crop. The in-app 903 × 804 preview also confirmed the 168-pixel shared sign-in logo; its authentication controls are synthetic. The connected-account route correctly returned this fixture to Home.

The new finite synthetic preview is recorded in `../sparq-career-home-build-2026-09-09/preview-04/ready.json` (URL `http://localhost:63549/home/inbox`). It is retained in the in-app browser for Joey, automatically stops within ten minutes, and saves only for this fixture session. Preview03 was already stopped with confirmed owned group/port cleanup before verification. The production workspace implementation has not been applied to real accounts.

Local checkpoint only. The exact commit and clean-tree receipt will be recorded outside Git in `../sparq-logo-2026-09-09/commit-receipt.json`. Next product action remains Joey's journey feedback, followed by the separately bounded real-account acceptance and Agent schema preparation.

No backend code, database, provider, live identity, deployment, push or infrastructure change. Inactive legacy/marketing/combine-specific headers retain their existing branding; this slice covers the active athlete career experience and its shared account/connection path.
