# GMTM research intake and reconciliation — September 6, 2026

Joey supplied `~/Desktop/gmtm-code-research/` and explicitly requested Astra be pointed at it. A bounded GPT-6 Astra read-only reviewer consumed the architecture documents while root compared them with SPARQ and verified selected core source. No separate Codex app conversation was created, no external message was sent and no application code was changed.

## Owner and preserved scope

Existing task `Evaluate Sparq agent project`, `01a06f58-7203-7f82-a090-3545f126936b`; owned checkout `work/sparq-agent-review`; branch `codex/athlete-home-first-value`; HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`; origin `joeygrant55/GMTM-Agent-SDK`. Existing uncommitted implementation remains in place. Core checkouts and the research folder were only read. No RDS/IAM/parameter-group, account, production data, deployment, billing or notification operations occurred. No environment exports or secrets were opened.

## Results

See [platform reconciliation](../../docs/state/gmtm-platform-reconciliation-2026-09-06.md) for the reuse/integrate/build/unresolved matrix, source evidence and next decisions. An output copy is at the task's `outputs/gmtm-platform-reconciliation-2026-09-06.md`.

The research establishes the main integration surface as API plus web, with existing profiles, media, scoring, communications and organization workflows to reuse selectively. The research is not a complete current adult/junior configuration contract and contains dated claims. Do not revive its historical pre-prod instructions or turn its platform cleanup list into this task's execution scope.

Three additional core resolver files were read through GitHub at explicit ref `1bf4fc0297d5eea56bed6bda54715f2f9c01593f`, without mutating local core branches. Root verified invitations/product access in event discovery, owner-scoped product checks, and coexisting parent/child representations. Frozen source and verification metadata live under `work/sparq-platform-reconciliation-2026-09-06/`; source at that ref is not live schema/behavior proof.

The current one-linked-athlete-per-Clerk restriction stays intact. Next discovery is the exact adult/junior events, requirements and actual junior account path. Do not unify two legacy parent relationship models or make both sufficient permission by assumption.

## Local uncommitted documentation changes

- Added `docs/state/gmtm-platform-reconciliation-2026-09-06.md` and this handoff.
- Updated `docs/state/current-state.md`, `docs/state/combine-adapter-source-map-2026-09-06.md` and `docs/state/sparq-combine-journey-plan-2026-09-06.md`.
- Added a task-output reconciliation and refreshed the task-output plan, with links resolved to actual sources.

Verification passed for this research-only checkpoint: three source blobs matched GitHub's blob identifiers at the explicit revision; seven documents/output copies passed local-link and whitespace checks; both output copies matched their source with links rebased; `git diff --check` passed. Evidence is in the task's `work/sparq-platform-reconciliation-2026-09-06/verification.json`. No application tests were rerun or live flows exercised. No commit/push/deploy. The earlier identity/data implementation receipt retains its original limited verification scope.
