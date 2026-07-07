# SPARQ Agent — Product Strategy

*Decided Feb 2, 2026 — superseded in part by the "Revised July 2026: Club-First Pivot" section at the end of this doc (see MARKET_RESEARCH.md for the evidence).*

## Vision
The first AI-powered recruiting advisor with real athlete data. Give every athlete access to $5,000-level recruiting guidance for $29/month.

## Monetization: Freemium → Premium

### Free Tier (Acquisition)
- 3 agent conversations/month
- Basic profile analysis
- Camp finder
- 1 saved report

### Premium ($29/mo or $249/yr)
- Unlimited conversations
- Deep college fit reports (auto-saved)
- Coach email drafting with real metrics
- Recruiting calendar alerts
- Unlimited saved reports & action plans
- Priority research (faster responses)
- Profile completeness tools

### B2B — Phase 2
- **High Schools/Clubs:** $500-2,000/yr per org
  - Every athlete gets an AI advisor
  - Coach dashboard — track all athletes
  - White-label option
- **College Programs:** Reverse matching
  - Find athletes that fit their program
  - AI-powered scouting reports

## Revenue Projections

| Stage | B2C Users | B2B Orgs | MRR | ARR |
|-------|-----------|----------|-----|-----|
| Launch (Month 1-3) | 100 | 0 | $2,900 | $35K |
| Growth (Month 4-8) | 500 | 10 | $15,500 | $186K |
| Scale (Month 9-12) | 2,000 | 50 | $63,000 | $756K |

## Unit Economics
- Claude API: ~$0.50-1.00 per deep research session
- Average user: 5-10 sessions/month = ~$5-10/month API cost
- Premium at $29/mo = **65-80% gross margin**
- At scale with caching/optimization: **90%+ margins**

## Competitive Moat
1. **Data** — 75K athletes, 131K metrics, 2,900 colleges, 7,832 scholarship offers
2. **First mover** — AI recruiting advisors don't exist yet (Feb 2026)
3. **Network effects** — More athletes → better matching → more colleges
4. **Switching costs** — Reports, conversation history, profile data
5. **Integrations** — Built on GMTM/Sparq infrastructure

## Go-To-Market
1. F&F launch (Week 1) — 20-50 athletes from GMTM network
2. Social proof — testimonials, before/after recruiting outcomes
3. High school coaches — "give this to your athletes" (viral loop)
4. Content marketing — TikTok/Instagram showing agent in action
5. Partnerships — AAU programs, travel ball, club teams

## Technical Architecture (Current)
- **Frontend:** Next.js 14 on Vercel (sparq-agent.vercel.app)
- **Backend:** FastAPI on Railway (focused-essence-production-9809.up.railway.app)
- **AI:** Claude Sonnet 4.6 (Anthropic SDK) — `web_search_20250305` native tool + custom `query_database`
- **Auth:** Clerk
- **Agent DB:** Railway MySQL (sparq_profiles, college_targets, conversations, messages, outreach)
- **Athlete DB:** GMTM MySQL (READ ONLY — users, user_metrics, scholarship_offers)

## Implementation Priority
1. ✅ Core agent with 6 capabilities
2. ✅ Streaming responses (SSE)
3. ✅ Chat persistence
4. ✅ Auto-saved reports
5. ✅ Dashboard + links
6. ✅ Clerk auth
7. 🔲 Stripe integration + usage gating
8. 🔲 Landing page with pricing
9. 🔲 Usage analytics
10. 🔲 B2B dashboard

## Key Decisions
- **Price:** $29/mo (10x cheaper than recruiting services)
- **No free trial** — free tier IS the trial
- **Reports are the value** — chat is the interface, reports are what people save/share
- **GMTM DB read-only** — all agent data on Railway MySQL
- **Claude Sonnet 4.6** — best speed/cost/quality tradeoff at this price point

---

# Revised July 2026: Club-First Pivot

*Decided July 2026, based on MARKET_RESEARCH.md. Supersedes the D2C-first monetization above.*

## Why the pivot

The Feb plan led with a $29/mo D2C consumer subscription. Market research (July 2026) shows
that lane is structurally squeezed: free-and-verified below (Scorability — free for athletes,
colleges pay $10–40K/yr, $40M raised), $9.99 AI beside (RecruitLook), $1K–3K human services
above (NCSA), seasonal churn, and a customer that expires (~18 months to commit-or-quit).
Meanwhile the channel that demonstrably works in this category is club/tournament B2B2C, and
the emerging moat across the industry is **verified athlete data** — Scorability acquired
Ryzer (27K camps/yr) precisely to own a verified-data pipe.

SPARQ's unfair advantage: **we own the measurement layer.** Capture devices + SPARQ testing
protocol + historical SPARQ/combine datasets + 75K GMTM profiles / 131K metrics / 7,832
scholarship outcomes. Nobody else can generate device-verified data at the club level.

## The flywheel

1. **Club runs SPARQ testing days** with our capture devices (included in club subscription).
2. **Verified metrics flow into athlete profiles** automatically, with provenance
   (event, date, device) — displayed as "SPARQ Verified" everywhere, distinct from self-reported.
3. **Every tested athlete gets a free SPARQ profile + honest assessment** benchmarked against
   the historical database — real percentiles, not vibes.
4. **Parents upsell to Pro** ($29/mo / $199/yr): the working agent (Scout/Drafter/Analyst),
   coach outreach with reply tracking, Sunday parent brief.
5. **The verified pool grows** → college programs pay for access to device-verified athletes
   (the $10–40K/yr lane Scorability validated) — Phase 3.
6. **Recruited athletes become club marketing** → more clubs sign → more testing → more data.

Consumer subscription moves from "the business" to "the upsell." The club is the customer;
the database is the asset; the agent is the reason athletes and parents engage weekly.

## Beachhead: flag football (added after USA Flag Football impact report)

Proof point in hand (2026 U.S. National Team Trials impact report, source: USA Flag Football
Head of Player Personnel): **68 GMTM athletes invited to 2026 trials; 64.6% of all Adult Men
trial invites** came from GMTM digital combines/SPARQ testing (up from 18% in 2025); average
25.8% share across all six categories, growing in every one.

- Flag football debuts at the **LA 2028 Olympics** and is the fastest-growing youth sport —
  and we are already embedded in the national-team selection funnel.
- Club-first GTM launches in flag football specifically ("SPARQ testing is how USA Flag
  Football finds national team athletes — get your club tested"), then expands sport by
  sport with the same playbook.
- Marketing caveat: invite-share reflects pipeline relationships as well as the rating's
  predictive power, and youth-category samples are small. Lead with the Adult Men number;
  don't claim causality.

## The data asset: outcome-labeled, not just verified

The durable AI advantage is the pairing of **standardized verified inputs** (device-captured
SPARQ ratings) with **labeled outcomes** (national-team trial invites, selections, 7,832
scholarship offers). That supports a calibrated selection model — "athletes with your SPARQ
profile reached X outcome at Y%" — with the LLM narrating numbers a model computed, not
guessing. General-purpose AI cannot replicate this without the outcome data.

**Build implication:** `athlete_outcomes` table (trial invites, selections, offers, commits)
linked to verified metrics and events is a first-class priority alongside verified-metric
ingestion. Every testing day and selection cycle grows the labeled set.

## The club offer (v1)

- **Price:** $1,500–$2,500/yr per club (anchor: clubs already pay Hudl $1,500–$4,000/program).
  Pilot phase: free/discounted for 3–5 clubs in exchange for testing cadence + testimonials.
- **Includes:** N testing days/season with capture devices; coach dashboard (roster,
  verified percentiles, progression, recruiting pipeline status per athlete); free athlete
  profiles + honest assessments for the full roster; parent briefs.
- **The pitch to clubs:** "Your athletes get verified combine data and an AI recruiting
  agent. You get proof your program develops athletes — and gets them recruited."

## Build priorities (delta from current product)

1. **Verified-metric ingestion**: capture device → API → `verified_metrics` with event
   provenance (event_id, club_id, device_id, date). Verified vs self-reported must be
   visually distinct across every surface.
2. **Org accounts + roster**: club entity, coach role, athlete invite/gift flow,
   team dashboard (read-only v1 is fine).
3. **Parent brief** (Sunday email): the payer-facing artifact that drives the Pro upsell.
4. **Keep**: agent inbox loop, honest assessment, outreach + reply tracking, Quick Scan
   (now "get SPARQ tested near you" is its CTA).
5. **Deprioritize**: D2C paywall as the primary motion (Stripe still needed — for club
   billing and Pro upsell), one-time report SKUs, video pipeline, unbuilt agents.

## Compliance note (non-negotiable before first testing day)

Device-captured performance data on minors requires parental consent at event registration
(COPPA for under-13s; state biometric-privacy laws — e.g., Illinois BIPA — may apply
depending on what the devices capture, especially any video/motion data). ToS + privacy
policy + consent flow ship before the first pilot event, not after.

## 90-day sequence

- **Weeks 1–2**: prod env vars for the new auth layer; pick 3 pilot clubs from the GMTM
  network; write the testing-day playbook; consent/legal pages.
- **Weeks 3–6**: verified-metric ingestion + org accounts + coach dashboard v1.
- **Weeks 7–8**: first pilot testing day; iterate on the capture → profile → assessment flow.
- **Weeks 9–12**: 3 pilots live; measure athlete activation + parent upsell rate; set club
  pricing from real willingness-to-pay; open paid club sales.

**Kill criteria** (decide with evidence, not vibes): if after 3 pilot clubs we can't get
(a) a second testing day scheduled per club, (b) >40% of tested athletes activating profiles,
or (c) any club willing to pay at renewal — revisit the whole thesis.
