# Which pair of free OpenRouter models both arms run on

Ticket: [#27](https://github.com/YuukiFST/harness-tally/issues/27), part of [#1](https://github.com/YuukiFST/harness-tally/issues/1).
Feeds: #26 (wire capture), #8 (profile rows), #10 (max_tokens contract), #9 (fault list).
Retrieval date for every claim: **2026-09-25** (server `Date` headers 13:29Z to 13:32Z).
Question: which two `:free` models on `https://openrouter.ai/api/v1/chat/completions` replace `mimo-v2.5-free` (primary) and `hy3-free` (robustness), such that pi 0.80.10 and opencode 1.17.9 can both drive them?

## Headline

**Recommended: primary `nvidia/nemotron-3-super-120b-a12b:free`, robustness `google/gemma-4-31b-it:free`.**
Both list `tools` and `tool_choice`, 262144 context, one first-party free endpoint each, a paid twin with a list price, and they are the two oldest tool-capable free listings (2026-03-11 and 2026-04-02).

**The binding constraint is not the model, it is the quota: 50 free-model requests per day per account** for an account that has bought less than 10 credits, 20 per minute (`meta/docs-api_reference_limits.md`).
That is roughly 48x less than the ~100 requests/hour spec 11 §5 was sized on (#34).

No completion request was sent: `OPENROUTER_API_KEY` is unset in this environment.
Every completion-level fact below (usage frame, `response.model`, error shapes, accepted `max_tokens`) is **UNVERIFIED** and is the live probe owed to #26.

## Method

- Catalogue: `GET /api/v1/models` and `GET /api/v1/models/{id}/endpoints` for every `:free` id and for the same id with `:free` stripped (the paid twin), unauthenticated.
  One command regenerates all of it: `bash docs/research/captures/free-openrouter-pair/catalogue.sh`, which also writes the table in `meta/summary.md` via `summarize.py`.
- Docs: each page fetched as Markdown (`https://openrouter.ai/docs/<page>.md`) with its response headers, saved under `captures/free-openrouter-pair/meta/docs-*.md`.
- Request count: 0 chat completions, 0 authenticated requests, no 429.
  Roughly 45 unauthenticated catalogue GETs (the models list four times while fixing the script, 36 endpoint lookups once, 3 by hand) and 10 doc pages.

## 1. Free-tier limits

From [Limits](https://openrouter.ai/docs/api_reference/limits), accessed 2026-09-25 (`meta/docs-api_reference_limits.md`):

| Credits purchased, all time | Requests/min | Requests/day |
|---|---|---|
| less than 10 | 20 | **50** |
| at least 10 (granted from 9) | 20 | 1000 |

- The limit applies to any model id ending in `:free`, "regardless of account status".
- The daily counter is one per account: `GET /api/v1/key` returns a single `free_model_daily_requests {used, limit, remaining}` for the current UTC day.
  The same page says "Making additional accounts or API keys will not affect your rate limits, as we govern capacity globally" and also "we do however have different rate limits for different models".
  Whether the 50/day is shared across all free models or counted per model: the single counter implies shared; per-model behaviour is **UNVERIFIED**.
- What counts: "free-model requests recorded". Whether a request that ends in 4xx, 429 or a mid-stream error is recorded is **UNVERIFIED**.
- A negative credit balance returns 402 "including for free models"; the in-flight spending budget "does not apply to requests to free models".
- A 429 for a platform limit carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`; successful responses carry no `X-RateLimit-*`.
  A 429 can also come from the upstream provider, with `error.metadata.provider_code`.
  Documented body: `{"error":{"code":429,"message":"Rate limit exceeded","metadata":{"error_type":"rate_limit_exceeded"}}}`.
- A rate limit hit after the stream started arrives as an SSE chunk with `error:{code:429,...}` and `finish_reason: "error"` on an HTTP 200.
- [Provider Logging](https://openrouter.ai/docs/guides/privacy/provider-logging) (`meta/docs-guides_privacy_provider-logging.md`): the account has a separate "may train on prompts" setting for free models; if it is off, providers that train are not routed to. Whether Nvidia's or Google AI Studio's free endpoint is excluded by that setting is **UNVERIFIED**.

## 2. Candidates

All 18 `:free` ids are in `meta/summary.md`. `expiration_date` is `null` on every one of them. Shortlist:

| id | listed | ctx | max out | tools / tool_choice | free endpoint (quant, 1d uptime) | paid twin list $/1M in/out |
|---|---|---|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` | 2026-03-11 | 262144 | 235929 | yes / yes | Nvidia (unknown, 97.8%) | 0.08 / 0.45 (2 hosts, fp8 and bf16) |
| `google/gemma-4-31b-it:free` | 2026-04-02 | 262144 | 32768 | yes / yes | Google AI Studio (unknown, 99.6%) | 0.09 / 0.34 (15 hosts) |
| `google/gemma-4-26b-a4b-it:free` | 2026-04-03 | 262144 | 32768 | yes / yes | Google AI Studio (unknown, 99.7%) | 0.09 / 0.30 |
| `poolside/laguna-s-2.1:free` | 2026-07-21 | 262144 | 32768 | yes / yes | Poolside (fp4, 99.9%) | 0.09 / 0.18 (Poolside only, fp4) |
| `qwen/qwen3.8-27b:free` | 2026-08-14 | 262144 | 235929 | yes / yes | ModelRun (fp4, 98.1%) | 0.42 / 3.00 (16 hosts, 1.8-4.4 out) |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | 2026-06-04 | 1000000 | 65536 | yes / yes | Nvidia (unknown, 99.0%) | 0.60 / 2.40 |
| `cohere/north-mini-code:free` | 2026-06-17 | 256000 | 64000 | yes / yes | Cohere (unknown, 98%) | **none** |
| `z-ai/glm-5.2:free` | 2026-06-16 | **32768** | 29491 | **no / no** | Decart (fp4, 100%) | 0.65 / 2.04 (many) |
| `liquid/lfm-2.5-2.6b:free` | 2026-08-11 | 65536 | **8192** | yes / yes | Liquid (fp8) | none |

Sources: `meta/models.json` (`created`, `context_length`, `top_provider.max_completion_tokens`, `supported_parameters`, `pricing`), `endpoints/*.json` (provider, quantization, uptime).
"List price" is the paid entry's model-level `pricing` in `/api/v1/models`; per-host prices differ and are in `meta/summary.md`.

Per-item answers for the two picks:

| Item | nemotron-3-super:free | gemma-4-31b-it:free |
|---|---|---|
| Tool calling | `tools`, `tool_choice` in `supported_parameters` | same |
| Streaming usage | Documented, not observed: usage is always sent in one final chunk before `[DONE]`; `stream_options.include_usage` is "deprecated and has no effect" ([Usage Accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)); that chunk carries a choice repeating `finish_reason` ([Streaming](https://openrouter.ai/docs/api_reference/streaming)). **UNVERIFIED** on the wire | same |
| Context vs arms | 262144 vs ~10K-token opencode first request | same |
| Max output | 235929, above opencode's 32000 and pi's 16384 | 32768, above both |
| Providers | 1 free endpoint (`nvidia`); `provider.only`/`allow_fallbacks:false` exist ([Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection)) but there is nothing to fall back to | 1 free endpoint (`google-ai-studio`) |
| `response.model` echo | **UNVERIFIED.** Docs: `model` is the model "that ends up being used"; `canonical_slug` is `nvidia/nemotron-3-super-120b-a12b-20230311` | **UNVERIFIED**; `canonical_slug` `google/gemma-4-31b-it-20260402` |
| Paid twin | `nvidia/nemotron-3-super-120b-a12b`, $0.08/$0.45 | `google/gemma-4-31b-it`, $0.09/$0.34 |
| Reasoning default | enabled, effort `medium` | disabled |
| Tokenizer | `Other` | `Gemma` |

## 3. Listing stability

- `expiration_date` is the documented "deprecation date for the model endpoint (null if not deprecated)" ([Models](https://openrouter.ai/docs/guides/overview/models), `meta/docs-guides_overview_models.md:178`); it is `null` on all 18 free ids and on the seven paid twins checked.
- [Free Variant](https://openrouter.ai/docs/guides/routing/model-variants/free): free variants "may have different rate limits or availability compared to paid versions". No doc states a notice period for withdrawing a free variant.
- [API Versioning](https://openrouter.ai/docs/api_reference/versioning): "models are added and removed by providers independently". Model removal is outside the breaking-change process.
- [Model Variants](https://openrouter.ai/docs/guides/routing/model-variants/overview): a `:free` id with no free entry does not fall back to the paid model; inference fails because there is no endpoint. A withdrawn free tier is therefore a hard failure, not a silent price change.
- The only positive signal available is age: `created` puts nemotron-3-super (2026-03-11) and gemma-4-31b (2026-04-02) as the longest-listed tool-capable free ids. Poolside's `laguna-s-2.1-free` on Zen is already `deprecated` on models.dev (#34, cited in `zen-wire-profile.md`).

## 4. Recommendation

- **Primary: `nvidia/nemotron-3-super-120b-a12b:free`.** Criterion: longest continuous free listing among tool-capable models, served first-party, and the only one whose max output (235929) leaves both arms' default caps untouched.
- **Robustness: `google/gemma-4-31b-it:free`.** Criterion: most different from the primary on every axis the tier is meant to vary (vendor, tokenizer, dense vs hybrid MoE, reasoning off by default) while keeping the same context, tool support and a paid twin; second-longest listing, first-party served.
- First fallback for either tier: `poolside/laguna-s-2.1:free` (coding-agent model, cleanest twin: same provider, same fp4 quant, one price), held back for its withdrawal signal on Zen.

Rejected:

- `z-ai/glm-5.2:free`: no `tools` in `supported_parameters`, and a 32768 window cannot hold opencode's ~10K-token first request plus its 32000 `max_tokens`.
- `cohere/north-mini-code:free`, `dots-studio/dots-3-note-preview:free`, `liquid/lfm-2.5-2.6b:free`: no paid twin, so no derived cost (liquid also has 8192 max output).
- `qwen/qwen3.8-27b:free`: newest of the large models, served by a third-party fp4 host, reasoning on at `xhigh` by default, and its list price ($0.42/$3.00) belongs to hosts spanning $1.80-$4.40 output.
- `thinkingmachines/inkling*:free`: no `tool_choice`, which opencode sends.
- `inclusionai/ling-3.0-flash-*:free`: finance/health-domain tunes; `-sante` has no paid twin.

## 5. Consequences

1. **Spec 11 cannot run as sized on 50 requests/day.** The pilot alone (2 units x 2 arms x n=3) is 12 unit-runs sharing one daily counter with the robustness tier. At an unmeasured requests-per-unit, the run spans weeks. The only documented lever is 10 purchased credits (1000/day), which #25 ruled out; this goes back to the product owner, not to this ticket.
2. **#26 wire capture** must spend its budget from the same 50/day, and needs a key in the environment. It must establish: the usage chunk shape and whether it repeats `finish_reason`; whether `: OPENROUTER PROCESSING` comments appear; what `response.model` holds (requested id, id without `:free`, or `canonical_slug`); the 429 headers and whether a 429 counts against the day; whether `max_completion_tokens` and `store: false` from pi are accepted (the free endpoints list only `max_tokens`).
3. **#8 profile rows** (documented, unverified): `force_include_usage` false (usage always sent), `swallow_usage_frame` false, `usage_carries_finish_reason` true, `parse_past_done` unknown. Field names `prompt_tokens_details.cached_tokens`, `cache_write_tokens`, `completion_tokens_details.reasoning_tokens`, plus an extra `usage.cost`.
4. **#10 max_tokens cap:** published caps 235929 (primary) and 32768 (robustness). Forcing the published cap on the primary would ask for 235929 tokens per request; the contract needs a run value below it. pi's `contextWindow` in `models.json` must be 262144 (the free entry), not the paid twin's figure, or its clamp is wrong.
5. **#9 fault list** gains: 429 `rate_limit_exceeded` with `X-RateLimit-*` (daily exhaustion must abort the run for the day, not retry); upstream-provider 429 with `metadata.provider_code`; mid-stream error chunk with `finish_reason: "error"` on HTTP 200; 402 on a negative balance; a withdrawn `:free` id failing with no endpoint (status **UNVERIFIED**); a routing refusal if the account's free-model training setting excludes the only endpoint.
6. **Both arms' retries and opencode's title call spend the 50.** opencode must run with `--title`, and arm-side retries on 429 (see `arm-retry-and-native-usage.md`) burn quota the proxy should stop.
7. **The `response.model` assertion (spec 11 §1)** cannot be equality with the request id until #26 records what OpenRouter echoes.
