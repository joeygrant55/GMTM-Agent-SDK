# SPARQ model strategy — September 7, 2026

Recommendation: establish a quality baseline with the current integration, evaluate Sonnet 5 for the main assistance role and GPT-5.6 Luna for routine work, and add Gemini only when a video feature needs it. Keep deterministic business facts in code. This is a source-backed selection and economics assessment, not a cross-model performance benchmark or a deployed routing change.

Subsequent live result: a local opt-in Luna adapter is now implemented for combine help, with bounded call accounting, and the [six-case synthetic comparison](luna-combine-evaluation-2026-09-07.md) completed on both Luna and the existing Sonnet 4.6 path. Luna is the leading routine-help pilot candidate from this small sample. Its six answers cost an estimated $0.0036654 versus $0.154974 for the current Sonnet path; Sonnet made a redundant context-tool round trip in every case. This is evidence about these two implemented paths, not a Sonnet 5 test or a universal model ranking. Production settings remain unchanged. The earlier access notes below record the preceding discovery steps.

Access update later September 7: Anthropic and Gemini keys already exist in SPARQ's Railway backend and authenticated model-information checks succeeded. OpenAI also has a stored key, but the API rejects it as `invalid_api_key`. Anthropic is the only implemented model provider; Gemini still needs an adapter, and Luna needs a working OpenAI credential. Metadata access does not establish generation quota or billing. See the [verified access inventory](../../.sammy/handoffs/2026-09-07-provider-access-inventory.md); availability statements below should be read with this update.

Mac mini follow-up: Hermes's separate OpenAI key successfully authenticated for Luna model metadata, and its OpenRouter key passed the authenticated current-key endpoint. Existing OpenAI access is therefore available for a future authorized test, while the Railway binding remains invalid. No keys were copied, no provider adapter was added and no generation was run. The mini's Anthropic environment key returned 401, distinct from the working Railway key. See the [mini provider access handoff](../../.sammy/handoffs/2026-09-07-mini-provider-access.md).

## Match intelligence to the work

| SPARQ workload | Intelligence needed | Recommended candidate / approach | Acceptance condition |
|---|---|---|---|
| Identity, permissions, required fields, submission counts, deadlines, SPARQ score calculation | Exact authoritative rules | Deterministic services; zero model calls | A model cannot change ownership, invent completion or certify a measurement |
| Short combine explanations, missing-item guidance, classification, formatting, simple draft edits | Narrow instruction following on supplied facts | GPT-5.6 Luna; Haiku 4.5 as a simpler same-provider alternative | Correct activity and next step, no invented requirement, concise useful answer |
| Personalized next steps, recruiting profile explanations, coach-message drafts | Reason across several verified facts and preferences | Sonnet 5; compare GPT-5.6 Terra | Useful personalization without unsupported claims; athlete reviews outbound drafts |
| Program comparisons, opportunity research, multi-source evidence synthesis | Strong reasoning with bounded retrieval | Sonnet 5 first; Sol or Opus 5 for difficult cases | Sources corroborate claims; missing evidence stays unknown; strict search/job budget |
| Partner reports and club/NGB campaign setup | Mostly deterministic aggregation plus moderate synthesis | SQL/analytics and templates, then Luna/Sonnet for narrative | Model uses reconciled counts; program outcomes stay distinct from activity |
| Film summaries, locating relevant clips, qualitative filming feedback | Video understanding and temporal context | Gemini 3.8 Flash; compare 3.5 Flash-Lite for cheaper passes | Evaluate on athlete-authorized labeled clips; preserve uncertainty |
| Verified timing, exercise validity and selection/eligibility decisions | Measurement systems and organizer rules | Device evidence, calibration and qualified review | A video-language model's interpretation is not a verified SPARQ result |
| Difficult engineering, architecture and strategic audits | Highest reasoning where each result is valuable | Astra or Fable 5.1 in the internal agent workflow | Reviewed implementation/analysis with tests; separate from per-athlete serving cost |

These are proposed workload assignments, not measured intelligence rankings. Use existing laptop agents for engineering and operations; athlete-serving APIs need their own availability, usage accounting and budgets. Voice can later reuse the same grounded assistance layer behind transcription and speech output; it does not require expanding the initial combine launch scope.

## Current prices and shortlist

Standard uncached text input/output, USD per million tokens, checked September 7. Account access and actual rate limits have not been verified for new candidates.

| Model | Input | Output | Decision |
|---|---:|---:|---|
| GPT-5.6 Luna | $0.20 | $1.20 | Primary economy candidate |
| Claude Haiku 4.5 | $1.00 | $5.00 | Lower integration effort within Anthropic |
| Claude Sonnet 4.6 | $3.00 | $15.00 | Existing live-tested baseline |
| Claude Sonnet 5 | $2.00 | $10.00 | Primary main-assistant candidate |
| GPT-5.6 Terra | $2.00 | $12.00 | Main-assistant challenger |
| GPT-5.6 Sol | $4.00 | $20.00 | Difficult research/planning candidate |
| Claude Opus 5 | $5.00 | $25.00 | Difficult research/planning candidate |
| GPT-6 Astra / Claude Fable 5.1 | $10.00 | $50.00 | Exceptional work and internal engineering |
| Gemini 3.8 Flash | $0.75 | $3.75 | Balanced/video candidate; temporary price |
| Gemini 3.5 Flash-Lite | $0.30 | $2.50 | Economical video/extraction challenger |
| Mistral Small 4 (`mistral-small-2603`) | $0.15 | $0.60 | Later inexpensive challenger |
| Grok 4.6 | $2.00 | $6.00 | Later reasoning/search challenger |

Official pricing: [OpenAI](https://developers.openai.com/api/docs/pricing), [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing), [Google](https://ai.google.dev/gemini-api/docs/pricing), [Mistral](https://docs.mistral.ai/inference/pricing), [xAI](https://docs.x.ai/developers/pricing). Model-specific guidance: [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [Sonnet 5](https://platform.claude.com/docs/en/models/sonnet-5/overview).

Important pricing qualifications:

- Sonnet 5's $2/$10 rate is now standard. Its newer tokenizer can produce approximately 30% more tokens for the same text than Sonnet 4.6, so a lower token price does not directly equal the same percentage saving per answer. Adaptive thinking defaults on; explicitly tune effort for the workload during evaluation. [Pricing/tokenizer](https://platform.claude.com/docs/en/about-claude/pricing), [migration behavior](https://platform.claude.com/docs/en/models/sonnet-5/overview).
- Gemini 3.8 Flash's rate doubles to $1.50/$7.50 on January 1, 2027. Paid and free-tier data treatment differs; use an appropriate paid configuration for athlete information. [Current-model guide](https://ai.google.dev/gemini-api/docs/latest-model), [pricing/data treatment](https://ai.google.dev/gemini-api/docs/pricing).
- Sol's current $4/$20 rate is promotional and available at least through November 21, 2026; recheck it for year-end budgets. [OpenAI pricing](https://developers.openai.com/api/docs/pricing).
- Reasoning tokens, search/tool calls, repeated turns, retries and video/audio processing change the bill. Long-context premiums also apply to some models. Batch can reduce asynchronous processing cost; caching has write/storage costs and requires useful reuse. Budget from actual provider usage, not visible words. [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).

Mistral Large 3 ($0.50/$1.50) and DeepSeek V4 Flash ($0.22/$0.66 off-peak, $0.44/$1.32 peak) also merit later synthetic testing. Their catalog prices are attractive, but another production integration needs a demonstrated quality/cost benefit. [Mistral](https://docs.mistral.ai/inference/pricing), [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/). Grok Bot access on a laptop is separate from a metered, tested xAI API integration.

Gemini supports direct video understanding; default static sampling can miss fast athletic movements. Clip summaries and recording assistance should be evaluated separately from calibrated measurements. [Google video documentation](https://ai.google.dev/gemini-api/docs/video-understanding).

## Economics for Charles's first 500 athletes

Illustration only: 500 athletes × 20 answered questions = 10,000 answers, each using 5,000 input and 500 output tokens in one call. This is a cohort scenario, not an observed usage forecast or monthly bill. It excludes extra reasoning, search, retries, cache effects, media, infrastructure and taxes, and uses equal token counts despite tokenizer differences.

| Routing scenario | Illustrative text-token cost |
|---|---:|
| All current Sonnet 4.6 | $225.00 |
| All Sonnet 5 | $150.00 |
| All GPT-5.6 Luna | $16.00 |
| 80% directly to Luna, 20% directly to Sonnet 5 | $42.80 |
| Every question starts on Luna; 20% also call Sonnet 5 | $46.00 |

Formula: `(input_tokens × input_rate + output_tokens × output_rate) / 1,000,000`, summed over every model turn and attempt. The [machine-readable scenarios](model-cost-scenarios-2026-09-07.json) preserve rates, sources, assumptions and arithmetic. A 30% token-count increase on Sonnet 5 would make its same-text scenario about $195 before thinking, rather than $150. That is a sensitivity calculation, not a measured conversion.

At this cohort size, engineering time and athlete completion are likely more valuable than extracting the final few dollars of model savings. Establish a working experience first, then measure whether cheaper routes preserve completion and retention. Track cost per useful answer and per athlete who completes the intended step, alongside total cohort spend.

## What the repo actually does

All seven current Anthropic request callsites use Sonnet 4.6. There is no implemented multi-model router, token-cost ledger or cache policy. [Combine help](../../backend/combine_help_api.py), [recruiting chat](../../backend/agent_api.py), [artifact drafting](../../backend/artifacts_api.py), [enrichment](../../backend/enrichment_worker.py), [deep research](../../backend/profile_api.py).

Combine help is the bounded path: three model turns at most, 1,200 output tokens per turn, 30-second model deadline, SDK retries disabled, one in-flight request per caller, no search and a minimized source context. Actual call cost is not currently recorded.

The larger expense/reliability risk is recruiting bootstrap: an initial search plus 8–12 requested program enrichments can mean 9–13 model calls. The generated target count is not enforced, and concurrent calls can repeat bootstrap work. Legacy recruiting chat also allows more turns and broader history than combine help. The restricted acceptance server does not start these workflows. [Worker](../../backend/enrichment_worker.py), [bootstrap](../../backend/workspace_bootstrap.py).

## Next implementation sequence

1. Add privacy-safe usage metadata: model/prompt version, actual input/output/cache/reasoning tokens as exposed by each provider, search usage, latency, completion/error/cancellation and estimated cost with a versioned rate table. Keep raw personal prompts and answers out of operational logs.
2. Centralize workload policy with allowed provider/model, tools, input/output limits, reasoning effort, timeout, one bounded fallback and per-athlete/program spend admission. Preserve all existing identity and source restrictions; a failed source read must not trigger a stronger model on incomplete data.
3. Deduplicate and cap bootstrap/enrichment jobs. Cache public program research by program/sport/source freshness and reuse it across athletes; generate personal interpretations separately. Budget both direct routing and escalation attempts.
4. Compare Sonnet 4.6, Sonnet 5 and Luna on the same synthetic/public SPARQ cases, with known correct facts and a blinded human rubric. Haiku is a useful same-provider alternative if integration simplicity wins. Add Gemini on labeled, authorized video cases when that feature is ready.
5. Release a candidate only after it passes the critical correctness cases and improves cost/latency without materially reducing usefulness. Keep a pinned model/prompt version and rollback baseline. Widen the initial pilot gradually under existing launch approval boundaries.

The 24-case first benchmark should cover: focused highlights and full-event questions; zero, partial, stale, unlinked and unavailable progress; 20/40-yard mismatch; both shuttle directions; video-only squat; deadline ambiguity; membership/qualification unknowns; source/history injection; unsupported external actions; malformed tool arguments; long answers; provider interruption/cancellation; private-data exclusion; missing evidence in college matches; constrained outreach edits; and grounded partner reporting. Use multiple phrasings and repeated runs for nondeterministic cases. Synthetic unlinked/junior cases do not substitute for authorized live junior/guardian acceptance.

Proposed release gates: zero critical false eligibility/completion/ownership assertions on the reviewed suite; at least 95% correct required facts and useful next steps; valid bounded responses; and measured p50/p95 latency and cost per accepted answer. These are proposed thresholds, not achieved benchmark results. A model's self-reported confidence is insufficient to choose an escalation.

This assessment does not authorize new provider data transfers, paid subscriptions, account changes or deployment. Today's explicit live-data approval applies to at most five local Sonnet 4.6 help attempts; candidate comparisons described here have not been run.
