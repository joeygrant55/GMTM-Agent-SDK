# Junior redesign slice 2: journey Home, colleges map, saves + sent (2026-10-02)

Branch feat/junior-pilot, base 96f98b1. Uncommitted (see `git status`). No commit, push, deploy or DB change.

Done: /home journey (4 steps from real data, save target 3), /home/colleges (badges, distance, filters, hearts, local SVG map),
/home/colleges/[id] (+ heart, "I sent it"), /home/progress (Emails placeholder), /home/footage (My card placeholder).
Backend: saved-colleges GET/POST, colleges/{id}/{program}/sent POST; tables sparq_saved_colleges, sparq_sent_emails
(prepare_agent_schema STATEMENTS + module SCHEMA; NOT applied to any DB). Fit reasons + drafts use GMTM junior drills.
Data: built by backend/scripts/build_college_data.py (sources in backend/data/*.sources.json); 187 programs.

Evidence: backend 1730 passed; tsc clean; check-profile-safety 21, check-candidate-policy 170, check-gmtm-entry 19,
check-sparq-session 50; check-production-build profile + combine passed. Scratch visual preview (mock backend) desktop+phone:
no console errors, no horizontal scroll, active tab correct on all 5 pages.

Before release: run prepare_agent_schema for the 2 new tables (Joey-gated). check-profile-workspace.cjs deleted (stale).
