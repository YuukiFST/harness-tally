# What pi 0.80.10 and opencode 1.17.9 put on the wire

Date: 2026-09-25.
Ticket: [#4](https://github.com/YuukiFST/harness-tally/issues/4), part of [#1](https://github.com/YuukiFST/harness-tally/issues/1).
Feeds: [#10](https://github.com/YuukiFST/harness-tally/issues/10) (max_tokens contract) and [#11](https://github.com/YuukiFST/harness-tally/issues/11) (run/unit attribution).

## Answer in one table

| # | Question | pi 0.80.10 | opencode 1.17.9 |
|---|---|---|---|
| 1 | Paths and join | Only `POST {baseUrl}/chat/completions`; no `/models` probe; a trailing `/` on `baseUrl` is absorbed | Only `POST {baseURL}/chat/completions`; no `/models` probe to the provider; trailing `/` stripped; fetches `models.dev` (a different host) unless `OPENCODE_DISABLE_MODELS_FETCH` |
| 2 | `stream`, `include_usage` | Always `stream: true`; `stream_options.include_usage: true` unless `compat.supportsUsageInStreaming: false` | Always `stream: true`; `stream_options.include_usage: true` unless `options.includeUsage: false` |
| 3 | Output cap | `max_completion_tokens` by default (`max_tokens` with `compat.maxTokensField`), value `min(maxTokens, contextWindow − estimate − 4096)`, floor 1; `maxTokens` defaults to 16384 | `max_tokens` always, value `min(limit.output, OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX or 32000)`; 32000 with no `limit` |
| 4 | Side-calls | No title; compaction is one tool-less request after the loop, same headers | Title call on every run unless `--title`; compaction on overflow is a tool-less request mid-loop; all carry the same headers |
| 5 | Static headers, env | **Yes.** `headers` at provider and model level; `$VAR`/`${VAR}` interpolated; a missing variable **fails closed** (no request sent) | **Yes.** `options.headers` and model `headers`; `{env:VAR}` substituted in config text, including `OPENCODE_CONFIG_CONTENT`; a missing variable **fails open** (header sent empty) |
| 6 | Two in flight | Never observed; loop is sequential | **Yes**: the title call runs concurrently with step 0; `--title` removes it |
| 7 | Headers | OpenAI JS SDK set (`User-Agent: OpenAI/JS 6.26.0`, `X-Stainless-*`); `accept-encoding: gzip, deflate` on http | `User-Agent: opencode/1.17.9 …`, `x-session-affinity` and `x-session-id` = opencode session id; `Accept-Encoding: gzip, deflate, br, zstd` |

## Method

Both arms were run from the pinned install at `C:/hbarms` (`pi --version` → `0.80.10`, `opencode --version` → `1.17.9`) against a local recording mock on `127.0.0.1`, never a gateway.
The mock records the request line, every header in arrival order and original case, the raw body, and arrival and finish times; it holds each reply for 0.8 s so that overlapping requests show up.
Agent-loop requests (non-empty `tools`) get a `read` tool call on a probe file first and a text reply after; tool-less requests get a fixed short text.
It is modelled on harness-bench `layer1/src/hb_layer1/mock_server.py` (HEAD 9c0fe11).

The invocations and isolation copy harness-bench `layer1/src/hb_layer1/arms.py`, isolated profile: a fresh `HOME`, `USERPROFILE`, `XDG_*`, `TEMP`/`TMP`/`TMPDIR` and `PI_CODING_AGENT_DIR` per scenario under `C:/tmp/hbwire-sandbox`, which is outside any git repository.
pi ran as `pi --mode json --no-session --model mockollama/MOCK-2.6B "<prompt>"` with `PI_OFFLINE=1`.
opencode ran as `opencode run --format json --dir <ws> --pure -m mockollama/MOCK-2.6B --dangerously-skip-permissions "<prompt>"` with the provider in `OPENCODE_CONFIG_CONTENT`, stdin from the null device.
The provider blocks are the arms.py ones plus test headers; each scenario's exact config is in its `meta.json`.

One command regenerates every capture: `python docs/research/captures/arm-wire-surface/survey.py`.
Scenarios, each in its own directory under `docs/research/captures/arm-wire-surface/`:

| Scenario | What varies |
|---|---|
| `pi-baseline`, `opencode-baseline` | Base URL `…/v1`; provider-level headers `x-hb-run` and `x-hb-unit` from env, `x-hb-static` literal; model-level `x-hb-model-header` |
| `*-trailing-slash` | Base URL `…/v1/`, no test headers |
| `*-missing-env` | Same config, `HB_RUN_ID` and `HB_UNIT_ID` unset |
| `*-compaction` | Mock reports `prompt_tokens: 30000` against a 32768 window; pi also gets `compaction.keepRecentTokens: 10` so a short conversation has something to summarise; opencode gets the inflated count on step 0 only, because on every response it compacts in a loop |
| `pi-default-maxtokens` | No `maxTokens` in `models.json`, `compat.maxTokensField: "max_tokens"` |
| `opencode-title` | `--title unit-01` |
| `opencode-default-output` | No `limit` block on the model |
| `opencode-output-env` | `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX=1234` |

Each directory holds `requests.jsonl` (one line per request: request line, headers, body keys, timings, in-flight count), `NNN-body.json` (the raw body, byte for byte), `stdout.jsonl`, `stderr.txt` and `meta.json` (command, env tags, exit code, `max_inflight`, provider config).

### What could and could not be read

pi is plain JavaScript; every pi citation below is a `file:line` under `C:/hbarms/node_modules/@earendil-works/pi-coding-agent/`, with `pi-ai`, `pi-agent-core`, `openai` (6.26.0) and `undici` (8.5.0) nested under its `node_modules/`.

opencode ships as a Bun single-file executable, `C:/hbarms/node_modules/opencode-ai/bin/opencode.exe`.
The bundled JavaScript sits in the binary as minified plain text, so it was read by searching the file; citations are `opencode.exe@<byte offset>` into that file (sha256 `65b07124…f353f6`).
Minified names (`jQ`, `qy`, `YN`) are the bundler's, not opencode's; the meaning is read from the code around them.
Bun's own `fetch` is native code and could not be read; opencode's `Accept-Encoding` and header ordering rest on the wire only.

npm skipped `opencode-ai`'s postinstall.
That script (`opencode-ai/postinstall.mjs`) only picks a platform package (AVX2 or baseline) and copies its binary into `opencode-ai/bin/opencode.exe`; it changes no configuration.
The binary already in `opencode-ai/bin/` is byte-identical to `opencode-windows-x64/bin/opencode.exe` (same sha256), so the skip had no effect on what was measured.

## pi 0.80.10

### 1. Paths, methods, base-URL join

Every request in every scenario was `POST /v1/chat/completions`; no `GET` and no other path reached the mock.
pi builds an `OpenAI` client with `baseURL: model.baseUrl` (`node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js:442-447`) and calls `client.chat.completions.create` (`:135-137`).
The SDK joins `baseURL + path` and drops the doubled slash when the base ends in `/` (`node_modules/openai/client.js:220-224`).
Confirmed: `…/v1` and `…/v1/` both produced `POST /v1/chat/completions HTTP/1.1` (`pi-baseline`, `pi-trailing-slash`).
The only `/models` fetch in `pi-ai` is the GitHub Copilot OAuth path (`node_modules/@earendil-works/pi-ai/dist/auth/oauth/github-copilot.js:86`), which a custom provider does not reach.
The SDK retry is off by default: `maxRetries: options?.maxRetries ?? 0` (`openai-completions.js:133`), fed from `settings.retry.provider.maxRetries`, unset by default (`dist/core/sdk.js:186`, `dist/core/settings-manager.js:571-577`); pi's own retry (`dist/core/agent-session.js:2095`) is a new request per attempt.

### 2. `stream` and `stream_options.include_usage`

`stream: true` is a literal in `buildParams` (`openai-completions.js:455`); there is no non-streaming path for this API.
`stream_options: { include_usage: true }` is set whenever `compat.supportsUsageInStreaming !== false` (`:462-464`), and the detected default is `true` for every provider (`:1043`).
Confirmed on all 9 captured pi requests, including the compaction call.

### 3. `max_tokens` / `max_completion_tokens`

pi sends one of the two, never both (`openai-completions.js:468-474`).
The field is `max_completion_tokens` unless `compat.maxTokensField` is `"max_tokens"` (`:1089`) or the base URL matches a hard-coded list (chutes.ai, Moonshot, Cloudflare AI Gateway, Together, NVIDIA, Ant Ling; `:1034`, `:1044`).
A proxy on `127.0.0.1` matches none of them, so pi pointed at the proxy sends `max_completion_tokens`, and the same detection also turns on `store: false` (`:465-467`, `supportsStore: !isNonStandard` at `:1040`).

The value is not a constant.
`buildBaseOptions` passes `clampMaxTokensToContext(model, context, model.maxTokens)` (`node_modules/@earendil-works/pi-ai/dist/api/simple-options.js:13`), which returns `min(maxTokens, contextWindow − estimateContextTokens(context) − 4096)` with a floor of 1 (`:2-9`).
`maxTokens` comes from `models.json` and defaults to 16384 (`dist/core/provider-composer.js:70`); `contextWindow` defaults to 128000 (`:69`).
Confirmed values:

- `pi-baseline`: `"max_completion_tokens": 4096` on both requests (`maxTokens: 4096`).
- `pi-default-maxtokens`: `"max_tokens": 16384` (no `maxTokens`, `compat.maxTokensField: "max_tokens"`).
- `pi-compaction`: 4096 on step 0, then `"max_completion_tokens": 1` on step 1, because the mock reported 30000 prompt tokens against a 32768 window and the clamp bottomed out.

So `models.json` controls both the field and the ceiling, and the context estimate lowers it request by request as the conversation grows.

### 4. Side-calls

pi has no title generation (harness-bench `docs/research/10-pi-measurement-surface.md` §8).
Compaction runs after the agent loop ends (`dist/core/agent-session.js:782`, inside `_handlePostAgentRun`) or before a new prompt (`:868`), when the last usage exceeds `contextWindow − reserveTokens` (`dist/core/compaction/compaction.js:137-141`, default `reserveTokens` 16384) or the response overflowed (`agent-session.js:1531-1558`).
Its output cap is `min(floor(0.8 × reserveTokens), maxTokens)` (`compaction.js:422`) or `0.5 ×` for a split turn prefix (`:580`), then clamped the same way as the main loop.
Its auth and headers come from the same resolution as the main loop (`agent-session.js:1603-1609`).

Confirmed in `pi-compaction`: after the two loop requests, request 2 arrived with no `tools`, 2 messages (system `"You are a context summarization assistant…"` and a user turn wrapping the conversation), `"max_completion_tokens": 4096`, the same `stream_options`, and all four `x-hb-*` headers.
stdout shows `agent_end`, `compaction_start`, `compaction_end` (`"reason": "threshold"`), `agent_settled`.
With the default `keepRecentTokens` (20000) and the same inflated usage, pi fired no compaction request, because the short conversation had nothing older than the kept tail (`prepareCompaction`, `compaction.js:456-484`); compaction on a real unit happens only once the history is long.
Branch summarisation (`dist/core/compaction/branch-summarization.js:223`) needs `/tree` navigation and is not reachable from a single `--mode json` prompt.

### 5. Static headers and env interpolation — YES, fails closed

`headers` is accepted at provider level, model level and in `modelOverrides` (`dist/core/model-config.js:136`, `:153`, `:162`; `docs/models.md:140`).
Provider headers are resolved by `resolveHeadersOrThrow` (`dist/core/provider-composer.js:241-243`, `dist/core/resolve-config-value.js:234-242`); model headers are merged from the model definition (`provider-composer.js:264-271`).
Each value goes through `resolveConfigValue` (`resolve-config-value.js:123-129`): `$VAR` and `${VAR}` are replaced from the environment, also inside a longer literal (`:21-64`), `$$` escapes a dollar, and a leading `!` runs a shell command (`:65-70`); `docs/models.md:149-167` documents the same rules.
A variable that is unset or empty makes the value unresolved (`:71-73`, `:90-92`) and `resolveConfigValueOrThrow` throws (`:199-217`).

Confirmed in `pi-baseline`: with `"x-hb-run": "$HB_RUN_ID"`, `"x-hb-unit": "${HB_UNIT_ID}"`, `"x-hb-static": "literal-value"` at provider level and `"x-hb-model-header": "model-level"` at model level, every request carried

```
x-hb-run: run-0001
x-hb-unit: unit-01
x-hb-static: literal-value
x-hb-model-header: model-level
```

and so did the compaction request in `pi-compaction`.

Confirmed in `pi-missing-env`: with the two variables unset, **no request reached the mock**.
The throw surfaces as `ModelsError("auth", "API key auth failed for provider mockollama")` (`node_modules/@earendil-works/pi-ai/dist/auth/resolve.js:92`), recorded as an assistant message with `"stopReason":"error"` in `stdout.jsonl`, and pi exited **0**.
A runner therefore has to read the event stream to see this; the exit code does not show it.

### 6. Requests in flight

`max_inflight` was 1 in every pi scenario, compaction included.
The loop awaits each `streamAssistantResponse` before running tools and looping (`node_modules/@earendil-works/pi-agent-core/dist/agent-loop.js:84-122`); tool calls may run in parallel (`:287-293`) but pi's built-in tools make no model requests; compaction runs after the loop has ended.

### 7. Request headers

Verbatim from `pi-baseline/requests.jsonl`, request 0, in arrival order:

```
POST /v1/chat/completions HTTP/1.1
host: 127.0.0.1:61300
connection: keep-alive
Accept: application/json
User-Agent: OpenAI/JS 6.26.0
X-Stainless-Retry-Count: 0
X-Stainless-Timeout: 300
X-Stainless-Lang: js
X-Stainless-Package-Version: 6.26.0
X-Stainless-OS: Windows
X-Stainless-Arch: x64
X-Stainless-Runtime: node
X-Stainless-Runtime-Version: v24.20.0
authorization: Bearer layer1
x-hb-run: run-0001
x-hb-unit: unit-01
x-hb-static: literal-value
x-hb-model-header: model-level
content-type: application/json
accept-language: *
sec-fetch-mode: cors
accept-encoding: gzip, deflate
content-length: 5656
```

Body keys, in order: `model, messages, stream, stream_options, store, max_completion_tokens, tools`.
The SDK default set is at `node_modules/openai/client.js:504-515`.
`accept-encoding` comes from undici's fetch, which pi installs globally (`dist/core/http-dispatcher.js:66-89`): `gzip, deflate` on `http:` and `br, gzip, deflate` on `https:` (`node_modules/undici/lib/web/fetch/index.js:1561-1566`).
The `https:` value is from source only; UNVERIFIED on the wire, since the mock is plain http.
No `content-encoding` was sent; request bodies are uncompressed.
pi adds `x-opencode-session` and `x-opencode-client` only when the provider id is `opencode`/`opencode-go` or the base URL host is `opencode.ai` (`dist/core/provider-attribution.js:49-58`), so a proxy on another host sees none of them.

## opencode 1.17.9

### 1. Paths, methods, base-URL join

Every request in every scenario was `POST /v1/chat/completions`; no `GET` reached the mock.
The bundled `@ai-sdk/openai-compatible` 2.0.41 builds URLs as `new URL(\`${Y}${E}\`)` with `Y` the base URL with its trailing slash removed (`opencode.exe@99367640`, `function jQ(G){let Y=IG(G.baseURL)…`), and the chat model posts to `path:"/chat/completions"` (`@99329213`).
Confirmed: `…/v1` and `…/v1/` both produced `POST /v1/chat/completions HTTP/1.1` (`opencode-baseline`, `opencode-trailing-slash`).
Off-provider traffic the mock cannot see: at start-up and every 60 minutes opencode fetches the `models.dev` catalogue unless `OPENCODE_DISABLE_MODELS_FETCH` is set (`@105370470`); this goes to that host, not to the base URL.
No `timeout` or `chunkTimeout` behaviour was exercised.

### 2. `stream` and `stream_options.include_usage`

The chat model sends `stream: true` and `stream_options: includeUsage ? {include_usage: true} : undefined` (`@99329213`).
opencode turns `includeUsage` on for every `@ai-sdk/openai-compatible` provider unless the config sets it to `false`: `if(A.api.npm.includes("@ai-sdk/openai-compatible")&&N.includeUsage!==!1)N.includeUsage=!0` (`@102817111`).
Confirmed on all 21 captured opencode requests, title and compaction calls included.

### 3. `max_tokens`

The openai-compatible chat model maps the AI SDK's `maxOutputTokens` to `max_tokens` (`@99326790`, `args:{model:…,user:…,max_tokens:Y,…}`); it never sends `max_completion_tokens`.
opencode computes `maxOutputTokens: Oo.maxOutputTokens(o.model, o.flags.outputTokenMax)` in `LLMRequestPrep.prepare` (`@100566092`), which is `function qy($,Z=YN){return Math.min($.limit.output,Z)||Z}` (`@102786449`) with `YN=32000` (`@102766435`); the flag is the env var `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX` (`@105740381`).
The same function feeds the title and compaction calls.
Confirmed values:

- `opencode-baseline`: `"max_tokens": 4096` on all three requests (`limit.output: 4096`), title included.
- `opencode-default-output`: `"max_tokens": 32000` on all three (no `limit` block).
- `opencode-output-env`: `"max_tokens": 1234` on all three (`OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX=1234`, `limit.output: 4096`).

Unlike pi, the value does not shrink as the context grows.
A `limit` block without `output` is rejected at start-up (`Configuration is invalid at OPENCODE_CONFIG_CONTENT ↳ Missing key provider.mockollama.models.MOCK-2.6B.limit.output`, exit 1, seen while building `opencode-default-output`).

### 4. Side-calls, and `--title`

Title generation runs on the first loop iteration of a session whose title is still the default: `SessionPrompt.ensureTitle` returns early `if(!U.isDefaultTitle(a.session.title))` (`@100623659`) and otherwise streams a tool-less request with the `title` agent, the small model and `retries:2` (`@100623603`).
It is forked, not awaited: `if(I++,I===1)yield*Eo({…}).pipe(l.ignore,l.forkIn(d))` (`@100642028`).
`--title <text>` sets a non-default title, so no title call is made.

Confirmed: `opencode-baseline` made 3 requests, the first being tool-less with system prompt `"You are a title generator. You output ONLY a thread title…"`, `"max_tokens": 4096` and all `x-hb-*` headers; `opencode-title` (`--title unit-01`) made 2, both agent steps.

Compaction: after a step whose usage overflows, the loop queues a compaction (`if(H&&H.summary!==!0&&(yield*y.isOverflow({tokens:H.tokens,model:N})))`, `@100642478`), processes it on the next iteration, and continues the loop.
Confirmed in `opencode-compaction`: request 2 arrived between the two agent steps, tool-less, 5 messages, system `"You are an anchored context summarization assistant for coding sessions…"`, `"max_tokens": 4096`, same headers; the run then finished normally.
When the mock reported the inflated count on every response, opencode compacted after every step and never finished; the harness killed it (first attempt, not kept).

### 5. Static headers and env interpolation — YES, fails open

Provider `options` are handed to `createOpenAICompatible`, which merges `options.headers` after `Authorization` (`@99367640`: `U={...G.apiKey&&{Authorization:\`Bearer ${G.apiKey}\`},...G.headers}`).
Model-level `headers` are added per request after opencode's own (`@100567119`: `…"User-Agent":pi},...o.model.headers,...c`).
Config text is passed through `ConfigVariable.substitute` before JSON parsing: `g.text.replace(/\{env:([^}]+)\}/g,(R,E)=>{return(g.env?.[E]??process.env[E])||""})` (`@103250048`).
`OPENCODE_CONFIG_CONTENT` goes through the same loader (`@103240497` calls `q(process.env.OPENCODE_CONFIG_CONTENT,…)`, and `q` calls `j2.substitute` at `@103235892`).
The replacement is textual, inside the JSON source, so a value containing `"` or `\` would corrupt the config; run and unit ids should stay within `[A-Za-z0-9._-]`.

Confirmed in `opencode-baseline`: with `"x-hb-run": "{env:HB_RUN_ID}"`, `"x-hb-unit": "{env:HB_UNIT_ID}"` and `"x-hb-static": "literal-value"` in `provider.mockollama.options.headers`, and `"x-hb-model-header": "model-level"` on the model, every request, the title call included, carried

```
x-hb-model-header: model-level
x-hb-run: run-0001
x-hb-static: literal-value
x-hb-unit: unit-01
```

Confirmed in `opencode-missing-env`: with the variables unset, the run proceeded and every request carried `x-hb-run: ` and `x-hb-unit: ` with **empty values**; exit 0.

Because the runner already generates `OPENCODE_CONFIG_CONTENT` per invocation, it can also write the literal run and unit ids into it, with no env indirection at all.

### 6. Requests in flight

Yes.
The title call is forked alongside step 0 (see §4), and the mock saw two requests open at once in every scenario without `--title`: in `opencode-baseline` the title request arrived at 6798 ms and the step-0 request at 6861 ms, while the first was still open (`inflight_at_arrival: 2`, `max_inflight: 2`).
`opencode-title` stayed at `max_inflight: 1`.
UNVERIFIED: whether subagent sessions started by the `task` tool can run concurrently when a step emits two `task` calls; the mock script never asks for `task`, so this was not exercised.

### 7. Request headers

Verbatim from `opencode-baseline/requests.jsonl`, request 1 (step 0), in arrival order:

```
POST /v1/chat/completions HTTP/1.1
Authorization: Bearer layer1
Content-Type: application/json
User-Agent: opencode/1.17.9 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14
x-hb-model-header: model-level
x-hb-run: run-0001
x-hb-static: literal-value
x-hb-unit: unit-01
x-session-affinity: ses_f279e8758ffer5Xc2A5yaYZmdM
x-session-id: ses_f279e8758ffer5Xc2A5yaYZmdM
Connection: keep-alive
Accept: */*
Host: 127.0.0.1:61397
Accept-Encoding: gzip, deflate, br, zstd
Content-Length: 30038
```

Body keys, in order: `model, max_tokens, messages, tools, tool_choice, stream, stream_options` for agent steps and `model, max_tokens, messages, stream, stream_options` for tool-less calls.
For any provider whose id does not start with `opencode`, opencode sends `x-session-affinity` and `X-Session-Id` set to its session id, `x-parent-session-id` for child sessions, and `User-Agent: opencode/1.17.9` (`@100567119`); a provider id starting with `opencode` gets `x-opencode-project`, `x-opencode-session`, `x-opencode-request` and `x-opencode-client` instead (same offset).
The session id was the same on every request of one process and different across processes.
`Accept-Encoding: gzip, deflate, br, zstd` is Bun's fetch default, observed on the wire; its source is native and was not read, so the value over `https:` is UNVERIFIED.
No `Content-Encoding` was sent.

## Consequences for the proxy

### For #10, the max_tokens contract

- The proxy has to handle both field names: pi pointed at a proxy URL sends `max_completion_tokens`, opencode sends `max_tokens`. Forcing one field while leaving the other in place sends the upstream two conflicting caps.
- pi's value moves: its own clamp (`contextWindow − estimate − 4096`) lowered it to 1 in the compaction scenario. Overwriting it with the model's published cap removes the protection pi relies on to stay inside `contextWindow`, so a late-unit request can ask for more output than the window leaves room for. The contract has to state whether the forced value replaces pi's value or caps it.
- opencode's value is fixed per run (`limit.output`, else 32000) and identical on title, compaction and loop requests.
- Spec 25 §7 marks side-calls by "`max_tokens` below the run's configured value". That does not hold here: opencode's title and compaction calls carry the same `max_tokens` as the loop, and pi's compaction call carried 4096, the same as its loop. `has_tools == false` separated every side-call in these captures; the client's original cap, recorded before the rewrite, is still needed for the audit trail.
- Both arms always stream with `include_usage: true`, so the spec 25 §3 rewrite stays a no-op for both.
- pi at a proxy URL also sends `store: false`, which it would not send to `opencode.ai` (`supportsStore: !isNonStandard`). If Zen rejects `store` or `max_completion_tokens`, set `compat.supportsStore: false` and `compat.maxTokensField: "max_tokens"` in the pi recipe. Whether Zen rejects them: UNVERIFIED; no gateway call was made.

### For #11, run/unit attribution

- Header tagging works on both arms at the pinned versions, on every request including title and compaction calls: pi via `models.json` `headers` with `$VAR`, opencode via `provider.<id>.options.headers` with `{env:VAR}` or literal values written into `OPENCODE_CONFIG_CONTENT`.
- The two arms fail in opposite directions when the variable is missing: pi sends nothing and exits 0; opencode sends the header with an empty value. The proxy should treat a missing or empty tag as a fault (reject or mark the request unattributable), and the runner should check that the event stream shows no auth error.
- opencode keeps two requests open at once at the start of every run without `--title`, so attribution cannot rely on "the one open request"; a per-request header does not have this problem.
- opencode already sends a per-process `x-session-id`, which groups one invocation's requests without any runner configuration; it does not name the run or unit, so it is a cross-check, not an identifier.
- Whether the proxy strips the `x-hb-*` tags before forwarding is a #11 decision; forwarding them leaks run ids to the gateway, stripping them is one more rewrite the record has to note.
