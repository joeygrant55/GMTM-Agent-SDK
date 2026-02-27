# SPARQ E2E Fix Spec
_Generated: 2026-02-26 after live E2E browser test_

## Fix 1 — "Get Started Free" routes to old GMTM sign-up page 🔴

**Problem:** The "Get Started Free" CTA buttons on the landing page route to `/sign-up`, which shows the old GMTM athlete ID lookup flow. New users see "Enter your GMTM athlete ID" and bounce.

**Fix:** Update all primary CTA links on the landing page that point to `/sign-up` to instead point to `/onboarding/search` (the MaxPreps 4-step flow).

**Files:** `frontend/app/page.tsx` — find any href="/sign-up" or similar primary new-user CTAs, change to `/onboarding/search`.

---

## Fix 2 — Quick Scan gate references "GMTM" instead of MaxPreps 🔴

**Problem:** `/quick-scan` for unauthenticated users shows "Link your GMTM athlete profile..."

**Fix:** In `frontend/app/quick-scan/QuickScanClient.tsx`, find the unauthenticated/empty state section and:
- Replace "GMTM" with "MaxPreps" in all copy
- Update the "Connect Profile" button to link to `/onboarding/search` (not `/connect` or any GMTM page)
- Button copy: "Find My Profile →"

---

## Fix 3 — College fit scores have no explanation 🟡

**Problem:** College cards show a fit score bar (e.g. "94% match") but no reasons. Zero trust signal.

**Fix:** In `frontend/app/home/colleges/page.tsx`, update each college card to show fit_reasons:
1. The API already returns `fit_reasons` (JSON array of strings from enrichment worker) in `GET /api/workspace/colleges/{clerk_id}`
2. If `fit_reasons` has items: render up to 3 as small bullet points below the fit score bar
3. If `fit_reasons` is empty/null: show grey text "🔍 Researching this program..." below the bar
4. Keep existing fit score bar, status dropdown, all other UI unchanged

---

## Fix 4 — Draft Coach Emails "Coming Soon" → real feature 🟡

Build a coach email draft page at `frontend/app/home/outreach/draft/page.tsx`:

1. Athlete selects a college from their match list (dropdown from `GET /api/workspace/colleges/{clerk_id}` using `useUser()` clerk_id)
2. Pre-populated email template using athlete's profile data (loaded from `GET /api/profile/by-clerk/{clerk_id}` + their sparq_profile stored in onboarding — name, position, class_year, school, city, state, hudl_url, maxpreps stats)
3. Template:
```
Subject: [Name] | [Position] | Class of [Year] | [High School]

Coach [Last Name from college fit_reasons if available, else ""],

My name is [Name] and I am a [Position] in the Class of [Year] from [High School] in [City, State].

I am very interested in [College Name] and believe I would be a great fit for your program. This past season I [key achievement from maxpreps_data if available].

I would love the opportunity to speak with you about my interest in [College Name].
[Hudl link on its own line if available]

Thank you for your time,
[Name]
```
4. Editable textarea, "Copy Email" button (clipboard API)
5. On copy: auto-log to outreach — `POST /api/workspace/outreach/{clerk_id}` with `{school: selectedCollege, method: "Email", contact_date: today, status: "Awaiting Response", notes: "Drafted via SPARQ"}`
6. Show a success toast "Copied! Logged to your outreach tracker." after copy
7. Back link to `/home/outreach`

Also in `frontend/app/home/HomeClient.tsx`: change the "Draft Coach Emails" card — remove "Coming Soon" text, add `<Link href="/home/outreach/draft">` around a "Start Drafting →" CTA (same lime green style as "View Matches →").

---

## Summary

| Fix | File(s) |
|-----|---------|
| 1 CTA routing | `frontend/app/page.tsx` |
| 2 Quick Scan copy | `frontend/app/quick-scan/QuickScanClient.tsx` |
| 3 Fit reasons | `frontend/app/home/colleges/page.tsx` |
| 4 Coach email draft | `frontend/app/home/outreach/draft/page.tsx` (new), `frontend/app/home/HomeClient.tsx` |

## Constraints
- TypeScript, no type errors
- No new npm packages
- Keep existing Tailwind dark theme (bg-sparq-charcoal, text-sparq-lime, border-white/10)
- Clerk useUser() for auth throughout
- Don't touch backend, auth, or routing config
- Commit everything with one descriptive message when done

When completely finished, run:
openclaw system event --text "Done: SPARQ E2E fixes — CTA routing, Quick Scan GMTM copy, fit reasons display, coach email draft page" --mode now
