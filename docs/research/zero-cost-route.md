# Is there a zero-cost route whose request cap fits one unit-run?

Ticket: [#32](https://github.com/YuukiFST/harness-tally/issues/32).
Builds on: `free-openrouter-pair.md` (#27), `arm-wire-surface.md`, `arm-retry-and-native-usage.md`.
Retrieval date for every web claim: **2026-09-25** (server `Date` headers 14:29Z to 14:40Z, kept next to each capture).
Question: which $0 route (no card, no purchase) serves OpenAI-compatible streaming chat completions with tools and `tool_choice` to both arms, with a documented request cap at or above what one unit-run needs?

## Headline

1. **Nobody has measured requests per unit-run yet.** The only per-run count available comes from a scripted mock: pi 5 requests, opencode 6 (5 agent steps plus 1 title call). The mock decided the step count, so it says nothing about a real Finn unit. Spec 11 assigns this number to the pilot (§5.3).
2. **One route has a documented daily cap that covers any plausible unit: NVIDIA build.nvidia.com**, at "Up to 40 rpm" and "10,000 requests per day". It also serves the exact pair chosen in #27 (`nvidia/nemotron-3-super-120b-a12b`, `google/gemma-4-31b-it`).
   Its caveats: the figure is site copy, not an API doc; it is qualified with "Rate limits may vary by model and traffic from other users may cause throttling"; and the published per-model OpenAPI schema does not list `tools` or `tool_choice`.
3. OpenRouter's free tier (50/day) fits only if a unit needs 50 requests or fewer. Every other candidate is ruled out by a card requirement, a token cap that one opencode unit uses up, a request cap below 50/day, a cap that is not published, or retirement.
4. **Spec 11 lets a construction span quota windows only at unit boundaries.** A single unit-run cannot be split: a mid-run 429 discards the construction.

No completion request was sent. All web access was unauthenticated GETs of docs, catalogue pages and one model list (about 30 requests).

## Method

- Local evidence: harness-bench `layer1/data/runs.jsonl` and `records.jsonl` (the Layer 1 mock probe, 2026-08-28), spec 11 at commit `9c0fe11`, `CONTEXT.md`, harness-bench issues #33 and #34, and this repo's earlier research notes.
- Web: each provider's own docs, fetched with `curl` into `captures/zero-cost-route/docs/`, one `.headers` file per page. Markdown twins (`.md`, `.md.txt`) were used where the provider serves them. Where a table is rendered client-side, values were read from the page's embedded JSON (Groq, build.nvidia.com).
- To regenerate: re-run the `curl -sSL -A "Mozilla/5.0" -D <f>.headers -o <f> <url>` commands. The URLs are in the table in §2.

## 1. Requests per unit-run, and the total budget

### 1.1 What a unit and a unit-run are

- A **unit** is "one part of the specification handed to an arm as one prompt ... the features of one stage of the reference build". There are at least six units (harness-bench `CONTEXT.md`, "Unit").
- The arm is "invoked once per unit, as a fresh process" (spec 11 @9c0fe11, line 25). Every request between launch and exit belongs to that unit (line 69). A **unit-run** is therefore one arm process working on one unit.
- The matrix is 2 arms × 2 tiers × n = 3, giving **12 constructions and 12·k unit-runs, plus discards** (lines 126-128). k ≥ 6 (line 24, §5.4).
- The pilot is the first 2 units × 2 arms × primary tier × n = 3, which is **12 unit-runs** (line 133).
- **Total at k = 6: 72 + 12 pilot = 84 unit-runs.** 48 of them are on the primary tier (36 matrix + 12 pilot) and 36 on the robustness tier. At k = 9: 108 + 12 = 120.
- Total requests = 84 × R, where **R = requests per unit-run, which has not been measured**.

### 1.2 What is known about R

| Source | pi 0.80.10 | opencode 1.17.9 | What it measures |
|---|---|---|---|
| Layer 1 mock probe, `runs.jsonl` (isolated profile) | 5 | 6 | A mock scripted to "four tool calls, then a final text answer, so five agent-loop requests per run" (harness-bench `docs/spec/41-layer1-request-shape.md:44`). The step count comes from the script, not the model |
| `records.jsonl`, opencode run | – | request 0 is `request_role: auxiliary`, 0 tools | opencode's title call. `arm-wire-surface.md:202-206`: a title call is made on every run unless `--title` is passed, and with `--title` there are 2 requests where there were 3 |
| Side-calls | +1 per compaction, after the loop (`arm-wire-surface.md:97-103`) | +1 per compaction, mid-loop (`arm-wire-surface.md:208-209`) | Only fire on long histories |
| Retries | up to 3 extra per failing turn (`arm-retry-and-native-usage.md:9`) | **no cap** (`arm-retry-and-native-usage.md:11-14`) | Only on errors |
| Spec 11 §5.2 (line 129) | "unknown until the pilot measures how many requests a unit takes" | same | – |
| DeepSWE leaderboard, #33 comment | 61-268 steps per task | same | Different agent, different task. Spec 11 line 129 says it "is not carried over" |

So per arm, **R = agent steps + compactions + retries (+1 title call for opencode without `--title`)**, and the agent step count for a Finn unit is unknown.
Below, routes are judged against a range. The low end is 5-6 requests (the probe). The illustrative high end is ~270, taken from DeepSWE only as a scale marker.

### 1.3 Tokens, for routes capped by tokens

On the mock probe, opencode's first request is 6659 `cl100k_base` tokens and pi's is 1228 (`report.md`, "First request, isolated environment"). Each later step resends the whole history, and that history only grows.
The floor for one unit is therefore about R × 6.7K input tokens for opencode (≈ 200K at R = 30) and R × 1.2K for pi, before any file content is read.
These are proxy-tokenizer counts, not the gateway's own counts (report.md header).

## 2. The candidates

"Card" means a payment method is required to reach the free quota.

| Route | Documented request cap | Documented token cap | Card / phone | Serves the #27 pair? | Verdict |
|---|---|---|---|---|---|
| **NVIDIA build.nvidia.com** (`https://integrate.api.nvidia.com/v1`) | "Up to 40 rpm", "10,000 requests per day" (site copy `rateLimits`, embedded in `nvidia-build-super.html` and `nvidia-build-gemma4.html`), "Rate limits may vary by model and traffic from other users may cause throttling" | none published | "free access to NIM API endpoints for prototyping" for Developer Program members (`nvidia-nim-faq.html`). Card: none mentioned. Phone: **UNVERIFIED** | **Yes, both**: `nvidia/nemotron-3-super-120b-a12b` and `google/gemma-4-31b-it` are in `GET /v1/models` (`nvidia-models.json`), both labelled "Free Endpoint" | **Fits** on requests for any R up to ~10,000/day |
| **OpenRouter `:free`** | 20/min, 50/day under 10 credits purchased (`free-openrouter-pair.md` §1) | none | no card for the 50/day tier | Yes (#27) | **Fits only if R ≤ 50** (one unit-run per day, and nothing else can use the account that day) |
| Google AI Studio / Gemini API (`https://generativelanguage.googleapis.com/v1beta/openai/`) | **not published**: "can be viewed in Google AI Studio" (`gemini-rate-limits.md:1-5`). RPD resets "at midnight Pacific time", per project (`:20-21`) | not published | Free tier = "Active project or free trial" (`:68`), no card | gemma-4-31b-it yes, free only, with no paid tier on Gemini (`gemini-gemma.md:10`, `gemini-pricing.md:1291-1303`). No nemotron | **Unknown**. The cap is visible only in a logged-in dashboard. The free tier's data is "Used to improve our products" (`gemini-pricing.md:1303`) |
| Groq free plan | gpt-oss-120b / qwen3.8-27b: 30 RPM, **1K RPD** | **8K TPM, 200K TPD** (`groq-rate-limits.html`, "Free Plan Limits" tab) | **UNVERIFIED** | Neither model. Offers gpt-oss-120b (131,072 ctx, $0.15/$0.60) (`groq-models.md:23`) | **Does not fit**: 200K TPD is used up by about 30 opencode requests (§1.3), and an 8K TPM is barely above opencode's 6.7K first request. Cached tokens are excluded from the limits (`groq-rate-limits.md`), which is not enough to rescue it |
| Cerebras | 5 RPM, 1M TPD (`cerebras-rate-limits.md`, Free Trial tab) | 1M TPH/TPD | **Card required**: "\$5 in free credits after adding a verified payment method"; "no permanently free tier" (FAQ) | No | **Excluded** (card, and credits expire after 30 days) |
| Mistral La Plateforme ("Free mode") | not published: "within the limits shown on the Limits page" (`mistral-tier.html`, "Plan, usage, and limits") | not published | **UNVERIFIED** | No | **Unknown**, the cap is dashboard-only |
| SambaNova Cloud free tier | **20 RPM, 20 RPD** per model | 200K TPD | Free tier = "no payment method linked" | gemma-4-31B-it (preview), no nemotron (`sambanova-rate-limits.md`) | **Does not fit** (20/day) |
| Cloudflare Workers AI | 300 RPM for text generation (`cloudflare-limits.md:60`) | 10,000 Neurons/day free (`cloudflare-pricing.md:23`). `@cf/nvidia/nemotron-3-120b-a12b` costs 45,455 neurons per M input tokens, `@cf/google/gemma-4-26b-a4b-it` 9,091 (`:88`, `:92`) | Workers Free plan exists. Card: **UNVERIFIED** | A nemotron-3 120B and gemma-4-26b, not the 31b | **Does not fit**: 10,000 neurons buys ≈ 220K nemotron input tokens a day, about 30 opencode requests |
| Hugging Face Inference Providers | per-provider | **$0.10/month** for free users (`hf-pricing.md:11`) | no | via providers | **Does not fit**: $0.10 a month |
| GitHub Models | – | – | – | – | **Retired** on 2026-07-30: "The playground, model catalog, inference API ... are no longer available" (`github-models-billing.md`) |

### 2.1 NVIDIA in more detail (the only candidate that fits on request count)

- **Endpoint and ids.** `GET https://integrate.api.nvidia.com/v1/models` answered unauthenticated and lists both ids (`nvidia-models.json`). Each model's OpenAPI spec has a single path, `/chat/completions` (embedded in the model pages).
- **Context and output.** The site metadata gives `contextLength` 1048576 for nemotron-3-super and 262144 for gemma-4-31b-it (`specifications` in each page). The `max_tokens` schema has `minimum: 1` and `default: 1024`, with no published maximum. The context and output caps the hosted endpoint actually enforces are **UNVERIFIED**, which matters for #10.
- **Tools.** `modelCapability.functionCalling: true` on both, and the page config says `toolsEnabledWithReasoning: true`. However, the published `ChatCompletionRequest` schema lists only messages, temperature, top_p, max_tokens, stream, stop, seed and the penalties. **`tools`, `tool_choice` and `stream_options` are not in it.** Whether the endpoint accepts `tool_choice` (opencode sends it, #27) is **UNVERIFIED**.
- **Usage on streams.** The schema has a `UsageInfo` with prompt, completion and total tokens. Whether a final usage chunk arrives on a stream, and whether cached tokens are reported, is **UNVERIFIED**.
- **Paid list price.** NVIDIA does not sell these endpoints. For §6 cost, the paid twin prices recorded in #27 still apply (nemotron-3-super $0.08/$0.45, gemma-4-31b $0.09/$0.34 per 1M on OpenRouter, `free-openrouter-pair.md` §2).
- **Risks.**
  - The 10,000/day figure is marketing copy (`content/copy.yaml`), not an API reference, and it varies "by model". Whether it counts per model or per account is **UNVERIFIED**.
  - "Traffic from other users may cause throttling" means a 429 can come from load rather than from quota. Under spec 11 any 429 mid-unit discards the construction.
  - An NVIDIA forum moderator, quoted in a user reply, says free-tier limits depend "on model, use-case and the amount of current overall traffic" and cannot be raised (`nvidia-forum-374542.json`). This is a secondhand quote.
  - #34 saw other NVIDIA trial endpoints (nemotron-3-ultra, nemotron-3.5-lightning, reached through Zen) return overload 502s or hang. That was a different model through a different gateway, but the same trial infrastructure.
  - Access is governed by the "NVIDIA API Trial Terms of Service" (`nvidia-build-super.md:59`).
  - The schema declares a 402 `PaymentRequiredError`, "You have reached your limit of credits". Whether a free account still has a credit balance that runs out is **UNVERIFIED**.

## 3. Can one unit-run be split across quota windows?

**No. Constructions can be split across windows, unit-runs cannot.**

- Discard rule, spec 11 @9c0fe11 line 100: `discarded` = "any of #25's nine faults, **including a mid-run 429 (#34)**. Never repaired, never retried". Line 96: "A construction is `discarded` when any of its units is."
- Line 129: "A construction spans days when the quota says so; **the runner resumes at the next unit boundary**." The only pause spec 11 allows is between units.
- Line 25: each unit is one fresh process, and "No conversation carries across units". Pausing mid-unit would mean holding a live arm process past a quota reset. Nothing in the spec provides for that, and the wall-clock limit per unit (line 112) would keep counting.
- The arms will not wait politely. pi retries a 429 up to 3 times with 2/4/8 s backoff, and opencode retries without limit (`arm-retry-and-native-usage.md:9-14`). An exhausted window turns into a 429 and a discard, not a pause.

Consequences:

1. The route has to have at least R requests (and R's worth of tokens) **left in the current window when a unit starts**. The runner needs to check the remaining quota before launching each unit. OpenRouter exposes this through `GET /api/v1/key`, and Groq and SambaNova through `x-ratelimit-*-requests(-day)` headers. For NVIDIA and Gemini, no documented quota-read endpoint was found.
2. **The per-minute cap also counts as a mid-run 429.** A per-minute cap is safe only if the arm cannot exceed it. A sequential loop at one request per few seconds stays under 40 RPM. opencode's title call runs concurrently with step 0 (`arm-wire-surface.md:236`); `--title` removes it.
3. Tiers can share a route only if their counters are independent or both fit together. Whether OpenRouter's and NVIDIA's daily counters are per account or per model is **UNVERIFIED**.

## 4. What this means for scheduling

- NVIDIA at 10,000/day and R ≤ 270: ~37 unit-runs per day. All 84 fit in about 3 days on request count (wall clock is not modelled here).
- OpenRouter at 50/day and R ≤ 50: 1 unit-run per day, so 84 days at k = 6. At R > 50 it cannot run at all.
- Either way, the first number owed is R from the pilot. With R unknown, the pilot has to run on a route whose cap is far above any plausible R, which today means NVIDIA if its `tool_choice` and streaming usage hold up.

## UNVERIFIED

1. R (requests per real unit-run) for either arm. Only the scripted mock figure (5 / 6) exists.
2. NVIDIA: whether the endpoint accepts `tools`, `tool_choice` and `stream_options`; whether a streaming usage chunk and cached-token counts are sent; the context and output caps it enforces; whether 10,000/day is per model or per account; whether sign-up needs a phone; whether a credit balance applies (402 "limit of credits"); the Nemotron-3-Super reasoning default and `response.model` echo.
3. Gemini API free-tier RPM/RPD/TPM for gemma-4-31b-it (dashboard-only).
4. Mistral Free-mode limits (dashboard-only) and sign-up requirements.
5. Groq: card/phone at sign-up; whether a request larger than the 8K TPM is rejected outright.
6. Cloudflare Workers Free: card at sign-up; tool-calling support of `@cf/nvidia/nemotron-3-120b-a12b`.
7. OpenRouter: whether the 50/day counter is shared across free models, and whether failed requests count (carried from #27).
