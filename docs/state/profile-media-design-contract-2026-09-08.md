# Athlete content as the starting point

Joey's new design correction: athletes should see their own media and content presented simply, with an immediate sense of action and value. This supersedes the question-only initial screen while preserving its focused question/answer/editor interaction.

## Completion

- Initial overview shows one actual eligible footage poster and its title, with up to two clearly labeled existing results. No fabricated ranking, scout interest, video assessment or athletic score.
- Athlete can browse their returned clips and explicitly use one in an introduction. That selects the factual public-page reference and opens the editor, preserving existing edits until explicit rebuild. Ask about my profile opens the existing question surface; returning to the overview/answer/editor retains state.
- Missing or failed posters show an honest title/availability fallback, never generic athlete artwork represented as their own content. Private/uncertain-scope footage remains available as text in the existing owner sheet; it receives no public thumbnail.
- Add only stored film service and bounded stored thumbnail key to the three existing owner SELECTs. Project a nullable thumbnail_url after existing public inclusion checks. Admit exact source-selected CDN/YouTube HTTPS origins and conservative raster paths; reject unsafe/unknown URLs. Do not derive images from film IDs or video URIs, fetch/proxy media on the server, broaden source access, or send thumbnails to AI.
- Client validates optional thumbnail metadata, loads admitted images without a referrer or cross-origin credentials, and recovers image failure without source reload, provider call or another host. Existing payloads without the new field remain usable.

## Verification and scope

Use synthetic backend/ownership/URL-boundary tests, component checks and actual Next/ASGI desktop/phone journeys. Verify image load/failure, clipping, selection-to-editor continuity, no automatic AI calls, actor isolation and preserved edited drafts. Browser image fixtures must be intercepted locally and clearly identified as sample media in preview evidence, never fetched from a real athlete for tests. Run finite heavy jobs serially with retained process/port cleanup. No live DB/provider call, infrastructure change, outreach, push or deployment. Record source/evidence limits and a dated handoff before the local checkpoint.
