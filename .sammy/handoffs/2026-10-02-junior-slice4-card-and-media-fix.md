# 2026-10-02 Junior slice 4 (My card) + media path fix

- Slice 4 e7b8aaf: DDL create_sparq_card_clips applied (Railway Agent DB), Railway + Vercel prod deployed, smoke clean.
- Live test (GMTM Chrome = deviceId 5b2e86c6-190f-42ab-bc39-98084bd6fcb5): picker save/reload/restore PASS, Copy link = gmtm.com/athletes/2, 0 console errors.
- Found: Joey's clips never played inline or showed posters. Read-only query (gmtmread): film 8236487 uri films/<uuid>-processed,
  8243185 users/2/uploads/metrics/<uuid>-processed (CDN 200 video/mp4, h264 High + AAC, 1080p, 18.4 s / 15.8 s);
  posters users/undefined/uploads/<uuid>.jpg (200). Slice 3's B3 block of users/undefined was wrong (never measured).
- Fix 5025f80: backend + frontend accept exactly those forms; parity tests both sides. Fable review found a frontend
  blocker (isCardVideo), fixed; fix-check "Safe to commit and deploy". 1782 backend tests, 33 safety checks, tsc pass. Deployed.
- Live after fix: posters load (naturalWidth 720/1080), 0 "Preview unavailable", play is now an inline button that mounts
  <video src=cdn...>. Actual playback UNVERIFIED: agent's tab was hidden, the browser never fetched the file.
- Closed: Joey confirmed both clips play inline (2026-10-02).
- Logo 2966b36: header shows the real SPARQ logo (SparqLogo, sparq-wordmark.png), 44 px tap target. Fable review safe. Deployed; Joey confirmed live 2026-10-02. Joey also confirmed both clips play inline.
