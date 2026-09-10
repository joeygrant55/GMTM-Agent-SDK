# GMTM entry and the SPARQ athlete experience

## Direction from Joey

Athletes ordinarily join GMTM and complete a digital combine there. Joey wants a prominent signed-in entry into SPARQ Agent, clean movement in both directions, and SPARQ to become the athlete experience over time. The following is the recommended integration journey, not a deployed flow or a final hosting decision.

## Athlete journey

1. **Join and participate in GMTM.** Existing combine entry, submissions and media upload remain available in the current flow. SPARQ is accessible from signed-in navigation without becoming a compulsory detour during submission.
2. **Open SPARQ.** Use a persistent `Open SPARQ` entry, plus a stronger post-submission card such as `Put your profile to work` with an `Explore opportunities` action. Do not equate completion with selection, introduce a second submission checklist or require completion before exploring SPARQ.
3. **Arrive with the existing profile.** Carry the verified athlete and relevant combine context into the workspace. Do not ask the athlete to recreate a profile or routinely sign in again. Ask only missing goals and constraints that make the next result useful. Early/partial profiles get an honest useful starting state.
4. **Use the profile to pursue opportunities.** The athlete sees existing footage/results, researched options, public contacts and in-person opportunities. They can inspect why an option is relevant, prepare an introduction from selected evidence, save work and return to it. Implement the separate reviewed opportunity contract; these recommendations do not exist in the current app.
5. **Move back cleanly.** Provide a visible `Back to GMTM` action and contextual actions for the exact combine, profile edit or source footage. Return to the relevant screen, retain saved private work and refresh authorized source facts when coming back. Preserve user edits and handle changed-account/source failures explicitly.

Start with the prominent entry and a complete two-way journey. Once returning athletes reliably gain useful actions, make SPARQ the default signed-in athlete home while retaining direct access to ongoing combines and GMTM activities. The initial route recommendation is a first-party location such as `/agent`; a branded subdomain is an alternative if it enables a faster reliable launch. Neither URL is configured or approved here. Separate deployment does not have to create a separate athlete experience.

## Current implementation versus integration work

The current SPARQ app has Clerk authentication, explicit GMTM-athlete linkage, owned evidence/materials reads and separate saved goals/drafts. Claim redemption establishes the mapping; the mapping is not seamless GMTM-session sign-in. Existing GMTM source links also do not provide a persistent, contextual return journey.

Before the integrated release, implement and verify the GMTM-session-to-SPARQ handoff, first entry/return/session-expiry behavior and contextual navigation. Authenticate the actor and selected athlete on the server; do not trust an athlete ID or email passed in a URL. Parent/guardian and switched-child contexts must be explicit and independently authorized, never inferred from an adult session or carried silently across accounts. Choose the exact auth mechanism after inspecting the current GMTM web/mobile session contracts; sharing cookies or a hostname alone does not solve this.

GMTM remains canonical for existing athlete identity, profile facts, measurements, media and combine participation. SPARQ owns its private goals, research, saved opportunities and authored work. Keep the databases separate initially and integrate through reviewed ownership-bound interfaces; a database merger is not a prerequisite for a coherent experience. Profile/source edits continue in GMTM until explicit write integrations are designed and approved.

Design entry and return for mobile as well as desktop, including the GMTM mobile-app path. Retain combine context across the browser/app handoff where supported. A desktop-only entry would miss much of the existing combine traffic.

## First integration acceptance

- An existing signed-in athlete enters SPARQ from GMTM without routine second sign-in or repeated profile entry and sees only the correct account's data.
- They review a real opportunity/action, preserve private work, return to the intended GMTM combine/profile screen and reopen SPARQ with saved work intact and appropriately refreshed source facts.
- Test first entry, repeat entry, expired sessions, logout/account switches, junior/guardian contexts and mobile browser/app return behavior. Failure must not expose another athlete or discard a draft.
- Keep submission and official consideration access intact; any later paid research offering is a distinct entitlement decision. No price or payment flow is approved by this document.

This clarification defines placement and user experience. It does not implement SSO, publish a CTA, change authentication/DNS, dispatch Fable, deploy code or change GMTM data. Research delivery and a seamless entry/return should be built as one pilot journey rather than unrelated launch claims.
