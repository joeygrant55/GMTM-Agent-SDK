# Signed-in combine acceptance — September 7, 2026

Joey asked to continue after the successful read-only Railway/identity check. Keep the existing Codex checkout and branch. Story: an authenticated athlete opens the adult-combine inbox, sees current authoritative requirements, asks a task-specific question, receives a grounded streamed answer, and retains the correct GMTM continuation destination.

## Scope and completion

- Serve a current-source frontend snapshot locally at `http://localhost:3218`, with its existing Clerk configuration passed in process memory and an explicit local backend URL.
- Serve only the actual combine GET/help POST routers at `http://127.0.0.1:8118` in a separate operator harness. No full application startup or schema initialization. Fail closed on other routes, identities, events and origins.
- Use real Clerk signature/issuer verification, require the exact local authorized party, and resolve the authenticated subject through the existing unique mapping to GMTM user 2. No fabricated or newly created link.
- Keep both databases in guarded read-only transactions, pin GMTM to db2-dev/gmtmread, and use the existing verified Railway MySQL proxy. Restrict personal data to user 2 / adult event 1318.
- Permit at most five explicit help requests using the existing bounded provider implementation. Do not send external messages, redeem claims, persist conversations or navigate authenticated GMTM routes that may mutate invitations.
- Verify sign-in protection, actual checklist rendering, task context, real streamed help and safe failure, source refresh and the continuation URL. Capture redacted receipts/screenshots and identify any unverified boundary accurately.
- Fix concrete local implementation problems discovered within this scope and run relevant checks. No deployment, push, infrastructure/credential setting change, production data write or other-checkout edit is included.

The test harness and receipts live outside the application repo in `work/sparq-live-browser-2026-09-07/`. Offline checks do not count as real browser/Clerk/provider acceptance. If human sign-in is required, prepare the working sign-in page first and request that specific step while continuing independent checks.
