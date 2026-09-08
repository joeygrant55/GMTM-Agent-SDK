# Current-combine journey planning checkpoint — September 6, 2026

Joey requested the detailed next-milestone plan after the identity/data implementation batch. This turn performed source review and documentation only. The next athlete loop is authorized context with zero results → actual outstanding requirement → optional grounded help → existing GMTM submission → refreshed progress → continuing private profile review.

## Owner and baseline

- Task: `Evaluate Sparq agent project`, `01a06f58-7203-7f82-a090-3545f126936b`.
- Checkout: `work/sparq-agent-review` within this task workspace.
- Branch: `codex/athlete-home-first-value`; HEAD `6c7e649ce5154f211401ed2e4af03d9691366194`.
- Origin: `https://github.com/joeygrant55/GMTM-Agent-SDK.git`.
- All prior application changes remain uncommitted. No branch, commit, push, deployment, live application flow or production mutation was performed.

## Deliverable and decisions

The [implementation plan](../../docs/state/sparq-combine-journey-plan-2026-09-06.md) defines five ordered slices, proposed API/snapshot contracts, ownership, source questions, acceptance cases and a measured pilot. A matching user-facing copy lives at the task's `outputs/sparq-combine-journey-plan-2026-09-06.md`.

Backend and frontend agents supplied independent read-only planning inputs. Their findings are incorporated: redeemed claims retain event identity but currently drop it during UI navigation; the home starting point selects from numeric results; generic bootstrap can infer the wrong sport and launch unrelated matching; the phone shell requires bounded layout work. A separate combine service must work without those dependencies. An invitation's selected event is context, not evidence of registration or entitlement. Repeated redemption must preserve subsequent explicit event choices.

Core API sources previously fetched at the reported deployed `1bf4fc02` revision were reused. Additional local web source in `/Users/joey/mercor-scan/repos/gmtm.com`, master at `b0293a2cc918da59afb53cc75c0cfdd71769c4a3`, was inspected read-only and was clean. This web revision was not verified against production. Question-level requiredness, type-specific validation, session/access checks and a candidate task redirect are discovery leads. Some task-page server rendering calls a payment-intent API; future checks must not assume all live navigation is read-only.

## Changes and verification scope

This turn's repository changes are uncommitted documentation only:

- Added `docs/state/sparq-combine-journey-plan-2026-09-06.md`.
- Added this dated handoff.
- Added one current planning paragraph to `docs/state/current-state.md`.

The task also adds the matching plan under `outputs/`. Verification passed: 12 relative repository links resolved, both output-plan links were rebased to their existing repository targets, output content matched that transformation, and document whitespace plus `git diff --check` passed. Application tests are not rerun for this documentation-only work. The earlier build handoff retains the 111 backend tests, 47 isolated browser assertions and TypeScript evidence; those are not new results from this turn or proof of this unimplemented milestone.

## Next action and open inputs

Start the source contract and zero-result fixture, then implement event resolution and progress/UI against the same contract. Charles's exact target combine URL/name and expected promotion date remain the already-requested inputs. Generic local fixture work can proceed; target-specific eligibility, rules and flow acceptance cannot be claimed without them. Live identity/database/schema, protected sharing surfaces and all other outstanding release gates remain open. All infrastructure, production, billing and external-message boundaries remain unchanged.
