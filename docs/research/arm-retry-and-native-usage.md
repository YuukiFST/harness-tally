# Retry behaviour and native usage reporting of pi 0.80.10 and opencode 1.17.9

Date: 2026-09-25.
Ticket: YuukiFST/harness-tally#5 (part of #1).
Feeds: #15 (aggregation and cross-check), #23 (calibration), harness-bench spec 25 §7, §12, §13.1 and §13.4.

## Summary

pi makes at most 4 attempts per turn (1 plus 3 retries), with 2 s, 4 s and 8 s backoff: 14 s of backoff in total.
This was measured on six failure types, and every run still exited 0 after pi gave up.
opencode has **no attempt cap**.
It retries with 2 s × 2^(n-1) backoff until the run is killed.
That backoff is capped at 30 s only when the error carries no HTTP response headers, and it is uncapped otherwise.
For opencode, no retry window can "equal the harness's own retry ceiling", because opencode has no ceiling.
Both arms recompute the total instead of passing the upstream `total_tokens` through.
They also disagree on whether `output` includes reasoning tokens.
pi drops a usage frame that arrives after `[DONE]`, and opencode counts it.

## Method

Two sources, for every claim.

1. **Package source at the pinned versions.**
   pi: `C:/hbarms/node_modules/@earendil-works/pi-coding-agent` 0.80.10, with its bundled `@earendil-works/pi-ai`, `pi-agent-core` and `openai` 6.26.0 under `.../pi-coding-agent/node_modules/`.
   opencode: `C:/hbarms/node_modules/opencode-ai/bin/opencode.exe` 1.17.9 (`opencode --version` prints `1.17.9`).
   This is a Bun single-file executable, so its JavaScript is embedded and minified.
   Claims about opencode cite the **byte offset** of the compiled code in `opencode.exe`.
   They also cite the matching readable TypeScript at the release tag `v1.17.9` = commit `5c23e88419c4743b9be42cea132f2fb1e6cb63ff` of `anomalyco/opencode` (paths under `packages/opencode/src/`).
   Each upstream function cited was matched against the embedded code by its constants and string literals.
2. **Replay against a scripted local mock.**
   `captures/arm-retry-and-native-usage/mock_upstream.py` is an OpenAI-compatible server on 127.0.0.1 (ports 11501-11540) that serves one scripted scenario per process.
   It logs every request with arrival time, completion time, a `messages_hash` and whether the request carried tools.
   `run_matrix.py` launches each arm with the harness-bench layer1 `isolated` recipe (`layer1/src/hb_layer1/arms.py` @ 9c0fe11).
   That recipe gives each run a fresh `HOME`, `USERPROFILE`, XDG dirs and TEMP under `C:/tmp/hbt5/runs/<arm>-<scenario>/`, which is outside any git repository.
   pi also gets a fresh `PI_CODING_AGENT_DIR` with `models.json` and `PI_OFFLINE=1`.
   opencode gets `OPENCODE_CONFIG_CONTENT`, `--pure`, `--dangerously-skip-permissions`, `OPENCODE_DISABLE_MODELS_FETCH=1` and `OPENCODE_DISABLE_AUTOUPDATE=1`, so there is no network beyond loopback.
   The prompt is `Reply with the single word done.`
   pi runs are cut off at 90 s and opencode runs at 150 s.
   `summarize.py` reduces each capture to `summary.json`.
   Attempts and gaps come from the mock log only.
   A gap is the arrival of the next request minus the end of the previous response.

Scenarios.
Each failure scenario is applied to **every** request that carries tools, so the harness's full retry budget is used up.
A request without tools (opencode's title call) always gets a normal reply with its own usage, `50/2`.
That lets the title call be told apart in native totals.

| Scenario | Upstream behaviour |
|---|---|
| `ok` | normal stream; usage `prompt 137, completion 11, total 999, cached_tokens 20, cache_write_tokens 7, reasoning_tokens 3` (total deliberately wrong) |
| `no_finish` | content and usage frames, `[DONE]`, never a `finish_reason` |
| `no_usage` | content, `finish_reason: stop`, `[DONE]`, no usage frame |
| `usage_after_done` | content, `finish_reason`, `[DONE]`, then the usage frame |
| `r429` | HTTP 429, headers only `content-type` and `content-length`, body `{"type":"FreeUsageLimitError","message":"Rate limit exceeded. Please try again later."}` |
| `r429_wrapped` | control: the same body nested under an `error` key |
| `r500` | HTTP 500, body `{"error":{"type":"server_error","message":"Internal Server Error"}}` |
| `err200_json` | HTTP 200 `application/json` carrying the #31 `ResourceExhausted 32/32` error body verbatim (`harness-bench docs/research/11-second-free-model.md:577`) |
| `err200_sse` | HTTP 200 `text/event-stream` whose first frame is that same error object |
| `disconnect` | one content frame, then the socket is reset mid-chunked-body (SO_LINGER 0, no terminating chunk) |

The skipped `opencode-ai` postinstall does not affect this survey.
`cmp` shows `opencode-ai/bin/opencode.exe` to be byte-identical to `opencode-windows-x64/bin/opencode.exe`.
From the part of `C:/hbarms/node_modules/opencode-ai/postinstall.mjs` that was read (lines 1-80), the script picks and places the platform binary.
The rest of that script was not read.

Regenerate every capture with the commands below.
Run them from `docs/research/captures/arm-retry-and-native-usage/`, and allow about 25 min for the opencode run.

```
python run_matrix.py pi 11501 C:/tmp/hbt5/runs
python run_matrix.py opencode 11521 C:/tmp/hbt5/runs
python summarize.py
```

## pi 0.80.10

### Retry policy

Only one retry layer is active.
The OpenAI SDK's own retry is off: `maxRetries: options?.maxRetries ?? 0` (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js:133`).
The session passes `retry.provider.maxRetries`, which is unset by default (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/dist/core/sdk.js:186`, `.../dist/core/settings-manager.js:571-576`).
Every attempt was sent with `X-Stainless-Retry-Count: 0`.

The active layer is `AgentSession` auto-retry.
It is on by default (`.../pi-coding-agent/dist/core/settings-manager.js:542-543`), with `maxRetries ?? 3` and `baseDelayMs ?? 2000` (`.../settings-manager.js:553-558`).
The delay is `baseDelayMs * 2 ** (attempt - 1)` (`.../pi-coding-agent/dist/core/agent-session.js:2100`), with no jitter and no Retry-After handling.
It stops once `_retryAttempt > maxRetries` (`.../agent-session.js:2094-2098`).

Whether a failure is retried depends on the **text** of the error message, not on its status code.
A message is retried when it matches `RETRYABLE_PROVIDER_ERROR_PATTERN` and does not match `NON_RETRYABLE_PROVIDER_LIMIT_ERROR_PATTERN` (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/utils/retry.js:4-19`, `:20-72`, `:82-89`).
Context overflow is excluded first and handled by compaction instead (`.../agent-session.js:2079-2083`).
The missing-`finish_reason` failure is thrown as `Stream ended without finish_reason` (`.../pi-ai/dist/api/openai-completions.js:375-377`).
That message matches the retryable pattern `ended without` (`.../pi-ai/dist/utils/retry.js:59`).

| Failure | Retried | Attempts | Gaps measured (ms) | First to last arrival (ms) | Error text pi reports | Exit |
|---|---|---|---|---|---|---|
| missing `finish_reason` | yes | 4 | 2072, 4048, 8040 | 14163 | `Stream ended without finish_reason` | 0 |
| 429 `FreeUsageLimitError`, top-level body | **yes** | 4 | 2034, 4048, 8082 | 14164 | `429 status code (no body)` | 0 |
| 429 `FreeUsageLimitError` under `error` (control) | no | 1 | none | 0 | `429: {"type":"FreeUsageLimitError",...}` | 0 |
| 500 | yes | 4 | 2041, 4026, 8037 | 14104 | `500: {"type":"server_error","message":"Internal Server Error"}` | 0 |
| 200 with JSON error body | yes | 4 | 2046, 4046, 8029 | 14122 | `Stream ended without finish_reason` | 0 |
| 200 with SSE error frame | yes | 4 | 2064, 4067, 8030 | 14162 | `Error from provider (Console): ... ResourceExhausted ... (32/32)` | 0 |
| mid-stream disconnect | yes | 4 | 2062, 4122, 8046 | 14231 | `terminated` | 0 |

Captures: `captures/arm-retry-and-native-usage/pi-<scenario>/{mock.jsonl,stdout.jsonl,summary.json}`.
All four attempts in each retried run carried the same `messages_hash`.
The JSON stream shows the retries explicitly.
It emits one `agent_end` per attempt, with `willRetry: true, true, true, false`, then `auto_retry_start {attempt 1..3, maxAttempts 3, delayMs 2000/4000/8000}` and finally `auto_retry_end {success: false, attempt: 3}`.

The `FreeUsageLimitError` guard does not fire on the body shape given in this ticket.
The OpenAI SDK builds the error message only from the parsed body's `error` key (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/node_modules/openai/core/error.js:21-37`, `.../openai/client.js:355-365`).
The error-body normaliser has the same limitation, because it reads `error.error` (`.../pi-ai/dist/utils/error-body.js:63-67`).
A top-level `{"type":"FreeUsageLimitError",...}` therefore surfaces as `429 status code (no body)`.
That text matches `429`, so pi spends all 4 attempts on a free-tier cap.
The same body nested under `error` produced a message that contains `FreeUsageLimitError`, and pi stopped after 1 attempt.
UNVERIFIED: the exact byte shape of a real Zen 429.
This survey used the shape given in the ticket.

In `--mode json` pi exits 0 even after it gives up.
It sets exit code 1 only in `text` mode (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/dist/modes/print-mode.js:100-107`).

Configurability: `retry.enabled`, `retry.maxRetries` and `retry.baseDelayMs` in pi's settings.
In the isolated profile no settings file exists, so the defaults above apply.

### Native usage

Per request, pi emits `message_end.message.usage` for each assistant message, and that includes failed attempts.
The mapping is `parseChunkUsage` (`.../pi-ai/dist/api/openai-completions.js:950-976`).
The table below shows it verified against the `ok` scenario (`pi-ok/stdout.jsonl`).

| pi field | Source | Mock `ok` value | Equivalent in OpenAI usage terms |
|---|---|---|---|
| `input` | `max(0, prompt_tokens - cached_tokens - cache_write_tokens)` | 110 | `prompt_tokens - cached - cache_write` |
| `cacheRead` | `prompt_tokens_details.cached_tokens` (or `prompt_cache_hit_tokens`) | 20 | `cached_tokens` |
| `cacheWrite` | `prompt_tokens_details.cache_write_tokens` | 7 | `cache_write_tokens` |
| `output` | `completion_tokens` (**includes** reasoning) | 11 | `completion_tokens` |
| `reasoning` | `completion_tokens_details.reasoning_tokens` | 3 | `reasoning_tokens` (a subset of `output`) |
| `totalTokens` | recomputed as `input + output + cacheRead + cacheWrite` | 148 (upstream said 999) | `prompt_tokens + completion_tokens` |

To reconstruct the proxy's figures: `prompt_tokens = input + cacheRead + cacheWrite` and `completion_tokens = output`.
Neither arm uses upstream `total_tokens`.
Chunk usage is read from `chunk.usage`, or from `choices[0].usage` as a fallback (`.../openai-completions.js:260-270`).

Summing the native total needs care when retries happen.
Every failed attempt emits its own assistant `message_end`.
In `no_finish`, all 4 carry the full usage (`input 110, output 11`), so the `message_end` sum is 4 × 148.
The failed message is then removed from agent state before the retry (`.../agent-session.js:2108-2112`).
The **final** `agent_end.messages` therefore holds only the last attempt (`pi-no_finish/summary.json`: `final_agent_end_assistant_usage` has one entry).
Doc 10's suggestion to "sum from the final `agent_end` alone" (`harness-bench docs/research/10-pi-measurement-surface.md:352`) undercounts any run that retried.
The sum over assistant `message_end` events is the one that matches the proxy request by request.

### Excluded calls

Checked against doc 10 §8 (`harness-bench docs/research/10-pi-measurement-surface.md:579-607`); the call sites are still present in 0.80.10.

- **Context compaction summary**: `completeSimple` at `C:/hbarms/node_modules/@earendil-works/pi-coding-agent/dist/core/compaction/compaction.js:412`, reached through `completeSummarization` (`:410-416`).
  It is a separate completion outside the agent loop, so it produces no `message_end`.
- **Split-turn prefix summary**: a second call in the same compaction (doc 10 §8 b).
- **Branch summarisation**: `.../dist/core/compaction/branch-summarization.js:226`.
  It is not reachable from `pi --mode json "prompt"` (doc 10 §8 c).
- pi has no title or classifier call (doc 10 §8).
- `getSessionStats()` sums only assistant `message` entries (`.../agent-session.js:2471-2494`), so compaction is also missing from the persisted totals.

Summarisation calls go through the session stream function without `maxRetries`, and `compaction.js` contains no retry, so they are made once.
UNVERIFIED by replay: none of these runs grew large enough to compact.

### Missing or late usage

| Scenario | Native `usage` | `stopReason` | Retry | Exit |
|---|---|---|---|---|
| `no_usage` | `input 0, output 0, cacheRead 0, cacheWrite 0, totalTokens 0`, no `reasoning` key | `stop` | no | 0 |
| `usage_after_done` | all zeros, as above | `stop` | no | 0 |

The late frame is dropped by the OpenAI SDK.
After it sees `[DONE]` it sets `done = true` and `continue`s past every later SSE message (`C:/hbarms/node_modules/@earendil-works/pi-coding-agent/node_modules/openai/core/streaming.js:33-37`).
This matches harness-bench spec 25 §6.2.
A native zero next to a non-zero proxy count is the only symptom.

## opencode 1.17.9

### Retry policy

Two retry layers exist, and they cover different calls.

1. **Main agent loop and compaction.**
   The AI SDK retry is disabled with `maxRetries: input.retries ?? 0` (`session/llm.ts:323`; `opencode.exe` byte 100572024).
   The retry is instead done by `Effect.retry(SessionRetry.policy(...))` around the whole processor stream (`session/processor.ts:994-1024`; byte 100597714).
   The policy stops only when `retryable()` returns `undefined` (`session/retry.ts:176-199`), and **it counts no attempts at all**.
   The delay is set in `session/retry.ts:26-66` (byte 100577293).
   Without Retry-After it is `2000 * 2^(attempt-1)`.
   That delay is capped at 30 000 ms only when the error has **no** `responseHeaders` (`:65`).
   When headers are present it is capped only at 2 147 483 647 ms (`:29`, `:61`).
   `retry-after-ms` and `retry-after` (in seconds or as an HTTP date) override the delay (`:39-59`).
2. **Title generation.**
   This call uses the AI SDK's own retry, `retries: 2` (`session/prompt.ts:218`; byte 100624430).
   The embedded AI SDK default schedule is `initialDelayInMs = 2000` and `backoffFactor = 2`, and it honours Retry-After below 60 s (byte 103110434).
   That allows up to 3 title requests.
   A failed title is swallowed (`session/prompt.ts:1187-1191`, `Effect.ignore`).
   UNVERIFIED by replay: the mock always answered the title call successfully.

Which failures are retried (`session/retry.ts:68-152`).
An `APIError` is retried if `isRetryable` is set or its status is 5xx.
The embedded AI SDK `APICallError` sets `isRetryable` for 408, 409, 429 and 5xx (byte 99425321).
Connection resets and stream errors become `APIError { isRetryable: true }` (`session/message-v2.ts:634-685`).
`FreeUsageLimitError` in the body is **retried**, not stopped: `retryable()` returns an upsell message (`session/retry.ts:76-88`; byte 100578160), and a returned value means "retry".
Other errors are retried only when their text matches rate-limit wording or JSON codes (`:125-151`).

| Failure | Retried | Requests before kill at 150 s | Gaps measured (ms) | First to last (ms) | Native output | Exit |
|---|---|---|---|---|---|---|
| missing `finish_reason` | no | 1 | none | 0 | `step_finish` with `reason: "unknown"` and full tokens (148) | 0 |
| 429 `FreeUsageLimitError`, top-level body | **yes, unbounded** | 7 | 2264, 4097, 8034, 16100, 32114, 64162 | 126772 | nothing on stdout | killed |
| 429 `FreeUsageLimitError` under `error` | **yes, unbounded** | 7 | 2783, 4190, 8086, 16045, 32065, 64062 | 127233 | nothing on stdout | killed |
| 500 | **yes, unbounded** | 7 | 2386, 4042, 8050, 16111, 32019, 64029 | 126639 | nothing on stdout | killed |
| 200 with JSON error body | no | 1 | none | 0 | a `step_finish` with `reason: "unknown"` and all-zero tokens; no `error` event | 0 |
| 200 with SSE error frame | no | 1 | none | 0 | `error` event `UnknownError` carrying the ResourceExhausted text | 1 |
| mid-stream disconnect | **yes, unbounded** | 8 | 2032, 4099, 8333, 16133, 30073, 30052, 30070 | 120797 | only `step_start` | killed |

Captures: `captures/arm-retry-and-native-usage/opencode-<scenario>/`.
The gaps show the header rule at work.
The 429 and 500 failures carry response headers, so their delays keep doubling past 30 s.
The disconnect failure has no response, so it levels off at 30 s.
All retried requests carried the same `messages_hash`.
`opencode run --format json` prints nothing while it retries.
`run.ts` emits only `step_start`, `text`, `reasoning`, `tool_use`, `step_finish` and `error`, and it ignores `session.status` of type `retry` (`cli/cmd/run.ts:650-727`).
Under a persistent 429, 5xx or disconnect, the process never exits by itself.

The 200-with-JSON-body case is silent: no retry, no error, exit 0, and one step with zero tokens.
The proxy's `upstream_error_payload` flag is the only signal for it.

### Native usage

Per request, opencode emits `step_finish.part.tokens` on stdout.
It is produced by `Session.getUsage` (`session/session.ts:384-431`; byte 103060859) from the AI SDK usage.
That usage is adapted in `session/llm/ai-sdk.ts:44-63` (byte 100446141), and the `step_finish` itself is emitted by `run.ts:679-681` (byte 99885737).
The table below shows it verified against the `ok` scenario (`opencode-ok/stdout.jsonl`).

| opencode field | Source | Mock `ok` value | Equivalent in OpenAI usage terms |
|---|---|---|---|
| `tokens.input` | `inputTokens - cacheRead - cacheWrite` | 117 | `prompt_tokens - cached_tokens` (see `cache.write`) |
| `tokens.cache.read` | `prompt_tokens_details.cached_tokens` | 20 | `cached_tokens` |
| `tokens.cache.write` | `inputTokenDetails.cacheWriteTokens` or provider metadata | 0 | not mapped from `cache_write_tokens` on `@ai-sdk/openai-compatible`; those 7 tokens stay inside `input` |
| `tokens.output` | `outputTokens - reasoningTokens` (**excludes** reasoning) | 8 | `completion_tokens - reasoning_tokens` |
| `tokens.reasoning` | `completion_tokens_details.reasoning_tokens` | 3 | `reasoning_tokens` |
| `tokens.total` | AI SDK `totalTokens` | 148 (upstream said 999) | `prompt_tokens + completion_tokens`; omitted when there is no usage |
| `cost` | configured model price | 0 | none |

To reconstruct the proxy's figures on this provider: `prompt_tokens = input + cache.read + cache.write` and `completion_tokens = output + reasoning`.
The two arms differ on `output`.
pi's `output` equals `completion_tokens`.
opencode's `output` is `completion_tokens` minus reasoning.
UNVERIFIED: which of the several embedded copies of the openai-compatible usage converter is the one used.
The mapping above is taken from the observed output, not from a single cited function.

### Excluded calls

- **Title generation**: 1 request, or up to 3 with the AI SDK retry.
  It goes through `llm.stream` straight to text (`session/prompt.ts:177-237`; byte 100624472), bypasses the processor and produces no `step_finish`.
  Verified: every opencode capture has one `aux` request answered with `50/2` tokens, and none of them shows up in stdout.
  It is suppressed when `opencode run --title <t>` is given, because the session is then created with a non-default title (`cli/cmd/run.ts:385-388`, `:453-455`; `session/prompt.ts:183`).
- **Subagent (task tool) sessions**: child sessions have a different `sessionID`, and `run.ts` drops their parts (`cli/cmd/run.ts:652`).
  Their steps are real upstream requests that never reach stdout.
  UNVERIFIED by replay, because the scripted prompt never used the task tool.
- **Retried attempts**: failed attempts emit nothing, as verified in `r429`, `r500` and `disconnect`.
  After a retry that succeeds, only the successful attempt emits `step_finish`.
  That second sentence is from source only: the replays used persistent failures, and a retry followed by a success was not replayed.
- **Compaction is included, not excluded.**
  It runs through the same processor with `tools: {}` (`session/compaction.ts:378-419`), and `step-finish` parts are written whatever the `summary` flag says (`session/processor.ts:719-729`).
  Its tokens therefore appear on stdout.
  UNVERIFIED by replay.
- `SessionSummary.summarize` makes no LLM call; `session/summary.ts` imports no LLM module.

### Missing or late usage

| Scenario | Native `tokens` | `reason` | Retry | Exit |
|---|---|---|---|---|
| `no_usage` | `input 0, output 0, reasoning 0, cache 0/0`; the **`total` key is absent** | `stop` | no | 0 |
| `usage_after_done` | **counted normally**: `total 148, input 117, output 8, reasoning 3, cache.read 20` | `stop` | no | 0 |

The late frame is counted because the embedded SSE parser drops only the literal `[DONE]` event and keeps parsing what follows.
Every embedded copy has the same line: `if(data==="[DONE]")return;` (for example byte 115513170).
This is the opposite of pi.
For opencode, the native-versus-proxy cross-check **cannot** detect `usage_after_done`, and the proxy's own fault flag is the only detector.

## Consequences for the proxy

### Retry-detection window (spec 25 §7, §13.1)

- **pi**: ceiling of 4 attempts; backoff 2000, 4000 and 8000 ms, 14 000 ms in total.
  Measured from the first to the last arrival: 14 104 to 14 231 ms across six fault types.
  The largest gap between consecutive attempts was 8 000 ms plus at most 122 ms.
  An anchor-free window must cover 14 s plus the duration of three failed attempts.
  A gap-based window, measured from the previous identical request's last byte, needs 8 s plus a margin.
  Record `retry.maxRetries=3` and `retry.baseDelayMs=2000` in the run manifest, since a settings file can change them.
- **opencode**: **no ceiling**.
  Attempts are unbounded.
  Gaps go 2, 4, 8, 16, 32, 64 s and keep growing when the failure carries HTTP headers.
  They are capped at 30 s only for header-less failures such as a disconnect, and Retry-After can stretch any single gap to 2^31 ms.
  A time window cannot equal this ceiling.
  The run's wall-clock timeout is the only thing that ends such a run, because the process never exits and prints nothing while it retries.
- **The window mostly affects bookkeeping, not correctness.**
  In all 10 retried runs (6 pi, 4 opencode), the attempt before each retry was one the proxy already flags as a fault: `missing_finish_reason`, `non_2xx`, `upstream_error_payload` or `upstream_disconnect`.
  So retry detection can anchor on the fault.
  Treat the next request with the same `messages_hash` as a retry at any gap.
  Keep the time window only to label identical requests that follow a clean one.
  Every run that retries is discarded under §6 anyway.

### Cross-check inputs (for #15)

| | pi | opencode |
|---|---|---|
| Native record | each assistant `message_end.message.usage`, summed over **all** of them (not the final `agent_end`) | each `step_finish.part.tokens` whose `sessionID` is the run's session |
| `prompt_tokens` | `input + cacheRead + cacheWrite` | `input + cache.read + cache.write` |
| `completion_tokens` | `output` | `output + reasoning` |
| Total | recomputed; ignore upstream `total_tokens` | recomputed; missing when there is no usage |
| Named excluded calls (proxy > native) | compaction summary, split-turn prefix summary (branch summary not reachable headless) | title (1-3 requests, tool-less), task-subagent child sessions |
| Calls on both sides | none beyond the agent turns | compaction (tool-less, yet native includes it) |
| Native silently zero while proxy is not | `no_usage`, `usage_after_done` | `no_usage`, `err200_json` (`step_finish` with zero tokens) |
| Native equals proxy although the frame was faulty | none observed | `usage_after_done` |

For opencode, the §7 side-call heuristic (`has_tools == false`) catches both the title call and compaction.
Only the title call is missing from native.
The gap attribution for #15 must therefore subtract side-calls by name, not the whole `side_call_requests` count.
For pi, every tool-less request is a compaction or summary call, and all of them are missing from native.

On integer counts, with zero tolerance (spec 25 §12):
- pi: the number of assistant `message_end` events equals the proxy's completions requests minus the summarisation calls.
- opencode: the number of main-session `step_finish` events equals the proxy's completions requests minus the title and subagent requests.

### Calibration (for #23)

- The per-arm token tolerance in spec 25 §13.4 reduces to named calls: pi's compaction and summary calls, and opencode's title and subagent calls.
  Running opencode with `--title` removes its title term, which leaves subagents as its only expected gap.
- Both arms exit 0 on runs the proxy must discard.
  pi does so after it gives up on retries.
  opencode does so on a missing `finish_reason` and on a 200 with a JSON error body.
  Neither exit code is evidence of a clean run.
- On the Zen free tier, pi spends 4 requests per turn on a top-level `FreeUsageLimitError` 429, and opencode keeps retrying it until the runner's timeout.
  Both behaviours burn free-cap quota during calibration.
  The runner should abort a run on its first `non_2xx` instead of waiting for the harness.

## Open items

- UNVERIFIED by replay: pi compaction calls, opencode compaction on stdout, opencode subagent steps, the title AI SDK retry, and an opencode retry followed by a success.
  Each needs a longer scripted session.
- UNVERIFIED: the real Zen 429 body shape.
  pi's behaviour depends on whether the error is nested under `error`.
