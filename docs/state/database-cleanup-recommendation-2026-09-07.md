# Database cleanup recommendation

September 7, 2026 Eastern; release evidence extends into September 8 UTC. Joey requested an opinion while Codex continues local SPARQ product work. This is a recommendation, not deletion approval or a cloud-state receipt. Fable remains the infrastructure executor.

## Recommendation

Delete `family-test` first after confirming its retained source snapshot remains available and no newer test work depends on the instance. The test purpose is complete. This is a restored copy of production data, not a clean synthetic development database; keeping it running provides no demonstrated product benefit. Retain the source snapshot, harness, reviewed patch and test receipts. No extra snapshot of the disposable copy is needed if it contains no unique work and the source remains restorable.

Delete `pre-prod` after a final check of retained snapshot and current consumers. Preserve `pre-prod-final-20260906`; confirm current deployed configurations, including SPARQ Railway, target `db2-dev`, and use an already authorized meaningful GMTM-backed read as application evidence. A failed login or an HTTP health response alone does not establish that a database is unused. Do not reset stopped/exhausted Codex read allowances for this check or restart the instance merely to inspect dependencies.

Neither instance is needed for the current local SPARQ startup tests. The PR 73 deployment receipt removes the earlier release-order dependency; its remaining authenticated verification should use an authorized non-mutating probe, not depend on preserving an idle production-data copy.

## Evidence read

- `/Users/joey/Desktop/gmtm-code-research/receipts/removeChildAccount-test-20260908T014109Z.json`: 14/14 checks, MySQL 8.4.11 on `family-test`, cleanup of nine synthetic users and one claim, no remaining fixture users. Fable identifies the restore source as `db2-dev-post-84-20260905-2238`. Saved receipts do not prove current snapshot availability or the absence of work added later.
- `/Users/joey/Desktop/gmtm-code-research/deploy-73-20260908T024032Z.md`: merge `93c18b14c848fa123017356aa2db309b28350c65`; reviewed function digest matches on staging and both API hosts, successful PM2 reloads and health 200. Follow-up observations around 03:14 UTC show stable workers and no matched timestamped errors. The last observation is approximately 29 minutes after the last production reload. The interrupted background observation job was replaced with manual checks. An authenticated distinguishing probe was not recorded; disk/reload/health evidence is not proof of that endpoint behavior.
- `/Users/joey/Desktop/aws-costs/mysql84/v2-run-20260906-deletes.md`: `pre-prod-final-20260906` available at 16:19:15 UTC September 6, followed by stop initiation. Fable's acknowledgment places the stopped state around 16:20 UTC.

[AWS documents automatic restart after seven consecutive stopped days](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html). From the reported September 6 stop, the estimated restart is Sunday September 13 around 12:20 p.m. Eastern. Confirm the actual stop state/time before scheduling; Saturday is a conservative cleanup target, not the calculated restart date. [Stopped instances still incur storage charges](https://aws.amazon.com/rds/faqs/), so repeated stopping is not a substitute for removing an unused instance.

No AWS query, deletion, database write, release action or production configuration change was performed by Codex for this recommendation. The infrastructure observations above are Fable's local receipts, not independent live Codex verification. Actual deletion requires Joey's explicit approval in the execution lane, followed by per-instance deletion/retained-snapshot evidence and normal application checks.
