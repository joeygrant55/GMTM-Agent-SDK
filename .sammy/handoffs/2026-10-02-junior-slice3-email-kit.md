# Junior slice 3: coach email kit + Emails page (2026-10-02)

Branch feat/junior-pilot, base 8e3178b. Uncommitted (not pushed, not deployed).

Built
- /home/colleges/[id] is the coach email kit (Email.dc.html): "Email Coach <Last>" only from sourced
  head_coach_name; else "Email the coach" + staff page link. To prefilled only from sourced coach_email.
  CC my parent (sparq_parent_contact, address + updated_at only). Open in my email / Copy / I sent it ✓
  (needs a draft) / Write a new draft (confirm). Side panel: What's in your note (ticks from current text),
  this level's contact rules with sources, Tip with questionnaire link.
- Draft: model gets first name, position, plausible grad year, state only. Server inserts after the model:
  hometown (GMTM city), "Coach <Last>", highlight video (GMTM public film: her featured clip, then Highlight Reel, then newest), GMTM
  profile link https://gmtm.com/athletes/{user_id} (/profile/ 404s, measured 2026-10-02), best 2 drills.
- /home/emails lists drafts (first) and sent marks; nav desktop + phone points there.
- New API: GET college-emails/{id}; GET/POST parent-contact/{id}; detail adds "coach".

Deploy needs: run prepare_agent_schema (new table sparq_parent_contact). Reads fail soft until then.

Verification: backend 1748 passed; tsc clean; check-candidate-policy 187; check-profile-safety 24;
check-gmtm-entry 19; check-sparq-session 50; profile production build smoke passed.
Not done: no signed-in browser walkthrough of the new pages.

## Fix pass (review H1/H2/M1/M2/Low + live bugs B1-B6)
- H1 profile link only when GMTM users.visibility = 2 (u.visibility added to _gmtm_identity).
- H2 coach To only on a school .edu domain (not shared alabama.edu) or the program/staff/questionnaire host:
  excludes exactly 2 of 111 (JCSU gmail, Southern Union alabama.edu).
- M1 mailto > 2000 chars: Copy leads; Open in my email carries To/CC/subject only. M2 no title -> "Coach".
- Heart restored on the kit. B1 shell no longer remounts the page on session load; tabs prefetch={false}.
- B2 Kneeling Power Ball Toss added to the drill allow-list (unit not measured: ft/in/cm accepted).
- B3 GMTM users/undefined thumbnails omitted (backend + frontend). B5 chooseLabels keeps labels off "You".
- B6 level kept on one line. B4: Vercel logs show no 503 on page/RSC paths; not reproduced locally.
Verification: backend 1760; tsc 0; policy 187, safety 29, gmtm-entry 19, session 50; build smoke passed;
local prod browser: /home hard load -> 0 RSC prefetches, first tab click navigates.
