# GMTM research → SPARQ implementation reconciliation

September 6, 2026. Read-only research checkpoint, using Fable's folder at `/Users/joey/Desktop/gmtm-code-research/` and the existing Codex-owned SPARQ checkout. An explicitly requested GPT-6 Astra reviewer inspected the architecture documents independently; root verified selected integration findings in core source at the reported deployed API revision.

## Decision

Build SPARQ's guided athlete journey over GMTM's existing events, submissions and profiles. Fable's map supplies enough platform context to focus implementation discovery on `gmtm-api-v2` and `gmtm.com`; a fresh deep audit of all repositories is unnecessary for this milestone. Reuse the existing capture, media, scoring, communications and organization capabilities selectively as their contracts become relevant. Repository presence does not establish current operational health or safe reuse.

The current SDK supplies the agent/workspace experience and locally hardened identity boundaries. It still needs the authorized event context, actual requirements adapter, return refresh and phone journey described in the [milestone plan](sparq-combine-journey-plan-2026-09-06.md).

## What the supplied research establishes

- [Repository landscape](/Users/joey/Desktop/gmtm-code-research/gmtm-repo-landscape-2026-09-01.md:39): the documented main backend is `gmtm-api-v2`; main web is `gmtm.com`; athlete mobile client is `gmtm-expo`. Capture, video, scoring and staff tools form supporting integrations.
- [Workflow audit](/Users/joey/Desktop/gmtm-code-research/audit.md:200): important domain rules exist in the web client as well as the API. Validate the athlete's whole path, not just database columns.
- [Identity inventory](/Users/joey/Desktop/gmtm-code-research/audit.md:231): child and switched accounts are existing platform concepts. This is relevant to junior discovery but does not prove which mode USA Football uses today.
- [Lambda inventory](/Users/joey/Desktop/gmtm-code-research/lambda-inventory.md:3): scoring, invitations, reminders and processing have existing implementations. The inventory explicitly sends runtime/activity questions to a separate infrastructure audit; a downloaded handler is not proof of an active job.

This review read the documentation and selected core source, not every Lambda handler or every repository. Environment exports were not opened; no scripts, applications or live workflows were run.

## Reuse / integrate / build / unresolved

| Capability | Existing source to use | SPARQ action | Remaining evidence |
| --- | --- | --- | --- |
| Combine entry before results | API `virtual`, `invite`, `limits`, `permissions` | Integrate owner-scoped event context independently of numeric metrics | Exact access and registration rules for each current combine |
| Required activities and completion | API `event`, `virtual`, `submission`; web Task component and virtual routes | Build deterministic projection, one next action and refreshed progress | Current task configuration, required-field semantics, attempt selection and visibility parity |
| Athlete identity and junior delegation | GMTM session/user relationships; SDK Clerk-to-athlete link | Preserve separate authenticated actor and selected athlete concepts where proven necessary | Which parent/child mechanism the junior flow uses; how authority can be safely carried into SPARQ |
| Profiles, film and sharing | GMTM user/athlete/player records, canonical profile routes and visibility | Integrate existing evidence; build clear athlete-controlled sharing after open SDK sharing issues are fixed | Authoritative allowed fields, revocation behavior and public-view acceptance |
| Device testing and media | `sparq-capture-android`, existing S3/video pipeline | Reuse capture/evidence sources; keep upload and processing state explicit | Current upload reliability and mapping from captured result to verified evidence |
| SPARQ score | Documented `/analytics/process/gSPARQ` and scoring handlers | Integrate the established implementation after contract review | Formula/version, inputs/units, applicable sport/age groups and provenance labels; do not substitute the unwired ML experiment |
| Invitations and follow-up | Existing invite/notification modules and Lambda jobs | Reuse approved delivery operations after behavior/idempotency/consent checks | Active job inventory and overlap; avoid duplicate reminders. No sending is included now |
| Organization operations | Existing front-office, organization permissions, reporting and leaderboards | Reuse staff workflows; add only the smallest scoped completion readout needed for pilot evaluation | Correct organization authorization, freshness and metric definitions |
| Scout/opportunity discovery | Existing search, `scout`, `finder` and SDK work | Selectively integrate sourced information later | Runtime status, quality, allowed use and source attribution; generated reports are not confirmed selection outcomes |

## New source facts independently verified

Root fetched these files from `gmtmsports/gmtm-api-v2` at `1bf4fc0297d5eea56bed6bda54715f2f9c01593f`, the revision Joey reports deployed. This is source verification, not a live service or database check. Frozen files are in the task's `work/sparq-platform-reconciliation-2026-09-06/` directory.

1. **There is an existing pre-submission discovery path.** `resources/virtual/virtual.resolver.js:1198–1223` builds `getMyVirtuals` candidates from the union of submitted tasks, invitations keyed by `invited_id`, and event products in the athlete's `limits`. It then filters published events with `invite_only = 0` and `visibility = 2`. Reuse the relationships, but do not treat this listing as complete authorization or a universal registration list: it excludes private/invite-only events and does not settle all open-event cases.
2. **Product access is owner-scoped in a relevant handler.** `resources/limits/limits.resolver.js:261–272` checks `limits` by the request session's athlete ID and requested product ID. That provides a source rule to trace; it does not make an arbitrary event ID or SPARQ claim proof of paid registration.
3. **Two parent/child representations coexist.** `resources/user/user.resolver.js:803–812,945–955` uses `user_parents` for family listing and child-session permission. `2926–2942,3121–3128` uses `users.parent_id` for switching and child listing. The checked-in schema includes both. Do not merge them into an OR-based permission grant, assume one supersedes the other, or claim either is the active junior enrollment path without tracing its caller and configuration.

The current SDK claim path intentionally refuses a second athlete on an already linked Clerk account. These findings do not justify removing that guard. If junior operations require guardian delegation, define an explicit authenticated actor → authorized athlete selection contract and review it before junior acceptance.

## Freshness and conflicting assumptions

- Fable's landscape is dated September 1; its live/dead classifications, DNS claims, open PR states and operational defects are historical audit findings. They were not freshly rechecked here.
- The bundle README labels `audit.md` August, while the document dates itself April 15, 2026. Use its source pointers as discovery rather than an exact current platform specification.
- Older MySQL 5.7 references and pre-upgrade instructions are superseded by Joey's September 6 MySQL 8.4.11 context. `strict-backlog.md` describes failures under default strict SQL mode; it explicitly says they are not upgrade blockers under the retained production mode. No migration or infrastructure work is added to this product milestone.
- The README says the local core clone is master at `1bf4fc02`; fresh local Git inspection instead found `chore/opensearch-v2-host` at `f2fe121`, with an unrelated untracked `ecosystem.deploy.js`. We left it unchanged and fetched source at the explicit revision. The local web clone remains master at `b0293a2`; its production equivalence is unverified.
- The folder's documents do not identify the current adult/junior event IDs, required task sets or which account flow those programs use. Existing SDK test values such as 1317/1318 remain fixtures, not confirmed current campaign IDs.

## Narrow next discovery and implementation

1. Obtain the exact two live event URLs/IDs and inspect their applicable configuration through a controlled read-only path. Establish Charles's promotion coverage/date separately.
2. Trace current web callers of the two child-account paths and establish the junior actor/athlete model. Existing self-owned adult flow can be developed independently; do not silently redefine identity for juniors.
3. Resolve event discovery/access using the relevant invitation/product/permissions rules, then create sanitized fixtures for both combines with zero, partial and satisfied requirements.
4. Implement the current-combine adapter and phone journey against those contracts. Preserve the existing GMTM submission flow and previous SDK ownership work.

No full platform rewrite, automatic notification activation, score replacement or new organization onboarding system is needed to start this milestone. Public release remains subject to the previously documented identity, data, sharing and live-flow gates.
