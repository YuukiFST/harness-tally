# OpenRouter wire profile of `google/gemma-4-31b-it:free` and `qwen/qwen3.8-27b:free`

Ticket: [#26](https://github.com/YuukiFST/harness-tally/issues/26), part of [#1](https://github.com/YuukiFST/harness-tally/issues/1).
Feeds: #8 (profile rows), #9 (fault list), #10 (max_tokens contract).
Retrieval date for every claim: **2026-09-25** (server `Date` headers 16:05:23Z to 16:07:03Z).
Question: what does `https://openrouter.ai/api/v1/chat/completions` send back today for the primary `google/gemma-4-31b-it:free` (Google AI Studio) and the robustness model `qwen/qwen3.8-27b:free` (ModelRun `modelrun/fp4`)?

## Headline

**The first completion got HTTP 429 from Google AI Studio's shared free pool, so every live completion probe stopped there, as the quota rules require.**
One chat completion was sent out of a budget of 24.
Nothing reached `qwen/qwen3.8-27b:free`.
The 429 was not an account limit.
The body says `"limit_source":"upstream_provider_shared_pool"`, and the account counter stayed at `used: 0` before and after (`meta/key-*.txt`).

Established from the wire today:

- The upstream-pool 429 shape (item 8, partly).
- `/key`, `/models/user`, an upstream 429 and a `/generation` lookup do not move `free_model_daily_requests.used` (item 12).
- `Accept-Encoding: identity` is honoured and needed (item 10).
- How the serving provider is named on an error, and that a failed generation id cannot be looked up (item 11, partly).

Items 1-7, item 9, the unknown-model and over-cap halves of item 8, and the provider-pin half of item 11 are **UNVERIFIED** on the wire for both models.
Where OpenRouter's docs state the answer, the documented answer is given and marked as documented, not observed.

## Method

- Client: `curl 8.21.0` from Git Bash on Windows 10, default curl `User-Agent`, `Accept-Encoding: identity` on every OpenRouter request.
- One command regenerates everything: `bash docs/research/captures/openrouter-wire-profile/capture.sh`.
  It writes the request bodies (`make_requests.py` into `requests/`), runs the probes, and writes `meta/summary.md` with `summarize.py`.
  A re-run spends up to 17 of the day's 50 free-model requests.
- Guards in `capture.sh`: at most 24 completions (counted in `requests.log`), at least 6 s from the end of one completion to the start of the next, and a hard stop on any 429 (`STOP_429` marker file; a re-run clears it).
- The key is read from `OPENROUTER_API_KEY` or the Windows user env var and piped to curl on stdin (`-H @-`), so it is neither on a command line nor on disk.
  No request header file is saved; each capture lists the headers sent with `Authorization (not recorded)`.
- Each completion is saved as `NN-<model>-<probe>.txt` (request body, all response headers, raw body) with the raw body alone as `.txt.body`.
  Bodies are kept with HTTP chunk framing (`curl --raw`), byte for byte as received.
- Request shapes, taken from `arm-wire-surface.md` §2-3 and §7:
  pi-shaped probes send `max_completion_tokens`, `store: false`, `stream_options.include_usage: true`, system + user + two tools (`read`, `bash`);
  opencode-shaped probes send `max_tokens`, `tool_choice: "auto"`, `stream_options.include_usage: true`.
  Planned per model: p1 pi stream with `include_usage`, p2 without `stream_options`, p3 single tool call, p4 parallel tool calls, p5 non-streaming, p6 `max_tokens` at the published cap, p7 cap + 1, p8 `provider: {only: [<slug>], allow_fallbacks: false}` (`google-ai-studio`, `modelrun/fp4`); then one unknown model id.
  All 17 bodies are in `requests/`; only `gemma-p1-pi-stream-usage.json` was sent.
- Docs fetched as Markdown with headers, not counted as requests:
  `meta/docs-api_reference_errors-and-debugging.md`, `meta/docs-guides_best-practices_reasoning-tokens.md`, `meta/docs-api_api-reference_generations_get-request-_-usage-metadata-for-a-generation.md`.
  Also cited: the pages already saved under `captures/free-openrouter-pair/meta/` on the same day.

### Request count

| # | Server time (UTC) | Request | Status | Counts as completion |
|---|---|---|---|---|
| 1 | 16:05:23 | `GET /api/v1/key` | 200, `used: 0` | no |
| 2 | 16:05:24 | `GET /api/v1/models/user` | 200 | no |
| 3 | 16:05:25 | `GET /api/v1/key` | 200, `used: 0` | no |
| 4 | 16:05:26 | `POST /chat/completions`, gemma p1 | **429** | **yes (1 of 24)** |
| 5 | 16:05:37 | `GET /api/v1/key` | 200, `used: 0` | no |
| 6 | 16:05:43 | `GET /api/v1/key` | 200, `used: 0` | no |
| 7 | 16:05:44-45 | unauthenticated `GET /models/google/gemma-4-31b-it:free/endpoints`, twice | 200 | no |
| 8 | 16:06:10 | `GET /api/v1/generation?id=gen-1790352326-DF6TqpPSdIpM5qFJU7Bi` | 404 | no |
| 9 | 16:06:31 | same lookup, 21 s later | 404 | no |
| 10 | 16:07:03 | `GET /api/v1/key` | 200, `used: 0` | no |

**Completions spent: 1 of 24. Stopped at the first 429 (item 1, gemma p1). Counter before 0/50, after 0/50.**
Rows 8-9 were run by hand after the script; `capture.sh` now does the same lookup from the `X-Generation-Id` header, so a re-run reproduces it.

## Probes

### PROBE 01 — 2026-09-25 — `google/gemma-4-31b-it:free`, pi-shaped stream

Request: `requests/gemma-p1-pi-stream-usage.json` (system + user "Reply with the single word: ok" + 2 tools, `stream: true`, `stream_options.include_usage: true`, `max_completion_tokens: 64`, `store: false`).
Status: **429**, time to first byte 0.44 s.
Verbatim response (the `set-cookie` and `Permissions-Policy` values are shortened here, full in the capture):

```
HTTP/1.1 429 Too Many Requests
Date: Fri, 25 Sep 2026 16:05:26 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
Access-Control-Allow-Origin: *
Access-Control-Expose-Headers: X-Generation-Id,X-Provider-Name,request-id,cf-ray
X-Generation-Id: gen-1790352326-DF6TqpPSdIpM5qFJU7Bi
set-cookie: __cf_bm=...; HttpOnly; SameSite=None; Secure; Path=/; Domain=openrouter.ai; Expires=Fri, 25 Sep 2026 16:35:26 GMT
Permissions-Policy: payment=(self ...)
Referrer-Policy: no-referrer, strict-origin-when-cross-origin
X-Content-Type-Options: nosniff
Server: cloudflare
CF-RAY: a40b45375a2be2b6-GIG

282
{"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations","provider_name":"Google AI Studio","is_byok":false,"provider_error_code":"429","limit_source":"upstream_provider_shared_pool","remedy_hint":"Retry shortly, add your own provider key (https://openrouter.ai/settings/integrations), or route to another provider with provider routing: https://openrouter.ai/docs/features/provider-routing"}},"user_id":"user_39KViMt0QrMBr4gKi6otIQroqrN"}
0
```

- No SSE stream opened despite `stream: true`: `Content-Type: application/json`, one chunk.
- **No `X-RateLimit-*`, no `Retry-After`, no `X-Provider-Name`** header, although `X-Provider-Name` is listed in `Access-Control-Expose-Headers`.
- The body carries `metadata.provider_name`, `provider_error_code` (a string), `limit_source` and `remedy_hint`, plus a top-level `user_id` beside `error`.
  The Limits page documents the upstream code as `error.metadata.provider_code` (`captures/free-openrouter-pair/meta/docs-api_reference_limits.md:394`); the wire used `provider_error_code`.
- An `X-Generation-Id` is issued even though no generation happened.

Capture: `captures/openrouter-wire-profile/01-gemma-p1-pi-stream-usage.txt`.

### PROBE K — 2026-09-25 — daily counter around every call

`free_model_daily_requests` from `GET /api/v1/key`, `label` dropped:

| File | Server time | After | `used` / `limit` / `remaining` |
|---|---|---|---|
| `meta/key-0-before-anything.txt` | 16:05:23 | nothing | 0 / 50 / 50 |
| `meta/key-1-after-models-user.txt` | 16:05:25 | `/key` + `/models/user` | 0 / 50 / 50 |
| `meta/key-2-after-completions.txt` | 16:05:37 | + one upstream 429 | 0 / 50 / 50 |
| `meta/key-3-after-generation-lookups.txt` | 16:05:43 | (no lookup had run yet) | 0 / 50 / 50 |
| `meta/key-4-final.txt` | 16:07:03 | + two `/generation` lookups (404) | 0 / 50 / 50 |

The last reading is 97 s after the 429, so a short counter lag does not explain the 0; a lag longer than that is not ruled out.

### PROBE G — 2026-09-25 — generation lookup of the 429 id

`GET /api/v1/generation?id=gen-1790352326-DF6TqpPSdIpM5qFJU7Bi`, twice, 44 s and 65 s after the 429:

```
HTTP/1.1 404 Not Found
{"error":{"message":"Generation gen-1790352326-DF6TqpPSdIpM5qFJU7Bi not found","code":404}}
```

Captures: `meta/generation-01-gemma.txt`, `meta/generation-01-gemma-try2.txt`.
The id in `X-Generation-Id` of a failed request cannot be resolved, so the generation endpoint only helps for completions that ran.
For those, the endpoint documents `provider_name`, `native_finish_reason`, `upstream_id` and `upstream_inference_cost` (`meta/docs-api_api-reference_generations_get-request-_-usage-metadata-for-a-generation.md:162-186`).

### PROBE E — 2026-09-25 — `Accept-Encoding` on a catalogue GET

Unauthenticated `GET /api/v1/models/google/gemma-4-31b-it:free/endpoints`:

- `Accept-Encoding: identity` → no `Content-Encoding`, 1313-byte plain JSON body (`meta/ae-identity.headers.txt`, `meta/ae-identity.body`).
- `Accept-Encoding: gzip, deflate, br` → `Content-Encoding: gzip`, 699-byte gzip body starting `1f 8b` (`meta/ae-offered.headers.txt`, `meta/ae-offered.body`).

On the 429 completion with `identity`, the body was plain (probe 01).
Behaviour on an SSE body is **UNVERIFIED**.

### PROBE U — 2026-09-25 — `/models/user`

`meta/models-user.txt` (extract; the ~750 KB list was not kept): 445 models, **8 `:free` ids**, both probed models among them.
`GET /api/v1/models` listed 18 `:free` ids earlier the same day (`free-openrouter-pair.md` §2).
`nvidia/nemotron-3-super-120b-a12b:free`, the earlier primary pick, is **not** in this account's list; the likeliest cause is the account's free-model training setting (`free-openrouter-pair.md` §1), which is **UNVERIFIED**.
Entries today: gemma `reasoning.default_enabled: false`; qwen `reasoning.default_enabled: true`, `default_effort: "xhigh"`, `supported_efforts: ["xhigh","medium","low"]`; caps 32768 and 235929; `canonical_slug` `google/gemma-4-31b-it-20260402` and `qwen/qwen3.8-27b-20260814`.

## Answers to the ticket's 12 items

Both models share every answer below, except where a column is named.
"Docs" answers are what OpenRouter publishes for all models; none was observed on the wire today.

| # | Item | Answer |
|---|---|---|
| 1 | Pi-shaped stream: frames, SSE comments, `[DONE]`, post-`[DONE]`, headers | **UNVERIFIED** (429 before any stream, probe 01). Docs: `: OPENROUTER PROCESSING` keep-alive comments occur (`free-openrouter-pair/meta/docs-api_reference_streaming.md:219-225`); a usage chunk precedes `[DONE]` (`:294-299`). No `X-RateLimit-*` on the 429; docs say successful responses carry none (`docs-api_reference_limits.md:397`) |
| 2 | Without `stream_options` | **UNVERIFIED**. Docs: `stream_options.include_usage` is "deprecated and ha[s] no effect"; usage is always included (`docs-cookbook_administration_usage-accounting.md:67-69`) |
| 3 | Streamed tool calls, single and parallel | **UNVERIFIED**. Not sent |
| 4 | Non-streaming | **UNVERIFIED**. Not sent |
| 5 | Usage fields; usage frame carries `finish_reason` | **UNVERIFIED**. Docs: `prompt_tokens_details.cached_tokens`, `prompt_tokens_details.cache_write_tokens` (explicit-cache models only), `completion_tokens_details.reasoning_tokens`, `cost`, `cost_details.upstream_inference_cost` (`usage-accounting.md:82-106`); the usage chunk has one choice repeating `finish_reason` and `native_finish_reason` (`streaming.md:294-302`) |
| 6 | Reasoning on the wire | **UNVERIFIED**. Docs: `reasoning` (string) and `reasoning_details` (array); `reasoning_content` is an accepted alias of `reasoning` (`meta/docs-guides_best-practices_reasoning-tokens.md:541-545`); reasoning tokens reported as `completion_tokens_details.reasoning_tokens` (`:104`). qwen reasons at `xhigh` by default, gemma not at all (`meta/models-user.txt`) |
| 7 | `model` echo, `provider` field | **UNVERIFIED**. Docs: `model` is the model "that ends up being used" (`docs-api_reference_overview.md:428`); documented stream chunks carry a `provider` field (`docs-api_reference_errors-and-debugging.md:338`). The 429 body has no `model` field |
| 8 | Error shapes | Upstream-pool 429 (gemma, observed): HTTP 429, `application/json`, no `Retry-After`/`X-RateLimit-*`, body `{"error":{"message":"Provider returned error","code":429,"metadata":{"raw":...,"provider_name":"Google AI Studio","is_byok":false,"provider_error_code":"429","limit_source":"upstream_provider_shared_pool","remedy_hint":...}},"user_id":...}` (probe 01). Unknown model id and `max_tokens` over cap: **UNVERIFIED**, not sent |
| 9 | Accepted at published cap | Published caps: gemma 32768, qwen 235929 (`meta/models-user.txt`). Accepted at cap: **UNVERIFIED**. Docs: with `max_tokens` set, OpenRouter "will only route to providers that support a response of that length" (`docs-guides_routing_provider-selection.md:79`), so over-cap should fail routing on a one-endpoint free model rather than be clamped; not observed |
| 10 | `Accept-Encoding: identity` honoured | **Yes** on a catalogue GET and on the 429 JSON body: `identity` gives plain bytes; offering `gzip, deflate, br` gives `Content-Encoding: gzip` (probe E). SSE body: **UNVERIFIED** |
| 11 | Which provider served; pinning | On an error: `error.metadata.provider_name` in the body; no `X-Provider-Name` header (probe 01). `GET /generation?id=` on the 429's id: 404, so failed requests cannot be traced (probe G). On success: **UNVERIFIED** (docs: generation lookup returns `provider_name`). `provider: {only, allow_fallbacks:false}` accepted: **UNVERIFIED**, not sent |
| 12 | Do `/key`, `/models/user` count | **No.** `used` stayed 0 across three `/key` calls and one `/models/user` call (probe K). Also not counted: one upstream-pool 429 completion and two `/generation` lookups (0 at 97 s after). Whether an OpenRouter-side 400/404 on a `:free` id counts: **UNVERIFIED** |

## Proposed spec 25 profile rows

No row below comes from a successful completion; every cell is either documented (with the source) or UNVERIFIED.
Both models go through the same OpenRouter normalisation layer, so the docs give the same row for both; that sameness is itself unverified.

| Field | `google/gemma-4-31b-it:free` | `qwen/qwen3.8-27b:free` |
|---|---|---|
| `force_include_usage` | false: usage always sent, `include_usage` has no effect (docs, `usage-accounting.md:67-69`) | same |
| `swallow_usage_frame` | false: the usage chunk has a non-empty `choices` (docs, `streaming.md:294`) | same |
| `usage_carries_finish_reason` | true (docs, `streaming.md:294-302`) | same |
| `parse_past_done` | false: usage is sent "just before the `[DONE]`" (docs, `streaming.md:294`); post-`[DONE]` bytes **UNVERIFIED** | same |
| usage field names | `prompt_tokens`, `completion_tokens`, `total_tokens`, `prompt_tokens_details.cached_tokens`, `prompt_tokens_details.cache_write_tokens`, `completion_tokens_details.reasoning_tokens`, `cost`, `cost_details.upstream_inference_cost` (docs) | same |
| `response.model` equality | **UNVERIFIED**. Until captured, accept any of: requested id, id without `:free`, `canonical_slug` (`google/gemma-4-31b-it-20260402`) | same, `canonical_slug` `qwen/qwen3.8-27b-20260814` |
| reasoning field | none expected (reasoning off by default); accept `reasoning`, `reasoning_details`, `reasoning_content` | `reasoning` + `reasoning_details` (docs), accept `reasoning_content` too; on by default at `xhigh` |

## Consequences

1. **The free route's daily counter is not the only limit.**
   Google AI Studio's free pool is shared across all OpenRouter users and rate-limited upstream, independently of the account's 50/day.
   A run can hit 429 with `remaining: 50`.
   The #9 fault list needs `limit_source` as a discriminator: `upstream_provider_shared_pool` is transient (retry later, not a day-abort), while an OpenRouter platform 429 with `X-RateLimit-*` is the daily cap (abort for the day).
2. **An upstream 429 costs nothing on the account counter** (probe K), so a proxy-level retry after a pause is quota-free for the account, though it still loads the shared pool.
3. **A `stream: true` request can get a non-SSE `application/json` error**, as on Zen (`zen-wire-profile.md` consequence 6).
   The parser must record it as `non_2xx` + `upstream_error_payload`, not `stream_truncated`.
4. **Error detection by top-level `error` key matches**; the body also has a top-level `user_id`, which the proxy must not log into shared artefacts unless it accepts the account id in them.
5. **The documented `provider_code` is `provider_error_code` on the wire**; accept both.
6. **Provider attribution cannot rely on a header or on `/generation` for failures.**
   On errors the only source is `error.metadata.provider_name`; for successes, `/generation` or a body `provider` field is documented but unverified.
7. **`Accept-Encoding: identity` must be forced upstream**; OpenRouter compresses (gzip) whenever the client offers it.
8. **Re-run needed.** Items 1-9 and 11 need `capture.sh` re-run at a time the Google AI Studio pool is not saturated.
   23 completions of the ticket budget and all 50 of today's account quota remain.
   If the pool stays saturated, gemma is a poor primary for a run that must finish, and the same question applies to ModelRun's pool for qwen, which was not reached.

## Key self-check

`grep -rc -F "$K" docs/research/captures/openrouter-wire-profile/` over all 44 files: **0 matches in every file** (run 2026-09-25 after the last capture).
The only `Authorization:` occurrences in the directory are the literal header name in `capture.sh` and in an OpenRouter docs page.
