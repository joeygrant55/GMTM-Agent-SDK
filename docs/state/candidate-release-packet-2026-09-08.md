# SPARQ combine candidate release packet

Status: locally verified source package; no push or deployment. Baseline `53470702d32ace95fdf02f340f2012b34d8686bf` on `codex/athlete-home-first-value`. The final local commit is recorded in the sibling `sparq-release-readiness-2026-09-08/commit-receipt.json` after commit. Codex owns product integration; Fable's GMTM infrastructure/security lane is separate.

## Product scope

The first pilot should help an adult athlete enter through an existing USA Football combine, connect the correct GMTM profile, see missing submissions, ask explicit contextual help, and return to a refreshed checklist after submitting on GMTM. Combine onboarding does not initiate college research. The candidate supports independently signed-in junior/adult profiles; parent delegation and a junior family pilot require separate acceptance.

## Verified locally

| Evidence | Result | Practical limit |
| --- | --- | --- |
| Backend regression suite | 605 passed, one upstream deprecation warning | Synthetic service interfaces; no live SQL/provider calls |
| Actual PyMySQL transport | Eight regressions fail old connectors and pass the timeout change | Synthetic sockets; no DNS, MySQL server or whole-request deadline |
| Exact extracted source package | 19 packaging/launcher checks pass, including actual candidate lifespan and ASGI health | Installed macOS Python 3.13.7 dependencies |
| Actual Next 14.2.35 production build | Compile/typecheck and 24 static pages pass | Existing dependency tree; synthetic configuration |
| Same production artifact, real Clerk package | Five excluded routes return 404; signed-out inbox redirects to sign-in | No signed-in identity or live backend acceptance |
| Changed frontend regressions | 175 account checks and 68 policy checks pass | Isolated browser/component and transport checks |

The prior committed `5347070` fixture acceptance remains separate: actual Next development/RSC plus candidate ASGI covers invitation/recovery, adult zero-to-one synthetic submission refresh, explicit help, optional bootstrap failure and phone behavior. This package does not relabel that synthetic state update as a real GMTM submission.

Production-build run 1 exposed a generated PageProps failure and a blocked compile-time font download. Run 2 passes after removing the unnecessary ConnectPage default argument and disabling font optimization for candidate builds. All 121 frontend application snapshot hashes match, with no input mutation or outbound denial; owned build/server groups exit and the port closes. Real Clerk packages are used without auth aliases. The retained build embeds deliberately nonexistent service configuration and is not a deployable artifact.

After run 2, the harness failure predicate was strengthened to reject any snapshot-input mutation. Its syntax passes; the recorded run already has zero such mutations. The original run receipt and saved harness remain unchanged, and the post-run harness hash is recorded separately.

## Backend source context

The generated archive is `../sparq-release-readiness-2026-09-08/candidate-source.tar` relative to the checkout. SHA-256: `61e61c141ef260a3af95172e10976610ed59b650352990115cb4b50272562ca5`. Its adjacent manifest lists hashes for exactly 17 regular files: two Docker context files, two dependency manifests, twelve reachable candidate modules and the launcher. No credentials, test fixtures, generated assets or legacy main entry are included.

The separate `Dockerfile.candidate` is explicitly selected. Its companion ignore file excludes descendants before reopening the exact source paths; the tar allowlist independently determines all context bytes. Docker supports Dockerfile-specific ignore files and tar build contexts. [Docker build-context documentation](https://docs.docker.com/build/concepts/context/)

No usable local Docker/Podman engine was available. The archive has **not** been built into an image. Installed metadata validates 26 dependency constraints and 37 dependency edges for Linux x86_64/aarch64 markers; Linux installation, wheel availability, an immutable Python image digest and container execution are still unverified. The Python 3.13 base family matches the tested interpreter family. These constraints are not a hash-locked dependency artifact.

To reproduce source packaging, from the repository root with a new absolute output path and existing parent directory:

```sh
python backend/scripts/package_candidate.py --output "$CANDIDATE_SOURCE_TAR"
```

For a later approved build environment, set `RELEASE_PYTHON_IMAGE` to the reviewed Python 3.13 image reference including its resolved digest, and use the verified tar:

```sh
docker build --file Dockerfile.candidate \
  --build-arg "PYTHON_IMAGE=$RELEASE_PYTHON_IMAGE" \
  --tag sparq-combine-candidate:review - < "$CANDIDATE_SOURCE_TAR"
```

This command is preparation guidance; it has not been run. Record the resulting image digest, actual Python/dependency versions and `pip check`, then verify the image with synthetic configuration and denied external access. Confirm configuration-only health, excluded routes and process shutdown. The exec-form entry and launcher's `execve` avoid leaving a shell between the server and process signals. [Docker ENTRYPOINT reference](https://docs.docker.com/reference/dockerfile/#entrypoint)

## Paired release configuration

The release operator must fill in exact SPARQ service IDs, candidate origins, region/architecture, frontend build ID, backend image digest and prior rollback artifacts before deployment. None were changed or freshly verified in this local package.

| Surface | Required configuration and behavior |
| --- | --- |
| Frontend build | `NEXT_PUBLIC_APP_SURFACE=combine`, exact HTTPS `NEXT_PUBLIC_BACKEND_URL`, real `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`; clean dependency installation from the reviewed lockfile |
| Frontend server | Matching Clerk secret/server configuration injected by the platform; preserve sign-in/up routes; never deploy the synthetic build retained here |
| Backend entry | `Dockerfile.candidate` and `python /app/backend/start_candidate.py`; no legacy Procfile/main entry; valid `PORT`, one worker, proposed initial one replica |
| Backend auth | `AUTH_ENFORCED=true`; real HTTPS `CLERK_ISSUER`; exact matching `CLERK_AUTHORIZED_PARTIES` and `ALLOWED_ORIGINS` |
| GMTM source | Existing reviewed `db2-dev` host, `gmtmread` and injected password; `gmtm`/3306. No pre-prod, new accounts, credentials/plugin changes or GMTM writes |
| Agent state | Explicit separate `AGENT_DB_*`, reviewed existing ownership/claim/schema state, injected `SHARE_TOKEN_SECRET`; schema changes remain a distinct approved operation |
| Help | Supported explicit `COMBINE_HELP_MODEL`, corresponding provider key, finite `COMBINE_HELP_MAX_MODEL_CALLS` and `COMBINE_HELP_MAX_CONCURRENT_CALLS` |
| Ingress/operations | HTTPS, functional SSE streaming, no token-bearing claim URLs in access logs, configuration health distinguished from DB readiness |

Model call limits are process-local and restart with the process; multiple replicas multiply the allowance. They are operational bounds, not a durable organization-wide quota. Existing exhausted evaluation allowances are not reusable. Establish an explicit new live-test budget and separate production quota decision before live model use. The initial one-worker/one-replica proposal does not resolve durable cost accounting.

Claim preview writes `opened_at`; redemption writes Agent ownership/claim state and may create a workspace. These operations require scoped live acceptance even though GMTM reads are read-only. The existing `prepare_agent_schema.py` is intentionally excluded from the runtime image. Its default is a no-connection plan; any apply must separately acknowledge the exact Agent target and account for non-atomic MySQL DDL and existing conversation-schema prerequisites.

## Remaining acceptance and release decision

1. On the chosen build platform, verify clean frontend dependencies and the real backend image; retain exact artifacts and digests.
2. In an explicitly scoped service/data acceptance run, verify real Clerk issuer/JWKS/authorized-party behavior, the intended athlete's exact ownership, current Agent schema, read-only GMTM access and safe error behavior. GMTM staging shares production data and cannot serve as an isolated test environment.
3. Observe an actual athlete save a submission on GMTM, return to SPARQ, refresh and see the correct activity/division update. Check help delivery only under the new explicit provider allowance. Preserve the user's real data; record receipts without sessions, claim tokens or prompt contents.
4. Review the exact paired SPARQ release and rollback record with Joey, including target identities and internal-document sharing scope. Only an explicit SPARQ release instruction authorizes deployment; Fable's core API or database cleanup permissions do not.
5. After an authorized deployment, verify the same critical paths against the deployed commit/build/image, including mobile layout and signed-out route exclusions. If identity/source correctness fails, stop pilot promotion and restore the recorded paired artifacts/configuration. Do not drop schema, erase athlete data or repoint to pre-prod during rollback.

After these pass, a small adult pilot can measure whether athletes reach their checklist, complete missing submissions and return for help. Broad promotion and club monetization follow evidence from that journey. Guardian delegation, durable organization quotas and coach/profile-sharing workflows remain subsequent product work.
