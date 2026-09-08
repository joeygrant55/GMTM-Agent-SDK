# PR 73 release recommendation and separate portfolio decisions

September 7, 2026 Eastern. Joey asked what Codex recommends for deployment/infrastructure and how to handle workspace organization and possible Recasa/Saintlings lead transitions. Scope is read-only investigation, technical coordination and local decision documents. Existing production and paused-task approvals remain explicit.

## Results

- Fresh GitHub check: PR 73 OPEN/MERGEABLE/CLEAN at reviewed head `c5628bea43a1e5a2019ba6edd4d055bf799f3757`, no merge timestamp and no attached checks. The recommendation remains to prioritize this narrow security fix independently of RDS resizing. Prior isolated 14-check evidence was reviewed, not rerun.
- Fable returned a document-only deployment packet. Root and an independent reviewer identified unsafe guessed-ID production probes, a floating release revision and destructive-reset drift risk, dependency reinstall falsely described as a no-op, incomplete runtime resolution and an observation schedule not actually arranged. Review was returned directly for correction. Candidate code approval and approval of the deployment procedure are separate.
- Fable returned v2 and acknowledged all six findings. The main corrections are present. Final execution gates remain actual per-host runtime/environment and clean-state checks, exact merged-function equivalence, safe host-specific data/behavior verification and a timestamped error comparison with an actually attended window. Root's v2 assessment is appended to the local review for the next execution handoff; it has not been separately sent. No production preflight was dispatched, and no observed runtime success is claimed.
- Infrastructure review response already received; actual capacity/working-set/swap/peak/I/O evidence and a final application/rollback contract remain due before recommending resizing. Temporary `family-test` cleanup, stopped `pre-prod` snapshot/dependency/deletion gates and billing proof remain separate from the security release. No AWS call or new infrastructure action occurred.
- Live task lookup/read confirmed **Audit Mac and agent setup** (`01a071bc-3e8d-72a0-88a4-a8bd9f5b8d3e`) is not loaded, with a last completed read-only Claude-alignment docket. The existing plan and explicit pause were read. No resume/follow-up message was sent to that task.
- Recommend separate future Codex lead tasks for Recasa and Saintlings, preserving current writers until source/build/approval handoff. Joey's possible future transition is not present cross-session adoption. No new task, archive, move, schedule or product-owner reassignment occurred.

## Durable artifacts and verification

Added [decision brief](../../docs/state/release-infra-and-portfolio-next-2026-09-07.md), this handoff, and a narrow newest section in `docs/state/current-state.md`. Sibling `work/sparq-next-decisions-2026-09-07/` contains native relay packets, Fable replies, deployment-plan review and `verification.json`. Request 05 asked for a release packet; request 06 returned the review. Each courier is a single bounded native ListAgents/SendMessage delivery to existing GMTM; no approval is forwarded and each exits after delivery. Receipt/response hashes and actual delivery/readback states are in those manifests.

SPARQ remains in `codex/athlete-home-first-value` at `6c7e649ce5154f211401ed2e4af03d9691366194`; no app code edits/tests, source-branch changes, commit, push or deployment in this pass. New/updated local docs and sibling evidence are uncommitted alongside existing dirty work. Verification checks the 170 captured app hashes, prior Control Tower/protected instruction sources, new document links, whitespace and native request/receipt identity. The prior turn's frozen evidence is not rewritten.

## Next authorized work

Finish reviewing the corrected deployment packet and resolve safe preflight gaps before execution. Joey decides production deployment and recovery authority. Continue the adult-combine candidate in the current product lane. The other recommendations await their own explicit resume/transition request; do not infer it from this handoff or restart the older organization queue.
