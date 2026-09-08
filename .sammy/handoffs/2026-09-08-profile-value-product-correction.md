# Founder correction: prioritize athlete profile value

Date: September 8, 2026. Owner: Codex in Evaluate Sparq agent project, existing `work/sparq-agent-review` checkout, branch `codex/athlete-home-first-value`. Clean starting HEAD: `15b3fd9746c1ece359ee45d46691b54ad133d578`. No ownership transfer.

## Decision and result

Joey explicitly rejects a second task checklist: GMTM already captures the combine, mostly on mobile. He wants SPARQ to help athletes interpret and use their existing profile, understand the process and pursue opportunities. Codex acknowledged it has not completed a real combine as a participant and that the displayed help was a fixture stub. No more founder testing of the blocked checklist demo is requested.

The [new direction](../../docs/state/profile-value-direction-2026-09-08.md) defines a private profile debrief answering a real athlete question, with an editable/copyable summary or introduction when it serves a real intended use. It preserves existing capture, makes process guidance source-attributed, and separates actual outcomes from views/review markers/ratings. It is a specification, not a working replacement page. The planning contract is to record the correction, check feasibility, define acceptance and retire conflicting current pointers; no app implementation is in this pass.

## Evidence

- Read repo AGENTS/state, Control Tower leadership/operating contract and project registry; verified actual Git state. Current explicit user direction supersedes their earlier checklist-first priority without changing ownership or permissions.
- Reviewed Fable's `~/Desktop/gmtm-code-research/README.md`, repo platform reconciliation and data architecture documents.
- Delegated source-only audits of GMTM data capabilities and SPARQ reuse. GMTM local snapshot is `f2fe121d`, not verified current production. Root also inspected review-marker SQL and metric-scale lookup. The new brief has exact source pointers.
- Current SPARQ supports strict identity linkage, canonical field mapping, result parsing and scoped model context. The focused candidate excludes legacy profile routes. Existing comparisons, visibility, raw-HTML sharing and legacy draft ownership need correction or avoidance before reuse.
- GMTM source contains feedback, private scouting/list fields and attention/review markers; no authoritative national-team selection ledger or validated cohort was established. No live population query was performed. Final outcome records may exist outside the inspected source or in organization custom fields.
- Checked the current [USA Football digital-combine FAQ](https://usafootball.com/national-team/digital-combine): program guidance is available, but it does not provide this athlete's status or a promised response deadline. Historical selection PDFs must not be applied to the current event by assumption.

## Verification and scope

Documentation-only change: `AGENTS.md`, `docs/state/current-state.md`, `docs/state/athlete-pilot-plan-2026-09-08.md`, the new direction file and this handoff. Independent product review identified two material corrections, both incorporated: do not assume a coach introduction is every athlete's next step, and test incremental value against the existing GMTM profile rather than merely a successful Copy click. Local link checks and `git diff --check` are the relevant verification; no application tests are needed for this scope. Until committed these five files are the complete intended uncommitted change set.

No application code, runtime settings, prototype processes or user browser state changed in this planning pass. No live DB/model request, secrets access, external message, push, deployment, cloud operation or other repo edit occurred. Source reads and public web research do not establish live acceptance. Fable retains infrastructure/security work, and the separate Audit task remains separate.

## Next action

Implement and review only the new profile-value slice, using a narrow authorized projection and grounded output. Validate with actual profile evidence and functional edit/copy before asking Joey to test again. Locate USA Football's real decision source and athlete-visible stage semantics as a separate bounded context task; initial value must not depend on creating a full selection-data project or org onboarding campaign. Public sharing, outreach, calibrated comparisons and automatic opportunity discovery are separate later work with their own evidence and approval boundaries.
