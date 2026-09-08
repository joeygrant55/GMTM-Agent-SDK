# Engineering lead adoption and first Fable review cycle

September 7, 2026 Eastern. Joey asked Codex to lead builds, spec/review Fable's work, obtain its codebase context and steer execution toward the overall product direction. This pass establishes the working arrangement, initial build overview and first completed technical review cycle. It does not claim completion of all products or activation of unattended work.

## Adopted arrangement

Codex leads engineering priorities/specification/integration/review; Fable provides platform context, independent review and approved assigned execution; Sammy/Hermes supports durable cross-machine reconciliation. Existing live writers keep their worktrees until explicit handoff. The [local execution contract](../../docs/state/engineering-lead-contract-2026-09-07.md) and [shared MacBook decision](/Users/joey/clawd/docs/strategy/codex-engineering-lead-2026-09-07.md) preserve all standing production/financial/external-action boundaries.

One new native message to GMTM requested readback and a current work/source inventory. [Fable's response](../../../sparq-engineering-lead-2026-09-07/fable-engineering-readback.md) explicitly acknowledges the arrangement, retains its current infrastructure/core execution lane and supplies current tasks and maps. It distinguishes Joey's actual approvals in its own session from the peer message. No other portfolio session or mini adoption is implied.

The MacBook Control Tower source update changes only five files: a new dated role decision, narrow pointers in the existing operating contract/state/NOW, and a dated handoff. Six AGENTS/CLAUDE/global-template sources were protected unchanged. The first apply attempt stopped before writes because Fable concurrently advanced Control Tower HEAD from `fe2691a` to `e0cc1f7`; all five target files still matched their preconditions. Updating only the expected HEAD allowed the same reviewed packet to apply. Existing concurrent work was preserved. No global configuration sync, queue, scheduler, path move, commit or push occurred from Codex.

## First completed review: PR 73

The [review](../../../sparq-engineering-lead-2026-09-07/pr-73-review.md) records no blocker for the narrow `removeChildAccount` ownership fix. Live GitHub metadata verified open [PR 73](https://github.com/gmtmsports/gmtm-api-v2/pull/73), exact head `c5628bea43a1e5a2019ba6edd4d055bf799f3757` and one changed resolver file. Root independently proved committed function equivalence to the reviewed candidate. Fable's real-MySQL receipt and harness received independent read-only review: 14 checks passed (target + 12 groups + cleanup).

The verified evidence is narrower than an HTTP/app acceptance pass: response errors are body codes under HTTP 200; sessions/responders are injected; Redis/Fastify/PM2 paths and stale sessions were not tested. Concurrency observed the correct winner/loser outcome without forcing the lock interleaving. The completed run cleaned its synthetic rows. None is a blocker to the narrow code review. Root did not execute the harness or operate AWS.

A second bounded peer request returned that review and the dated Railway-host correction to Fable. [His acknowledgment](../../../sparq-engineering-lead-2026-09-07/fable-pr-73-review-ack.md) accepts the corrections and reports moving harness setup under cleanup protection. Independent review verifies that edit but identifies a remaining `process.exit` in `finally` that can suppress setup/test failure, plus sequential cleanup that can skip later attempts. The saved 14-check receipt remains valid; a small proposed correction is requested before another run. Native delivery and actual acknowledgment are recorded in `work/sparq-engineering-lead-2026-09-07/relay-03-review/`. Neither is Joey's deployment decision.

The [remaining infrastructure spec review](../../../sparq-engineering-lead-2026-09-07/infra-spec-review.md) identifies memory-capacity, measurement-window and rollback/application acceptance gaps before recommending the proposed production resize. It also separates the temporary security-test restore, reconciles the old pre-prod inference and preserves the cost/approval gates. A third bounded peer request returned this review; [Fable accepted the findings and supplied document-only infrastructure and harness proposals](../../../sparq-engineering-lead-2026-09-07/fable-infra-review-readback.md). Proposed numbers still need workload evidence and the harness needs a concrete reviewed diff before reuse. Native receipt and response hashes are in `relay-04-infra-review/`. No new AWS measurement, mutation, database run or automatic continuation is authorized.

## Initial portfolio and product sequence

The [build overview](../../docs/state/build-overview-2026-09-07.md) distinguishes current local evidence from actual deployed/App Store status. Recasa's local evidence reports build 33 attached and awaiting final commercial/release decisions; Saintlings app has a branch/commit mismatch with an older ready-to-release handoff; Junie's release evidence is older; Profluence/Battle Rhythm remain registry-only intake. Existing owners/publishers were not interrupted or reassigned.

Next SPARQ packages: one supported adult-combine candidate; full athlete acceptance using the exact current source and safe test environment; then minimum cohort measurement and release packet. Fable's maps guide targeted contract/source verification. Avoid a whole-platform rewrite or a broad ownership sweep delaying the narrow production fix. Proposed adult-first pilot and actual public release remain separate decisions.

## Files and verification

SPARQ repo: added `docs/state/engineering-lead-contract-2026-09-07.md`, `docs/state/build-overview-2026-09-07.md`, this handoff, and updated `docs/state/current-state.md`. All prior application changes remain local/uncommitted in `codex/athlete-home-first-value`, HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`, origin `joeygrant55/GMTM-Agent-SDK`.

Sibling artifacts: `work/sparq-engineering-lead-2026-09-07/` holds the role packet, guarded source installer, prior source backups, Fable responses, frozen one-message relay packets and review evidence. Control Tower's five document updates remain local/uncommitted alongside its prior dirty work. Fable's separately pushed core PR is not a Codex push.

Verification includes unchanged SPARQ application hashes, applied Control Tower file hashes, protected instruction sources, local links, whitespace, relay recipient/message/count/cost and actual Fable readback. No application test suite, Agent model call, production probe, release, or old harness allowance reset is included in this pass. Final verification results are retained in the sibling `verification.json`.

Final preservation checks pass: all 170 captured SPARQ application files unchanged; five Control Tower documents match the applied packet; six protected instruction sources unchanged; both repo whitespace checks pass. All three current-turn native requests delivered once to GMTM and received response files. The couriers exited; other live portfolio sessions and Mac mini adoption remain unverified. New and updated documents/evidence remain local and uncommitted.
