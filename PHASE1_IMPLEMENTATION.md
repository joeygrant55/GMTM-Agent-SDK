# SPARQ Agent - Phase 1 Implementation Plan

**Goal:** Build 5 core agents that help athletes discover opportunities and make connections

**Timeline:** Week 1 (Feb 3-9, 2026)

---

## 🎯 AGENTS TO BUILD

### 1. Camp & Combine Finder Agent
**Priority:** 1 (Build first)
**Complexity:** Medium
**Value:** High - immediate actionable opportunities

**Tools Needed:**
- `search_gmtm_events()` - Query GMTM event database
- `web_search_camps()` - Search web for upcoming camps/combines
- `scrape_event_details()` - Extract details from event pages
- `rank_events()` - Score events by fit (location, level, cost, timing)

**Agent Prompt:**
```
You are a Camp Discovery Agent. Your job is to find the best camps and combines for an athlete.

Given:
- Athlete's sport, position, location, age/grad year, metrics, budget
- Current date

Research:
1. Search GMTM events database for upcoming events
2. Search web for: "[sport] camps [location]", "[position] combines [region]"
3. Extract: Name, date, location, cost, coaches attending, registration deadline
4. Verify legitimacy (check reviews, official sites, past attendees)
5. Rank by fit:
   - Distance from athlete (prefer <100 miles)
   - Cost (flag if >$200)
   - Level match (D1/D2/D3 based on athlete's metrics)
   - Timing (flag if registration closes soon)
   - Value signals (D1 coaches, film reviews, combine testing)

Return top 5-10 with reasoning.
```

**Output Format:**
```json
{
  "events": [
    {
      "name": "Houston SPARQ Combine",
      "date": "2026-02-24",
      "location": "Houston, TX",
      "distance_miles": 15,
      "cost": 75,
      "deadline": "2026-02-20",
      "coaches": ["12 D2 programs", "3 D1 assistants"],
      "testing": ["40-yard", "vertical", "bench", "shuttle"],
      "fit_score": 95,
      "why_good_fit": "Close to home, affordable, your speed metrics will shine, D2 level match",
      "registration_url": "https://sparq.com/houston-feb"
    }
  ]
}
```

---

### 2. College/Team Opportunity Matcher Agent
**Priority:** 2
**Complexity:** High (requires multiple data sources)
**Value:** Very High - shows realistic paths

**Tools Needed:**
- `search_gmtm_coaches()` - Find coaches by school/position
- `get_college_roster()` - Scrape roster data
- `check_transfer_portal()` - Track roster holes
- `get_club_teams()` - Find club/AAU/Olympic programs
- `match_level()` - Predict D1/D2/D3 fit based on metrics

**Agent Prompt:**
```
You are an Opportunity Matching Agent. Your job is to find realistic recruiting targets.

Given:
- Athlete's metrics, position, grad year, location
- Athlete's goals (college level, geographic preferences)

Research:
1. Analyze athlete's metrics vs position averages
2. Determine realistic level (D1/D2/D3/NAIA/JUCO)
3. Find programs recruiting that position + level
4. Check rosters for graduating seniors / transfer portal departures
5. Identify programs with roster needs at athlete's position
6. Find alternative paths: club teams, Olympic programs

Return:
- 5-10 college programs (ranked by fit + need)
- 3-5 club/AAU teams if applicable
- Olympic/developmental programs if metrics qualify
```

**Output Format:**
```json
{
  "college_targets": [
    {
      "school": "Houston Baptist University",
      "division": "D2",
      "position_coach": "Mike Johnson",
      "roster_need": "High - 3 WRs graduating",
      "fit_reasoning": "Your 4.48 40-time matches their speed preference. They signed 2 TX WRs last year.",
      "contact_status": "Not contacted yet"
    }
  ],
  "club_opportunities": [],
  "olympic_programs": []
}
```

---

### 3. Coach Research & Contact Finder Agent
**Priority:** 3
**Complexity:** Medium (web scraping + data enrichment)
**Value:** High - enables outreach

**Tools Needed:**
- `find_coaching_staff()` - Scrape athletic department pages
- `find_email()` - Extract/guess email addresses
- `research_coach_history()` - LinkedIn, past signees, preferences
- `verify_contact()` - Check if email is valid

**Agent Prompt:**
```
You are a Coach Research Agent. Your job is to find and research coaches.

Given:
- School name
- Position

Research:
1. Find athletic department staff directory
2. Identify: Position coach, recruiting coordinator, head coach
3. Extract contact info (email, phone, Twitter)
4. Verify email format (firstname.lastname@school.edu)
5. Research background:
   - Years at school
   - Previous positions
   - Recent signees (247Sports, Rivals)
   - Recruiting preferences (size/speed/style)
   - Social media activity

Build contact card with all info + notes.
```

**Output Format:**
```json
{
  "coaches": [
    {
      "name": "Mike Johnson",
      "title": "Wide Receivers Coach",
      "school": "University of Houston",
      "email": "mike.johnson@uhcougars.com",
      "phone": "(713) 555-1234",
      "twitter": "@CoachJohnsonUH",
      "years_at_school": 3,
      "previous_school": "Rice University",
      "recent_signees": [
        "2025: 3 WRs (avg 4.5 40-time, all TX)",
        "2024: 2 WRs (speed focus)"
      ],
      "recruiting_notes": "Prefers speed over size. TX pipeline. Active on Twitter. Responds to emails (per 247 forums)."
    }
  ]
}
```

---

### 4. Email Outreach Agent
**Priority:** 4
**Complexity:** Low (text generation)
**Value:** Very High - converts research into action

**Tools Needed:**
- `draft_email()` - Generate personalized email
- `get_athlete_highlights()` - Pull key stats/achievements
- `suggest_send_time()` - Optimal day/time
- `send_email()` - Actually send (with approval)
- `track_email()` - Monitor open/reply

**Agent Prompt:**
```
You are an Email Outreach Agent. Your job is to write compelling, professional emails to coaches.

Given:
- Athlete profile (name, position, grad year, location, metrics, film URL)
- Coach profile (name, title, school, recruiting preferences)
- Email type (introduction, follow-up, camp registration, etc.)

Write:
1. Subject line (compelling, specific)
2. Greeting (use coach's preferred name/title)
3. Hook (why you're reaching out, mutual connection)
4. Value prop (athlete's key strengths aligned with coach's needs)
5. Social proof (verified metrics, achievements, film)
6. Call to action (specific next step)
7. Sign-off (professional but personal)

Rules:
- Keep it under 150 words
- Lead with value, not desperation
- Include 1-2 specific stats
- Reference coach/program specifically (not generic)
- Confident but humble tone
```

**Output Format:**
```json
{
  "subject": "WR from Houston - 4.48 40 time, 36\" vertical",
  "body": "Coach Johnson,\n\nI'm Joey Grant, a WR at Westlake High School (Houston, TX), class of 2027. I've been following UH football and saw you signed two speedy receivers from Texas last year.\n\nMy verified SPARQ metrics:\n- 40-yard: 4.48s (93rd percentile)\n- Vertical: 36\" (88th percentile)\n- Film: https://hudl.com/joey-grant\n\nI'll be at the Houston SPARQ Combine on Feb 24 and would love to connect. Are you open to a quick call next week?\n\nThanks for your time,\nJoey Grant\n(713) 555-5555",
  "send_time_suggestion": "Tuesday or Thursday, 10am-2pm (avoid Fridays, weekends, late nights)",
  "follow_up_date": "2026-02-17 (2 weeks if no response)"
}
```

---

### 5. Social Media Content Agent
**Priority:** 5
**Complexity:** Medium (content generation + timing)
**Value:** Medium-High - builds athlete brand

**Tools Needed:**
- `draft_post()` - Generate post copy
- `suggest_hashtags()` - Relevant hashtags
- `suggest_tags()` - Who to tag (coaches, programs)
- `suggest_timing()` - Optimal post time
- `create_graphic()` - Generate stat card images (future)

**Agent Prompt:**
```
You are a Social Media Content Agent. Your job is to help athletes build their brand.

Given:
- Achievement (new PR, camp invite, offer, commitment, game highlights)
- Athlete profile

Create:
1. Post copy (authentic, engaging, not boastful)
2. Relevant hashtags (3-5 max)
3. Tags (coaches, programs if appropriate)
4. Optimal post time
5. Content strategy notes

Tone:
- Authentic, not overly promotional
- Humble confidence ("Grateful" not "I'm the best")
- Work ethic focus ("Earned not given")
- Future-focused ("Ready for next challenge")
```

**Output Format:**
```json
{
  "post": "36\" vertical 📈 Putting in work for Feb camps. Grateful for the coaches pushing me every day. #GrindSeason #WR #Class2027",
  "hashtags": ["#GrindSeason", "#WR", "#Class2027", "#Houston", "#SparqTraining"],
  "tags": {
    "suggested": ["@HoustonFB", "@UTSA_FB"],
    "reasoning": "You're targeting D2 programs in TX. Tagging schools shows interest without being pushy."
  },
  "best_time": "Tuesday 7-9pm (high engagement window for athletes)",
  "notes": "Keep it achievement-focused but humble. Coaches want to see work ethic + coachability."
}
```

---

## 🛠️ TECHNICAL ARCHITECTURE

### Agent SDK Structure
```
/Users/joey/GMTM-Agent-SDK/
├── agents/
│   ├── camp_finder_agent.py
│   ├── opportunity_matcher_agent.py
│   ├── coach_research_agent.py
│   ├── email_outreach_agent.py
│   └── social_media_agent.py
├── tools/
│   ├── gmtm_tools.py (database queries)
│   ├── web_research_tools.py (scraping, search)
│   ├── email_tools.py (sending, tracking)
│   └── content_tools.py (text generation)
├── backend/
│   ├── agent_router.py (API endpoints for each agent)
│   └── main.py
└── frontend/
    └── app/athlete/[id]/agent-dashboard.tsx
```

### API Endpoints
```
POST /api/agent/find-camps
POST /api/agent/match-opportunities
POST /api/agent/research-coaches
POST /api/agent/draft-email
POST /api/agent/draft-social-post
```

### Data Flow
1. Frontend sends athlete profile to agent endpoint
2. Agent calls tools (GMTM DB, web search, scraping)
3. Agent analyzes + ranks results
4. Agent returns structured output
5. Frontend displays actionable results
6. Athlete reviews + approves actions (emails, posts)

---

## 📅 BUILD SCHEDULE

### Day 1 (Mon Feb 3) - Camp Finder
- [ ] Build `camp_finder_agent.py`
- [ ] Create `search_gmtm_events()` tool
- [ ] Create `web_search_camps()` tool
- [ ] Test with real athlete profile
- [ ] Return top 5 camps

### Day 2 (Tue Feb 4) - Coach Research
- [ ] Build `coach_research_agent.py`
- [ ] Create `find_coaching_staff()` scraper
- [ ] Create `find_email()` tool
- [ ] Test with 3 universities
- [ ] Return contact cards

### Day 3 (Wed Feb 5) - Email Drafter
- [ ] Build `email_outreach_agent.py`
- [ ] Create email templates
- [ ] Test drafts with real coach profiles
- [ ] Add send approval flow

### Day 4 (Thu Feb 6) - Opportunity Matcher
- [ ] Build `opportunity_matcher_agent.py`
- [ ] Create `match_level()` algorithm
- [ ] Query GMTM coach database
- [ ] Scrape college rosters
- [ ] Test with 5 athletes

### Day 5 (Fri Feb 7) - Social Media Agent
- [ ] Build `social_media_agent.py`
- [ ] Create post templates
- [ ] Test with sample achievements
- [ ] Add timing suggestions

### Weekend (Feb 8-9) - Integration
- [ ] Add agent buttons to athlete dashboard
- [ ] Build results display UI
- [ ] Add approval flows
- [ ] End-to-end testing
- [ ] Polish and deploy

---

## 🎯 SUCCESS METRICS (Week 1)

**Technical:**
- All 5 agents return results in <10 seconds
- 90%+ accuracy on coach contact info
- Email drafts require minimal editing

**User Value:**
- Find 5+ relevant camps per athlete
- Identify 10+ realistic college targets
- Draft 3+ ready-to-send emails
- Generate 1+ social post per achievement

---

## 🚀 NEXT STEPS (Week 2+)

Once Phase 1 is working:
1. Add **Assessment Agent** (honest evaluation)
2. Add **Progress Tracker** (metric improvements over time)
3. Add **Email sending** (not just drafting)
4. Add **Automated follow-ups** (2 weeks, 4 weeks)
5. Deploy to production for pilot athletes

---

**Let's start with Camp Finder (Day 1) - ready to build?**
