# Zen wire profile of `mimo-v2.5-free` and `hy3-free`

Ticket: YuukiFST/harness-tally#3.
Retrieval date for every claim: **2026-09-25** (server `Date` headers 11:21:19Z to 11:24:20Z).
Question: what does `https://opencode.ai/zen/v1/chat/completions` send back today for `mimo-v2.5-free` and `hy3-free`, and what is each model's output cap?

## Headline

**Neither model can be profiled from outside OpenCode today, and the wire shape the ticket asked for was not captured.**
`mimo-v2.5-free` answers every unauthenticated request with `HTTP 403 FreeTierError: "OpenCode's free tier can only be used from within OpenCode"`.
`hy3-free` is gone: `HTTP 401 ModelError: "Model hy3-free is not supported"`, byte-for-byte the shape the gateway returns for an invented model id, and it is no longer in `/zen/v1/models`, no longer in the Zen docs, and `"status":"deprecated"` on models.dev.
Probing stopped after 5 of the 24 allowed requests, because every further probe on these two ids would have returned the same gate or the same 401 and burned shared quota.
No 429 was received.

Items 1-7 of the ticket and the accepted-at-cap half of item 9 are therefore **UNVERIFIED** for both models.
What was established: the current error shapes (item 8, partly), the published caps (item 9, partly), and `Accept-Encoding` behaviour on the error path (item 10, partly).

## Method

- Client: `curl 8.x` from Git Bash on Windows 10, unauthenticated (no `Authorization` header), default curl `User-Agent`.
- Every live request went through `captures/zen-wire-profile/probe.sh`, which enforces the budget (at most 24), a spacing of at least 45 s (the ticket requires 30 s), and a hard stop on any 429.
  It calls `curl -sS -N --raw -D <headers> -o <body>` and writes headers plus raw body to `captures/zen-wire-profile/<NN>-<model>-<probe>.txt`, with the raw body alone beside it as `.txt.body`.
- Request bodies are pre-generated in `captures/zen-wire-profile/requests/`, one file per model and probe (all 15 were prepared; 4 were sent).
  Shape of the pi-like body (probe p1):

  ```json
  {"model":"mimo-v2.5-free",
   "messages":[{"role":"system","content":"You are a coding agent. Use tools when the user asks you to act on files. Be brief."},
               {"role":"user","content":"Reply with the single word: ok"}],
   "tools":[{"type":"function","function":{"name":"read",...}},{"type":"function","function":{"name":"bash",...}}],
   "max_tokens":512,"stream":true,"stream_options":{"include_usage":true}}
  ```

- Running request count is kept in `captures/zen-wire-profile/requests.log` (one line per live request, local send time).
- Published caps: `https://opencode.ai/docs/zen/` and `https://models.dev/api.json`, fetched with curl at 11:20Z; these are not gateway requests and are not counted.
  Saved as `captures/zen-wire-profile/meta/zen-docs.html` (plus a text rendering `zen-docs.txt`) and `meta/models-dev-opencode-extract.json` (the two relevant entries of key `opencode`; the 4.9 MB full file was not kept).

### Request count

| # | Server time (UTC) | Target | Status |
|---|---|---|---|
| 1 | 11:21:19 | `mimo-v2.5-free`, stream + `include_usage`, `Accept-Encoding: identity` | 403 |
| 2 | 11:22:03 | `hy3-free`, same body | 401 |
| 3 | 11:22:49 | `GET /zen/v1/models` | 200 |
| 4 | 11:23:35 | `hy3-nonexistent-free`, same body | 401 |
| 5 | 11:24:20 | `mimo-v2.5-free`, non-streaming, `Accept-Encoding: gzip, deflate, br` | 403 |

**Total: 5 of 24. No 429.**

## Probes

### PROBE 01 — 2026-09-25 — `mimo-v2.5-free`, pi-shaped stream

Request: `requests/mimo-v2.5-free-p1-stream-usage.json` (system + user + 2 tools, `stream: true`, `stream_options.include_usage: true`, `max_tokens: 512`), header `Accept-Encoding: identity`.
Status: **403**, time to first byte 0.79 s.
Verbatim response:

```
HTTP/1.1 403 Forbidden
Date: Fri, 25 Sep 2026 11:21:19 GMT
Content-Type: application/json
Content-Length: 151
Connection: keep-alive
Cf-Placement: remote-ORD
Server: cloudflare
CF-RAY: a409a5059c6e5c71-MIA

{"type":"error","error":{"type":"FreeTierError","message":"Error from provider (Console): OpenCode's free tier can only be used from within OpenCode"}}
```

No SSE stream was opened: `Content-Type` is `application/json`, not `text/event-stream`, despite `stream: true`.
No rate-limit headers, no `Retry-After`.
Capture: `captures/zen-wire-profile/01-mimo-v2.5-free-p1-stream-usage.txt`.

### PROBE 02 — 2026-09-25 — `hy3-free`, pi-shaped stream

Request: `requests/hy3-free-p1-stream-usage.json`, identical to probe 01 except `model`, `Accept-Encoding: identity`.
Status: **401**, time to first byte 0.71 s.
Verbatim response:

```
HTTP/1.1 401 Unauthorized
Date: Fri, 25 Sep 2026 11:22:03 GMT
Content-Type: text/plain;charset=UTF-8
Content-Length: 90
Connection: keep-alive
Cf-Placement: remote-ORD
Server: cloudflare
CF-RAY: a409a61d39c05838-MIA

{"type":"error","error":{"type":"ModelError","message":"Model hy3-free is not supported"}}
```

The body is JSON but the `Content-Type` is `text/plain;charset=UTF-8`.
Capture: `captures/zen-wire-profile/02-hy3-free-p1-stream-usage.txt`.

### PROBE 03 — 2026-09-25 — `GET /zen/v1/models`

Request: `GET https://opencode.ai/zen/v1/models`, no body.
Status: **200**, `Content-Type: application/json`, `Content-Length: 6807`, 81 model ids.
Free-looking ids listed: `big-pickle`, `jev-1.13-free`, `deepseek-v4-flash-free`, `muse-spark-1.3-contributor-free`, `muse-spark-1.2-contributor-free`, `mimo-v2.6-flash-free`, `space-bunny-free`, `mimo-v2.5-free`, `ling-3.0-flash-fin-free`, `nemotron-3-ultra-free`, `nemotron-3.5-lightning-free`.
**`hy3-free` is absent; no id contains `hy`.**
`mimo-v2.5-free` is listed.
Capture: `captures/zen-wire-profile/03-gateway-models-list.txt`.

### PROBE 04 — 2026-09-25 — invented model id

Request: `requests/unknown-model.json`, the probe-01 body with `model: "hy3-nonexistent-free"`, `Accept-Encoding: identity`.
Status: **401**.
Verbatim response:

```
HTTP/1.1 401 Unauthorized
Date: Fri, 25 Sep 2026 11:23:35 GMT
Content-Type: text/plain;charset=UTF-8
Content-Length: 102
Connection: keep-alive
Cf-Placement: remote-ORD
Server: cloudflare
CF-RAY: a409a857b907a54f-MIA

{"type":"error","error":{"type":"ModelError","message":"Model hy3-nonexistent-free is not supported"}}
```

Same status, headers and body shape as probe 02: the gateway treats `hy3-free` exactly as an id that never existed.
Capture: `captures/zen-wire-profile/04-unknown-model-p8-unknown-model.txt`.

### PROBE 05 — 2026-09-25 — `mimo-v2.5-free`, non-streaming, compression offered

Request: `requests/mimo-v2.5-free-p5-nonstream.json` (probe-01 body with `stream: false` and no `stream_options`), header `Accept-Encoding: gzip, deflate, br`.
Status: **403**.
Verbatim headers:

```
HTTP/1.1 403 Forbidden
Date: Fri, 25 Sep 2026 11:24:20 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
Cf-Placement: remote-ORD
Content-Encoding: br
Server: cloudflare
CF-RAY: a409a9735b3a9fe7-MIA
```

The body arrived brotli-compressed in one 0x71-byte chunk; decoded with Node `zlib.brotliDecompressSync` it is byte-identical in content to probe 01:

```
{"type":"error","error":{"type":"FreeTierError","message":"Error from provider (Console): OpenCode's free tier can only be used from within OpenCode"}}
```

So the gate is not specific to streaming, and Cloudflare compresses with `br` whenever the client offers it.
Capture: `captures/zen-wire-profile/05-mimo-v2.5-free-p5-nonstream.txt` (raw), decoded body in `05-mimo-v2.5-free-p5-nonstream.decoded.txt`.

### PROBE M1 — 2026-09-25 — published caps (not a gateway request)

`https://opencode.ai/docs/zen/`, HTTP 200 at 11:20:10Z:

- The endpoint table lists `mimo-v2.5-free` on `/zen/v1/chat/completions` (`meta/zen-docs.txt:172`) and describes it as "available on OpenCode for a limited time" (`meta/zen-docs.txt:292`).
- **The page publishes no output cap and no context limit for any model**: no occurrence of "max output", "output limit" or `max_tokens` in the HTML.
- **`hy3-free` is not mentioned anywhere on the page** (0 matches for `hy3`, `hunyuan`, `tencent`), neither in the model table nor in the deprecated-models table (`meta/zen-docs.txt:310-329`).
- The page contains no statement that the free tier is restricted to the OpenCode client; the restriction is known only from the 403 body.

`https://models.dev/api.json`, key `opencode`, HTTP 200 at 11:20:08Z (`meta/models-dev-opencode-extract.json`):

| id | `limit.context` | `limit.input` | `limit.output` | `status` | `reasoning` | `interleaved.field` |
|---|---|---|---|---|---|---|
| `mimo-v2.5-free` | 200000 | absent | **32000** | `deprecated` | true | `reasoning_content` |
| `hy3-free` | 190000 | 192000 | **64000** | `deprecated` | true | `reasoning_content` |

Both models now carry `"status":"deprecated"`; #34 recorded that status only for `deepseek-v4-flash-free` and `laguna-s-2.1-free`.

## Per-model answers to the ticket's 10 items

| # | Item | `mimo-v2.5-free` | `hy3-free` |
|---|---|---|---|
| 1 | Pi-shaped stream, frames, SSE comments, `[DONE]`, post-`[DONE]`, headers | **UNVERIFIED.** 403 `FreeTierError` before any stream; `Content-Type: application/json`, no SSE (probe 01) | **UNVERIFIED.** 401 `ModelError`, model not served (probe 02) |
| 2 | Same without `stream_options` | **UNVERIFIED.** Not sent; probe 05 shows the gate is independent of body shape | **UNVERIFIED.** Model not served |
| 3 | Streamed tool calls, single and parallel | **UNVERIFIED.** Gate | **UNVERIFIED.** Model not served |
| 4 | Non-streaming response | **UNVERIFIED.** 403 (probe 05) | **UNVERIFIED.** Model not served |
| 5 | Usage fields, usage frame carries `finish_reason` | **UNVERIFIED** today. Last seen 2026-08-07 (harness-bench research 11 §5.2, §5.4) and 2026-09 (#34) | **UNVERIFIED.** No hy3 usage object was ever captured verbatim; #34 reported `reasoning_tokens: 12` in prose only |
| 6 | Reasoning field names in deltas | **UNVERIFIED** today. models.dev declares `interleaved.field: reasoning_content`; research 11 §5.5 saw `reasoning` + `reasoning_details[]` on 2026-08-07 | **UNVERIFIED.** models.dev declares `reasoning_content` |
| 7 | `model` echo on every frame | **UNVERIFIED.** Error bodies carry no `model` field | **UNVERIFIED** |
| 8 | Error shapes | Gate: HTTP 403, `application/json`, `{"type":"error","error":{"type":"FreeTierError","message":"Error from provider (Console): OpenCode's free tier can only be used from within OpenCode"}}`. `max_tokens` overflow: **UNVERIFIED** (not sent; would have met the gate first, but that ordering is itself not tested) | Unknown/withdrawn model: HTTP 401, `text/plain;charset=UTF-8`, `{"type":"error","error":{"type":"ModelError","message":"Model hy3-free is not supported"}}`, identical to an invented id (probe 04). Overflow: not applicable |
| 9 | Output cap | Published: **32000** (models.dev `limit.output`); Zen docs publish none. Accepted at cap: **UNVERIFIED** (gate). Upstream's own words: **UNVERIFIED** | Published: **64000** (models.dev); Zen docs do not list the model. Accepted at cap: not applicable, model not served |
| 10 | `Accept-Encoding: identity` honoured | On the error path, yes: `identity` gives `Content-Length`, no `Content-Encoding` (probe 01); `gzip, deflate, br` gives `Content-Encoding: br` + chunked (probe 05). On an SSE stream: **UNVERIFIED** | Error path with `identity`: plain, `Content-Length` (probe 02). Offering compression: not tested |

Headers common to every gateway response today: `Server: cloudflare`, `CF-RAY: <16 hex>-MIA`, `Cf-Placement: remote-ORD`, `Connection: keep-alive`.
No response carried any rate-limit header.

## Proposed profile rows (spec 25 §2 format)

No row below is derived from today's wire, because no completion was obtained.

| Profile | Models | `force_include_usage` | `swallow_usage_frame` | `parse_past_done` | `usage_carries_finish_reason` |
|---|---|---|---|---|---|
| `zen-openrouter` | `mimo-v2.5-free` | false (last verified 2026-09, #34) | false (last verified 2026-09, #34) | true (last verified 2026-09, #34) | true (last verified 2026-08-07, research 11 §5.4) |
| — | `hy3-free` | **no row**: model not served on 2026-09-25 (probes 02-04) | | | |

Field names for `zen-openrouter`, all last verified before today and **UNVERIFIED on 2026-09-25**:
cached tokens `prompt_tokens_details.cached_tokens`; cache-write tokens `prompt_tokens_details.cache_write_tokens`; reasoning tokens `completion_tokens_details.reasoning_tokens` (always 0 on mimo per #34); reasoning deltas `reasoning` and `reasoning_details[]` per research 11, while models.dev now declares `reasoning_content`, so all three names must stay accepted per spec 25 §5.1.
Error body today: `{"type":"error","error":{"type":<string>,"message":<string>}}` on 401 and 403.

The `mimo-v2.5-free` row is only usable if the proxy's upstream traffic passes the free-tier gate, which curl did not.

## Consequences for the proxy

1. **The free tier refuses non-OpenCode clients (403 `FreeTierError`).**
   Spec 25 assumes any arm can reach Zen's free models through the proxy; today a request that does not look like OpenCode is refused before the model is reached.
   Which request attribute the gate keys on (`User-Agent`, an OpenCode-specific header, or something else) is **UNVERIFIED**: I did not send requests impersonating the OpenCode client, because that would be circumventing an access control and needs an explicit decision by the project owner, including a reading of Zen's terms.
   Until that is decided, the Pi arm in #1 cannot run on `mimo-v2.5-free`, and the OpenCode arm is the only one that might pass.
2. **`hy3-free` is withdrawn, so the robustness tier chosen in harness-bench #35 is dead**, the second tier lost in two months after `deepseek-v4-flash-free`.
   This needs a new tier decision in harness-bench before tally #8 can write a second row.
3. **The start-up canary (spec 25 §9) cannot be issued by the runner as its own client.**
   If the canary does not carry the same client identity as the harness, it will get 403 even when the arm works, and it will pass for a client the gateway would refuse.
   The canary has to be sent with the arm's own headers, or through the arm.
4. **Error detection by `error` key (spec 25 §6 `upstream_error_payload`) matches today's shape.**
   Today's 401 and 403 bodies are `{"type":"error","error":{...}}`, with a top-level `error` key.
   Tally #9 quotes #34 as finding bodies shaped `{"type":"...Error","message":...}` without an `error` key; that flat shape did not appear today.
   Detection should accept both, keyed on `error` or on a top-level `type` ending in `Error`.
5. **The 401 body is JSON served as `text/plain;charset=UTF-8`.**
   A proxy that only parses bodies whose `Content-Type` is JSON will miss this error payload; parse by content, not by header.
6. **A `stream: true` request can get a non-SSE `application/json` error response.**
   The stream parser must handle a response with no `data:` lines and record it as `non_2xx` plus `upstream_error_payload`, not as `stream_truncated`.
7. **`Accept-Encoding: identity` (spec 25 §8.3) is honoured, and it is needed.**
   Offering `gzip, deflate, br` produced `Content-Encoding: br` on the error path; forwarding the client's own `Accept-Encoding` upstream would hand the parser brotli bytes.
   Behaviour on an SSE body is UNVERIFIED.
8. **Two new fault causes need names in the #9 list:** 403 `FreeTierError` (client refused by the free-tier gate) and 401 `ModelError` for a model that was served before (tier withdrawn).
   Both are configuration-level failures that will repeat on every request, so they should abort the run like a canary mismatch rather than let a run accumulate discarded requests.
9. **The `max_tokens` contract (#10) has no verified upstream cap.**
   The only published figures are models.dev's `limit.output` (32000 mimo, 64000 hy3), the Zen docs publish none, and whether the gateway accepts `max_tokens` at the published cap was not testable.
10. **models.dev marks both tiers `deprecated`**, and #34 already showed it lists dead ids; it is also now behind in the other direction, because it still lists `hy3-free` while the gateway and docs have dropped it.
    Liveness must come from the gateway (probe 03 style), as harness-bench #35 already requires.

## Not done, and why

- Items 1-7 and the capped/overflow `max_tokens` probes: every request to these two ids returns the gate or the 401 before reaching a model, so further probes would spend shared quota to re-record the same error.
  The 19 unspent requests remain available for a re-run once the gate question is decided.
- Probing other free ids (for example `mimo-v2.6-flash-free`) was out of this ticket's scope and was not done.
