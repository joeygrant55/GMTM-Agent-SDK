# Submitted results and footage source map

This is a source audit, not evidence of deployment, actual playback or live schema acceptance. Reviewed local core API snapshot: `/Users/joey/mercor-scan/repos/gmtm-api-v2`, `f2fe121d`, branch `chore/opensearch-v2-host`. Client source is the adjacent `gmtm.com` checkout. Neither core checkout was edited or executed.

## Stored thumbnails — later September 8 extension

The [media design contract](profile-media-design-contract-2026-09-08.md) supersedes the initial no-thumbnail projection below. The three existing owner film queries now also select `service` and `thumbnail_uri`, with SQL `OCTET_LENGTH` limiting the latter to 2048 bytes. There are no new queries or server media requests. Existing ownership, public-source eligibility and dead-link checks apply before a nullable thumbnail is projected; private/unknown/dead footage receives no thumbnail.

- Core `schemas.md:569` records nullable `thumbnail_uri` and `service`; no intrinsic image dimensions are provided.
- `resources/film/film.resolver.js:438` maps GMTM/S3 to the GMTM CDN and YouTube service names to YouTube's image origin. The adapter does not reuse that helper's permissive substring-host/arbitrary-URL behavior.
- Local research `lambda-code/generate-thumbnail/index.js:66` writes `videos/film/thumbnails/<UUID>.png`. The legacy `thumbnail-extractor/index.js:55` supports `videos/events/<event>/edited-thumbnails/<filename>` and `users/<user>/uploads/<filename>`. Its extension is environment-derived; do not assume every historical record is JPEG.
- `resources/film/film.resolver.js:1541–1547` stores YouTube keys as `vi/<11-character-video-id>/default.jpg`.
- The adapter accepts only exact `https://cdn.gmtm.com` or `https://i.ytimg.com` namespaces corresponding to the recorded service, positive safe-integer owner/event path segments, and conservative JPEG/PNG/WebP filenames. No ports, credentials, encoded paths, query strings, fragments, arbitrary hosts or video-URI-derived images are accepted. Unknown legacy forms return `null`.
- The client uses a 16:9 containment frame; this is presentation, not a claim about stored dimensions. It omits referrers and cross-origin credentials. Missing/failed images remain honest placeholders with the canonical film-page action available. No alternative image host or generic athlete photo is substituted.

This is verified local source mapping, not fresh live thumbnail coverage, image availability, CORS or playback acceptance. Earlier owner reads below predate these added columns. Thumbnail metadata remains outside the server-assembled model context and generated draft text.

## Submitted answers

- `resources/submission/submission.resolver.js:301–317`: own submissions derive `user_id` from the authenticated session and include nonremoved visibility >=0.
- `1504–1513`, `2536–2543`: the original `event_task_submissions.payload` is inserted and replaced on edit. `event_answers` is a secondary CRM mirror; edits append rows at `2580–2596`, so it is unsuitable as the latest answer source.
- Client `components/organisms/Task/index.js:172–184`: `questions` maps `<type>:<title>` to `{key,type,question_id,metric,value,...}`. Retained keys/labels preserve historical question context when definitions change (`1241–1257`).
- Numeric answers are `{value:{value:number|string,unit:string},type:"metric"}` (`1974–1989`). The adapter only admits explicit known title/unit pairs. It does not flatten essay, parent, contact, teammate or other nested payload values. Unsupported legacy payload formats stay outside the projection.
- Client `components/molecules/MetricInput/index.js:94–136`: documented formatted time inputs (`SS.00`, `MM:SS`, `MM:SS.00`, `HH:MM:SS` and corresponding supported `Time (...)` labels) store milliseconds. The adapter preserves those values with the explicit unit `milliseconds`; ordinary `seconds` values remain seconds. Fractional milliseconds are excluded.
- `submission.resolver.js:170` labels `created_on` as `submitted_on`. Edits do not explicitly set a new submission timestamp; the adapter does not call this a measurement or last-edit date.
- `approved=1` is automatically set during non-S3 video/edit handling and processing callbacks (`2448–2450`, `2980–2985`, `3079–3089`). `submission_reviewed` is a CRM marker (`3353–3377`). Neither is selection or verified performance evidence, and neither enters the response.

## Footage

- `resources/athlete/athlete.resolver.js:1053–1084` and `3029–3075`: existing profile media uses submitted-film, direct personal-film and legacy career personal-film paths. The new adapter fixes each query to the current owner and validates every returned owner reference, including overflow rows. All present direct-user, career-user and submission-user references must agree.
- Film/career approval predicates reject unapproved suggestions. Both `suggested_by` and `suggested_by_org_id` are checked when approval is 0. Removed, inconsistent, dangling career/submission references and challenge ownership are excluded.
- `schemas.md:569–603` documents the film fields and the historical `event_id` default 0. Only exact integer 0 or NULL means no declared film event reference. Nonzero event references must be positive; submitted-film references must match the event reached through the owned submission.
- Personal film ownership does not grant access to arbitrary event metadata. Its event join reads only events passing the full existing public gate, including `networks_only=0`. Missing/restricted event context leaves the owner’s film visible with generic provenance and `can_include=false`.
- Public film attached to a private career can remain includable because the career proves ownership only: no career information enters this projection. Public profile media queries gate `f.visibility`, not career visibility (`athlete.resolver.js:1076–1084`, `resources/video/video.resolver.js:82–90`). Career still must be nonremoved and approved/unsuggested.
- `film.in_person_event_id` is not resolved in this slice. Such owner footage remains private context and is not eligible for a draft; no in-person event identity/publicity/verification is inferred.
- `https://gmtm.com/film/{id}` is the existing film page, generated solely from a validated safe positive integer. No URI, thumbnail, raw service URL or description column is read. No link is fetched automatically. Media with exact recorded `dead_link=1` has no link. Other footage is `unchecked`, never confirmed playable. Draft eligibility adds only the canonical public page reference: it requires public source scope and exact `dead_link=0` or NULL. Unknown/malformed dead-link values remain view-only. Legacy `processed` values do not determine eligibility or establish active processing. Core `resources/film/film.resolver.js:1185` stores 0 for GMTM uploads, while its response at `1295–1296` presents GMTM uploads as 1; the web film page at `pages/film/[film_id]/[...slug].js:837` does not treat 0/NULL as an active processing state. The initial processed=0 interpretation was corrected after the bounded owner read exposed that mismatch; queries and ownership/publicity gates are unchanged.

## Bounded read contract

The handler accepts no query parameters and resolves the existing forward/reverse Clerk owner link. Those two Agent SELECTs precede four fixed GMTM SELECTs:

| Function | Parameters | Bound |
| --- | --- | --- |
| `_submission_rows` | `(athlete_id, 51)` | Latest nonremoved attempt per task; 50 rows plus one overflow |
| `_submitted_film_rows` | `(athlete_id, 51)` | Film reached through owned submission |
| `_direct_film_rows` | `(athlete_id, 51)` | Personal film with direct owner |
| `_career_film_rows` | `(athlete_id, 51)` | Personal film with NULL direct owner and owned career |

All source queries return canonical `user_id` for the owner-only live reader. Each query is a literal parameterized SELECT in its named function. There is no fallback query, arbitrary athlete selector, metadata introspection, provider or media access. The completed earlier measurement read remains separate.

Submission payload transport is limited with SQL `CASE` to 65,536 bytes, then checked again before parsing; question maps are limited to 40 entries. Duplicate JSON keys and conflicting latest task rows are rejected. A malformed newest attempt never falls back to an older one. Output is capped at 20 submitted results plus 10 footage records. Source and ownership failures return `source_unavailable` with no partial response; empty supported results remain `ready` with scope limitations. Connections close before response projection.

## Verification responsibility

`backend/tests/test_athlete_materials.py` exercises the actual FastAPI handler, existing owner-link resolver, fixed SQL boundary and projections with synthetic stores. It covers foreign/missing/conflicting owners, all three film paths, private and removed context, malformed/oversized payloads, numeric units, no contact leakage, safe generated links, processing flags, row/output bounds and cleanup. Root records the final aggregate test result, fixture integration, live read allowance/results, source hashes and handoff. This source map does not claim any real athlete material was loaded.
