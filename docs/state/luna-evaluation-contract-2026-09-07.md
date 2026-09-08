# Local Luna integration and comparison

September 7, 2026. Joey explicitly approved the proposed local Luna integration, usage tracking, request limits and a small synthetic comparison with the existing Sonnet baseline. This is a new synthetic-test authorization; it does not reset or reuse the exhausted five-call athlete-data acceptance harness.

## Deliverable

- Opt-in server-selected GPT-5.6 Luna for the existing combine-help SSE flow, preserving Sonnet 4.6 as the default and retaining the authenticated deterministic source boundary.
- Privacy-safe usage metadata for attempted model calls, including failures and unknown usage after interrupted streams. Bound provider calls, output, concurrency and test spending; disable automatic retries and fallback.
- Six paired synthetic cases covering focused highlights, the adult dash caption bug, presence versus qualification, unavailable junior/guardian progress, prompt injection and a concrete missing-field next step.
- Real provider streaming through the application adapter, with measured token usage, latency and price-based cost estimates. Record every attempt and report failures; do not silently replace poor answers.
- Independent offline review, focused regression checks, written results and an accurate deployment limitation.

## Live test limits

At most 24 provider calls across this whole evaluation, including Sonnet tool continuations and failed attempts, with a $2 conservative reservation budget and 1,200 output tokens per call. Reserve budget before transmission, keep unknown charges reserved and do not reset counters across reruns. Six cases are run once per model; no hidden SDK retries. Changes or service failures consume the existing allowance. Stop if the budget is exhausted or credentials are rejected. No paid judge model is used; local agent review grades the saved synthetic answers against rubrics withheld from the models.

Only public program requirements and explicitly fabricated progress/history are sent. No source DB reads, Clerk calls, actual athlete data, email or GMTM navigation are part of the comparison. OpenAI uses `store=False` and the official Responses endpoint; Anthropic uses its official messages endpoint. Existing keys may be delivered into the isolated test process memory over the existing SSH/Railway access, without printing or persisting their values. No remote credential files or Railway variables are changed.

## Completion and limits

Completion means the local adapter and accounting checks pass, the bounded live comparison is attempted and its actual outcomes are reported, with a next-model decision supported by the observed answers. If provider generation is unavailable, record the exact safe status and leave live acceptance open. A small synthetic sample does not establish production readiness, athlete outcomes, quotas at scale or a durable multi-instance billing limit. Process limits reset on restart; the evaluation runner must separately persist its reservation/attempt state.

No deployment, production model switch, database write, infrastructure operation, commit/push or unrelated checkout change is authorized by this batch. Root owns evaluation runner/report/state/handoff; Ampere owns provider/accounting implementation and focused tests; Halley owns synthetic fixtures; Herschel independently reviews execution boundaries.

Official references checked: [Luna capabilities and pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Responses creation and streaming fields](https://developers.openai.com/api/reference/python/resources/responses/methods/create).
