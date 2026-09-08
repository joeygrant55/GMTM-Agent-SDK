# Junior handoff: resolve the existing athlete before connecting SPARQ

September 7, 2026. Evidence and execution packet; participant walkthrough **not yet run**. Governed by the [verification contract](junior-handoff-verification-contract-2026-09-07.md).

## What changed our understanding

A June 2026 GMTM support conversation documents a family that had completed Junior Digital Combine #1, created another child account in the app, and could not see the completed work in that child view. Support later reported that the main and child accounts used the same athlete name and instructed the parent to switch back. This is a concrete report of confusing duplicate profiles; it does not identify canonical database IDs or establish the current #2 workflow. We must resolve the athlete that owns the submissions before offering a connection or interpreting a different profile's empty checklist as unfinished work.

| Evidence | What it establishes | Limit |
| --- | --- | --- |
| [June 9–10 support exchange](https://mail.google.com/mail/#all/19ead8995804fb8d) | Support confirmed a prior junior submission; the family reported missing completion in a newly created child profile; support reported duplicate names and explained Switch Back. | Reported support history, not current source/database inspection or permission to access this family's account. Names, email addresses and screenshots are not copied here. |
| [January 29 SPARQ results support](https://mail.google.com/mail/#all/19c0b0b1696740d2) | Support directed a parent to the GMTM app, account switching and a legacy child-claim mechanism to access event results. | In-person results flow, not proof that current digital-combine participants should create or claim another child. Historical claim material is not used or reproduced. |
| [August 10 current campaign email](https://mail.google.com/mail/#all/19fec087a178f004) | Promotes both current combines and asks athletes to create their own profile. | Does not specify parent versus junior login/contact ownership. It also retains an old June deadline below the September 21 heading, so it is not a clean operational specification. |
| [August 4 registration edits](https://mail.google.com/mail/#all/19fcdbd90a7d2c6e) | Connor confirms the organizer's registration-page changes were applied to junior 1317 and adult 1318. | The quoted request concerns branding/copy; it does not specify identity or delegation. The linked copy document was not retrieved. |
| [Current official combine page](https://usafootball.com/national-team/digital-combine), checked September 7 | Requires an adult parent/guardian to handle the USA Football account and purchases, then directs combine participation to GMTM. | The USA Football purchase requirement does not determine the GMTM submission owner or grant access in SPARQ. |
| [Source matrix](junior-account-acceptance-2026-09-07.md) | Reviewed web submissions follow the active GMTM session; mobile has a wired parent-to-child session switch. SPARQ separately resolves one linked athlete. | Source behavior alone does not establish who operates a current family's account or a guardian delegation bridge. |

These searches were targeted, not exhaustive. No account credentials, claim codes or private submission contents are needed to resolve the workflow. Support history demonstrates that parent-managed operation exists; the exact current campaign arrangement remains to be confirmed.

## The product decision

Keep three facts separate: **who is operating the session**, **which athlete profile is represented**, and **which profile already owns the combine submissions**. An email address, athlete name, event choice or browser-selected child is insufficient to join them automatically.

1. **An existing athlete profile owns the work, with a supported athlete-owned SPARQ connection.** Verify that exact pair and reuse the current single-athlete adapter. The user's contact address alone cannot prove this case. A parent operating an athlete-named login does not silently become a verified self-owned junior.
2. **A parent needs SPARQ access on behalf of a distinct child.** Treat this as delegated access. Keep the parent's personal link intact. GMTM must provide authoritative parent/athlete scope that SPARQ can validate, with explicit athlete selection, revocation and isolation of conversations/progress. This is a proposed design branch, not an implemented or approved production integration.
3. **More than one profile could own the work.** Stop connection and resolve the canonical owner through the existing support process. Do not create a duplicate child, merge profiles, move submissions, swap links or select the first name/email match. A duplicate-name incident is a workflow defect, not evidence that one account is unauthorized.

The initial product should keep GMTM as the place to submit. The handoff must show the expected athlete before personal progress is presented. Until delegated access exists, SPARQ cannot claim to support a parent switching among children. A parent may still read public organizer requirements without that claim.

## Short operator walkthrough

**Entry requirements:** one existing participant with their involvement and permission, or an organization-owned representative test setup explicitly labeled as a mechanics test; confirmed web/app entry; expected athlete and canonical submission owner; separately confirmed parent authority if delegation is involved. Joey's athlete 2 acceptance remains valid for self-account/division isolation only. Historical email participants are not automatically test subjects.

1. **Show the existing journey.** The participant operates their normal GMTM entry and sign-in. Record whether the operator is the athlete or parent and whether a child switch is used. Record booleans/roles in the review copy; keep identifying details in a restricted operator record. Do not ask them to paste passwords, OTPs, cookies or claim codes into a handoff.
2. **Resolve the existing profile.** Confirm the intended athlete and which canonical profile owns any saved event 1317 submissions. Use a narrowly authorized read-only check or the participant's normal interface. Equal names/addresses are not enough. With duplicate profiles or no evidence, record unresolved and end this branch without a new link.
3. **Check SPARQ's current connection.** Validate its existing unique actor/athlete mapping. If it points at the parent, a sibling, a duplicate profile or is ambiguous, retain the current mapping and record the unsupported handoff. No claim redemption or child selection is used to force success. An unlinked participant is an onboarding case requiring a separately reviewed concrete connection action.
4. **Compare the supported pair.** Only if the current connection and authority are established, load junior 1317 through a freshly pinned, bounded, read-only harness. Compare observed submission counts/status against the same canonical owner. Show freshness and public requirements; verify recovery retains 1317. Do not enter answers or make model calls.
5. **Check isolation within scope.** Verify unsupported attempts to choose another athlete are rejected before source access using synthetic cases first. A real sibling's data is not a negative-test fixture. If future delegation is implemented, add actor/athlete-scoped caches/conversations and switch/revocation coverage before participant acceptance.
6. **Close accurately.** Stop owned test servers and retain redacted status/counts. Record pass, fail or not run per row below. A mechanics fixture or expected refusal does not count as successful real-family acceptance.

Opening authenticated GMTM event pages, legacy account-switch actions and SPARQ claim pages can cause writes. Their precise actions must be understood and authorized before a walkthrough executes; do not replay historical support instructions as read-only tests. The earlier self-account harness cannot be restarted or repointed at another athlete.

## Acceptance record

| Gate | Current status | Required evidence |
| --- | --- | --- |
| Actual operator and athlete are distinguished | Not run | Participant-operated flow and organizer's supported arrangement. |
| Existing canonical profile identified | Not run | Same source owner for submission and SPARQ access; duplicate candidates resolved. |
| Correct authority reaches SPARQ | Not run | Verified self-owned mapping, or implemented authoritative delegation. |
| Saved junior progress agrees with canonical owner | Not run | Fresh bounded source/browser observation for the approved participant. |
| Junior recovery preserves event and athlete | Self-account only | Current user 2 evidence exists; participant evidence pending. |
| Different athlete is refused / state cannot leak | Existing synthetic coverage | Add explicit delegated switch/revocation coverage if that branch is selected. |
| Current campaign accepts this family arrangement | Unconfirmed | Organizer/operator readback. Support history is not universal policy. |

## Ready-to-use request for Connor (local draft only)

“Could you walk us through one existing junior combine account, with the participant's permission? We need to see who signs in, whether they switch to a child in the app, and which existing athlete profile owns the submitted work. Please don't create another child profile or send us login codes. A short walkthrough of the normal flow is enough to choose the SPARQ handoff correctly.”

This text has not been sent or placed in Gmail drafts. The next required input is an existing authorized participant/test setup or the operator readback; no account has been selected from the support mailbox.
