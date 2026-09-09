# Find my next opportunity

Joey's September 9 direction: SPARQ's recurring value should come from researching relevant opportunities, people to contact, and in-person ways to demonstrate skills. The existing GMTM profile supplies useful context; it is not the product's endpoint. This follows the profile-value direction and is the next product milestone after restoring real footage previews.

## First useful experience

An athlete opens **Opportunities**, confirms a goal and any missing search constraints, and receives up to three current options worth considering. Each compact card answers why it is relevant, what it requires and what the athlete can do next. Categories can include a team/program pathway, a relevant publicly listed contact and a camp/combine/showcase. Do not force one of each category or fill three slots with weak matches.

Reuse the profile, saved goal, evidence selection and editable introduction composer. Ask only for missing information that changes the search: sport/competition category, intended level or pathway, location/travel range, timing and budget. Treat Joey's profile as a product test account, not a representative recruiting prospect. A goal written during technical testing is not enough to establish actual search intent.

## What a useful recommendation must contain

- Named organization and exact opportunity/cycle, participation route and official URL.
- Current date/deadline and timezone, place or remote status, cost and published requirements. Unknown material fields remain explicit; past events do not become open opportunities.
- Eligibility assessment limited to known requirements and athlete-confirmed facts: compatible with known criteria, needs confirmation, or excluded. Do not invent recruiting needs, chances of selection or fit percentages.
- One short reason grounded in the athlete's stated goal and supported profile facts. Upload ownership does not establish who appears in a video, the athlete's sport or ability. The founder's profile contains inspiration footage of another athlete; never treat that as personal performance evidence.
- An official contact's published role and purpose when relevant. Prefer the actual recruiting/program contact or published inquiry route. Do not invent email addresses, infer private contacts, or label a person interested in the athlete without evidence.
- Per-field source references, a checked time and an expiration/recheck policy. An existing team, plausible URL or model-written citation is not enough to call an opportunity open or verified.
- One primary action: inspect the official application/registration details, save the option, or prepare a relevant introduction. Secondary source/eligibility details belong in an expandable panel.

The experience should be visual and concise: title, place/date/cost, one relevance sentence and one action. Avoid a directory dump or another completion checklist. Media should clarify the organization/event when licensed and available, not supply generic credibility.

## Implementation sequence

1. Define an opportunity evidence contract and renderer around a small human-reviewed source set. Separate reusable public facts from private athlete relevance. Use field-level evidence and deterministic date/eligibility validation before model explanation.
2. Replace the current Opportunities placeholder with an owner-scoped shortlist. Preserve link-generation checks and the strict saved-work contract. Reuse reviewed-source/freshness ideas from `profile_pathways.py`; its guidance is not a live opportunity inventory.
3. Connect **Prepare introduction** to the existing composer with the verified recipient and athlete-selected evidence. Preserve an existing edited draft until the athlete explicitly chooses to replace it or start separate work. No automatic sending, registration or applications.
4. Add bounded research discovery and extraction behind the same contract. Discovery suggests candidates; validation determines what can be presented as current/actionable. Source outages and insufficient evidence should return fewer options, with a useful explanation.
5. Test with a small consenting adult-athlete cohort. Measure whether an athlete selects a credible option they would pursue, prepares a relevant next step and returns for refreshed research. Track viewed, selected, draft-prepared and official-route-opened separately; none establishes sending, application, coach response or selection.

## Reuse decisions from the current repository

`ProfileWorkspace.tsx` already has an Opportunities destination but no working shortlist. Existing evidence, saved intent and the composer are the safest integration points.

Legacy `enrichment_worker.py` and college/research screens contain discovery concepts and useful field ideas. They are not ready to expose unchanged: a name and plausible URL can pass their current verification, fit scores are model-generated, and enrichment hard-codes Class of 2026. Contacts, dates and camps need source-level validation. The legacy outreach target loader also lacks the required owner binding. Do not remount these routers to shortcut the new experience.

## Completion and evaluation

Verify profile → reviewed options → selection → useful next action, including expired dates, wrong categories, ambiguous timezones, unsupported contacts, unrelated citations, duplicate options, source failures, actor isolation and preservation of authored drafts. A result card rendering is not success by itself. Joey should be able to assess the full athlete experience before external testing; outreach is not authorized by this spec.

This is a product/implementation contract, not a current market inventory or a claim that research is implemented. No live opportunity research, real recommendations, provider calls, outbound messages, pricing change or deployment occurred while writing it.
