# SPARQ 10x Experience Spec
_Generated: 2026-02-26 — Three high-leverage improvements_

---

## Feature 1: Live AI Demo (no sign-up required)

### Goal
Let cold visitors experience the AI before committing to onboarding.
Prove the product in 3 questions. Gate on the 4th.

### Route
Replace `frontend/app/demo/page.tsx` with a real streaming chat experience.

### Behavior
1. Page loads with a clean chat interface — no auth required
2. Visitor types any question, hits Send
3. Chat calls `POST /api/demo-chat` (new Next.js API route) which proxies to the SPARQ backend streaming endpoint at `focused-essence-production-9809.up.railway.app/api/agent/stream`
4. Response streams back and renders with the same streaming UI as the workspace (typewriter effect, 🌐 indicator for web_search)
5. A question counter tracks usage in `localStorage` key `sparq_demo_questions` (integer 0–3)
6. After 3 questions, disable the input and show a gate banner:

```
You've used your 3 free questions.
Create your profile to get answers personalized to YOUR stats and matches.
[Get Started Free →]  (links to /onboarding/search)
```

7. Starter prompts shown on empty state (clickable chips):
   - "What D1 schools recruit safeties from Texas?"
   - "How do I email a college coach for the first time?"
   - "What stats do D2 coaches look for in a linebacker?"
   - "When should I start the recruiting process as a junior?"

### API Route: `frontend/app/api/demo-chat/route.ts`
- Method: POST
- Body: `{ message: string, history: {role: string, content: string}[] }`
- Streams response from backend `/api/agent/stream` with a generic system context (no athlete profile)
- If backend is unreachable, return a graceful error: "Our AI is taking a quick break. Try again in a moment."
- No auth required — this is a public endpoint

### Backend note
Check if `/api/agent/stream` accepts requests without a `clerk_id` or `profile_id`. If it requires them, pass `clerk_id: "demo"` or a sentinel value and handle it gracefully in the backend (skip personalization, just answer generally).

### UI Design
- Full-page dark layout matching the workspace aesthetic
- Header: SPARQ logo + "Try SPARQ AI — No sign-up required" badge in lime
- Chat bubbles: user right-aligned (lime bg), AI left-aligned (dark card)
- Streaming text with cursor animation
- Question counter: subtle "2/3 questions used" in top right
- Mobile responsive

### File: `frontend/app/demo/page.tsx` — rewrite entirely

---

## Feature 2: Instant Fit Reasons + Enrichment Completion Notification

### Part A — Instant fit preview (no waiting for enrichment)

The college_targets table already has: college_name, college_city, college_state, division, conference, fit_score.
The sparq_profile already has: position, target_division, target_geography, grad_year, gpa.

Use this data to generate 2-3 immediate fit bullets without waiting for the enrichment worker.

#### New backend endpoint
`GET /api/workspace/colleges/{clerk_id}` already exists — extend each college object to include `fit_preview` array if `fit_reasons` is null/empty.

Add a Python helper in `backend/profile_api.py`:

```python
def _generate_fit_preview(college: dict, profile: dict) -> list[str]:
    """Generate instant fit reasons from existing DB data (no AI needed)."""
    reasons = []
    
    # Division match
    div = college.get("division", "")
    if div:
        reasons.append(f"{div} program actively recruiting {profile.get('position', 'athletes')}s")
    
    # Geography
    college_state = college.get("college_state", "")
    target_geo = profile.get("target_geography", "Anywhere")
    if target_geo == "Anywhere":
        reasons.append(f"Matches your open geography preference")
    elif target_geo == "In-state" and college_state == profile.get("state", ""):
        reasons.append(f"In-state program — {college_state}")
    else:
        reasons.append(f"Located in {college.get('college_city', '')}, {college_state}")
    
    # Class year / grad year
    grad_year = profile.get("grad_year", "")
    if grad_year:
        reasons.append(f"Recruiting the Class of {grad_year}")
    
    return reasons[:3]
```

In the colleges endpoint: if `college["fit_reasons"]` is null or `[]`, set `college["fit_reasons"] = _generate_fit_preview(college, profile_data)` before returning.

This means every college card shows real bullets immediately, even before enrichment runs.

#### Frontend change
In `frontend/app/home/colleges/page.tsx`:
- Remove the "🔍 Researching this program..." fallback
- The backend now always returns fit_reasons (either real enrichment or instant preview)
- Show fit_reasons bullets as before

### Part B — Enrichment completion notification

When the enrichment worker finishes processing all colleges for a profile, signal the frontend.

#### Backend change in `backend/enrichment_worker.py`
After the final `print(f"[Enrichment] Complete...")` line, add:
```python
# Mark enrichment complete on the profile
db = _get_agent_db()
try:
    with db.cursor() as c:
        c.execute(
            "UPDATE sparq_profiles SET enrichment_complete = 1 WHERE id = %s",
            (sparq_profile_id,)
        )
    db.commit()
finally:
    db.close()
```

Add `enrichment_complete TINYINT(1) DEFAULT 0` to the `sparq_profiles` table creation in `_ensure_tables()`.

#### New backend endpoint
`GET /api/workspace/enrichment-status/{clerk_id}` → returns `{"complete": true/false, "colleges_researched": N, "total": N}`

Query: count college_targets where fit_reasons IS NOT NULL vs total for this profile.

#### Frontend polling hook
In `frontend/app/home/colleges/page.tsx`, add a useEffect that polls `/api/workspace/enrichment-status/{clerk_id}` every 30 seconds if not complete. When it flips to complete:
- Show a toast notification: "✅ Coach research complete — your fit breakdown is ready!" 
- Refresh the colleges list to show real enriched fit_reasons

---

## Feature 3: "You're a Recruit" Welcome Screen

### Goal
After completing onboarding (Step 4), route the athlete to a personalized reveal screen before the workspace. Make them feel seen. Create the emotional hook.

### Route
New page: `frontend/app/onboarding/welcome/page.tsx`

### Behavior
1. After Step 4 (profile creation), redirect to `/onboarding/welcome` instead of `/home`
2. Page loads the athlete's profile + percentile from two API calls:
   - `GET /api/workspace/colleges/{clerk_id}` → get college count
   - `GET /api/athlete/{maxpreps_id}/percentile` (already exists from quick-scan) OR derive from profile data
3. Display the reveal screen (full viewport, centered):

```
[SPARQ logo — small, top center]

Welcome to SPARQ, [First Name]. 👋

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You rank in the top [X]% of [Position]s
in the Class of [Year] nationally.

[Stat 1]  •  [Stat 2]  •  [Stat 3]
[School Name] — [Record if available]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[N] programs are being matched
to your profile right now.

[Enter Your Workspace →]
```

4. The stats come from `maxpreps_data` stored in sessionStorage (`ONBOARDING_MAXPREPS_KEY`)
5. Percentile comes from calling `/api/quick-scan/{maxpreps_id}` with the athlete's MaxPreps ID (stored in sessionStorage from Step 1)
6. College count comes from `/api/workspace/colleges/{clerk_id}`
7. If percentile call fails, skip it gracefully — still show stats and college count
8. CTA button "Enter Your Workspace →" links to `/home`
9. No back button — this is a one-way door into the workspace

### Visual treatment
- Full dark viewport
- Athlete name in large bold white text
- Percentile in lime green — biggest number on the page
- Stats as 3 small tiles (same style as quick-scan page)
- College count with a pulsing lime dot to suggest activity
- Subtle fade-in animation on each section (staggered, 200ms apart)
- No sidebar, no nav — full focus moment

### Redirect change
In `frontend/app/onboarding/profile/page.tsx`, find the redirect after successful profile creation (likely `router.push('/home')`) and change to `router.push('/onboarding/welcome')`.

---

## Summary of Files

| Feature | Files to create/modify |
|---------|----------------------|
| 1 — Live AI Demo | `frontend/app/demo/page.tsx` (rewrite), `frontend/app/api/demo-chat/route.ts` (new) |
| 2A — Instant fit preview | `backend/profile_api.py` (add `_generate_fit_preview`, patch colleges endpoint) |
| 2B — Enrichment notification | `backend/enrichment_worker.py` (mark complete), `backend/profile_api.py` (new enrichment-status endpoint), `frontend/app/home/colleges/page.tsx` (polling + toast) |
| 3 — Welcome screen | `frontend/app/onboarding/welcome/page.tsx` (new), `frontend/app/onboarding/profile/page.tsx` (change redirect) |

## Constraints
- TypeScript, no errors
- No new npm packages
- Dark theme: bg-sparq-charcoal, text-sparq-lime, border-white/10
- Clerk useUser() for auth
- Same streaming SSE pattern as WorkspaceAIPanel for demo chat
- Graceful fallbacks everywhere — if API fails, degrade nicely
- Commit all changes with one descriptive message at end
- Mobile responsive

## When done, run:
openclaw system event --text "Done: SPARQ 10x spec built — live AI demo, instant fit reasons, enrichment notifications, welcome screen" --mode now
