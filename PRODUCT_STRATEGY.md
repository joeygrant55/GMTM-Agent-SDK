# SPARQ Agent — Product Strategy

*Decided Feb 2, 2026*

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
- **Frontend:** Next.js on Vercel (sparq-agent.vercel.app)
- **Backend:** FastAPI on Railway
- **AI:** Claude Opus 4.5 (Anthropic)
- **Auth:** Clerk
- **Agent DB:** Railway MySQL (conversations, reports, links)
- **Athlete DB:** GMTM RDS (READ ONLY — metrics, orgs, offers)
- **Search:** Brave Search API (real-time web research)

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
- **Claude Opus 4.5** — best model, worth the cost at this price point
