# Telling opencode 1.17.9 task-subagent requests apart at the proxy

Date: 2026-09-25.
Ticket: YuukiFST/harness-tally#34.
Builds on: `arm-retry-and-native-usage.md` (subagents listed as an UNVERIFIED native-versus-proxy gap) and `arm-wire-surface.md` (headers, §7).

## Summary

Every opencode request carries `X-Session-Id` (and `x-session-affinity`) set to the id of the session that made it.
A task subagent runs in its own child session, so its requests carry the **child's** id, which differs from the run's root session id.
That single comparison classified every request correctly in all four scripted runs (7 child requests, 9 root requests).
opencode also sends `x-parent-session-id: <root id>` on child agent steps, but **not** on a child's compaction request, so that header cannot be the rule on its own.
Native usage can include subagents without any proxy help.
After the run, `opencode db` over the isolated data dir returns per-session token rollups (`session.tokens_*`), and child sessions are rows with `parent_id` set.
Summed over all sessions, those rollups matched the wire exactly in every scenario, except for the title call, which opencode never records.

**Recommendation (most boring, reliable):**
1. The proxy records `X-Session-Id` on every request.
   The runner takes the root id from any stdout event's `sessionID`.
   A request whose `X-Session-Id` differs from that root id is a subagent request.
   `x-parent-session-id` serves as a cross-check only.
2. On the native side, read `opencode db "select id, parent_id, agent, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, tokens_cache_write from session" --format json` after the run, with the run's environment, and attribute per session id.
   With `--title`, native then equals proxy request for request, with no named gap left.

## Method

- **Source.**
  Tag `v1.17.9` = commit `5c23e88419c4743b9be42cea132f2fb1e6cb63ff` of `anomalyco/opencode`, sparse-checked out to `C:/tmp/oc-src`, with paths under `packages/opencode/src/`.
  Each cited function was matched against the minified code embedded in `C:/hbarms/node_modules/opencode-ai/bin/opencode.exe`, cited below as `@<byte offset>`.
- **Wire.**
  `captures/opencode-subagent-attribution/subagent_mock.py` is a recording OpenAI-compatible mock on 127.0.0.1.
  It decides every reply from the request **body** only, never from headers, so the headers remain a pure observation.
  1. If the tools include `task` and the conversation has no tool result yet, it replies with the scenario's `task` tool call(s).
  2. Any other request with tools gets the text `ok`.
  3. Tool-less requests (title, compaction) get fixed text.
  Each response reports distinct usage (prompt `100*(seq+1)+7`, completion `seq+3`), so native records can be matched to wire requests one by one.
- **Isolation.**
  `run.py` launches `opencode.exe run --format json --dir <ws> --pure -m mockollama/MOCK-2.6B --dangerously-skip-permissions [--title unit-01] <prompt>`.
  The provider is passed in `OPENCODE_CONFIG_CONTENT`, and each run gets a fresh `HOME`/`USERPROFILE`/`XDG_*`/`TEMP` under `C:/tmp/hbsub-sandbox/<scenario>`, which is outside any git repo.
  The runs also set `OPENCODE_DISABLE_MODELS_FETCH=1` and `OPENCODE_DISABLE_AUTOUPDATE=1`, and the config is the arm-wire-surface one without test headers.
  No gateway or live upstream was contacted.
- **Read-back.**
  After each run, `run.py` calls `opencode db <sql> --format json` and `opencode export <id>` for every session, using the same environment.
  `summarize.py` then classifies every request by the header rule and compares per-session wire sums with the native rollups and with stdout.

Regenerate from `docs/research/captures/opencode-subagent-attribution/` (about 90 s):

```
python run.py
python summarize.py
```

| Scenario | What it scripts |
|---|---|
| `task-general` | one `task` call, `subagent_type: general`; **no** `--title`, so the title call is on the wire too |
| `task-explore` | one `task` call, `subagent_type: explore` |
| `task-parallel` | two `task` calls in one step (`general` and `explore`) |
| `task-child-compaction` | one `general` task; the child's first step reports `prompt_tokens: 30000` against a 32768 window, forcing a compaction **inside the child** |

Each scenario directory holds `requests.jsonl`, `NNN-body.json`, `stdout.jsonl`, `db-*.json`, `export-{root,child}-<id>.json`, `meta.json` and `summary.json`.

## 1. Headers: yes, `X-Session-Id` identifies the session

Source: `session/llm/request.ts:176-194` (`@100567119`).
For any provider whose id does not start with `opencode`, every request gets `x-session-affinity` and `X-Session-Id` set to `input.sessionID`, plus `x-parent-session-id` whenever `input.parentSessionID` is set.
The agent loop passes `sessionID` and `parentSessionID: session.parentID` (`session/prompt.ts:1321-1323`, `@100644606`).
The task tool creates the child with `parentID: ctx.sessionID` (`tool/task.ts:143-146`, `@100725600`), and the child runs its own prompt loop under the child session id (`tool/task.ts:186-199`).

Two call sites do **not** pass `parentSessionID`.
- Compaction: `processor.process({ user, agent, sessionID, tools: {}, system: [], messages })` (`session/compaction.ts:410-419`, `@100604306`).
- Title: `llm.stream({ ..., sessionID: input.session.id, ... })` (`session/prompt.ts:209-219`).
  Title generation is also skipped outright for child sessions: `if (input.session.parentID) return` (`session/prompt.ts:183`, `@100623589`).

On the wire, taken from `summary.json` of each scenario:

| Scenario | Requests | Root (`X-Session-Id` = root) | Child (`X-Session-Id` ≠ root) | Child without `x-parent-session-id` | Root with `x-parent-session-id` |
|---|---|---|---|---|---|
| `task-general` | 4 | 3 (title, step 0, step 1) | 1 | 0 | 0 |
| `task-explore` | 3 | 2 | 1 | 0 | 0 |
| `task-parallel` | 4 | 2 | 2 (two distinct child ids) | 0 | 0 |
| `task-child-compaction` | 5 | 2 | 3 (step, compaction, step) | **1** (the compaction) | 0 |

The child compaction request, verbatim (`task-child-compaction/requests.jsonl`, seq 2):

```
User-Agent: opencode/1.17.9 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14
x-session-affinity: ses_f2700cb4affez6j0054ev9k6Y5
x-session-id: ses_f2700cb4affez6j0054ev9k6Y5
```

The child step just before it (seq 1) carried the same two ids plus `x-parent-session-id: ses_f2700deaeffe1VSf2qBSlPwvDn`, which is the root's id.
So the rule "`X-Session-Id` ≠ root" is complete, and "`x-parent-session-id` present" misses child compaction.
The title call carries the root id and no parent header (`task-general` seq 0), so it classifies as root.
It stays tool-less and is still told apart by `has_tools == false`, as in #5.

`User-Agent` is identical on root and child requests (`opencode/1.17.9 ai-sdk/provider-utils/4.0.23 runtime/bun/1.3.14`) and carries no session information.

**Where the root id comes from.**
The proxy can take it from the first request of the run, which is always a root request because a child exists only after a root step has called `task`.
Or the runner can take it from stdout, where every event carries `sessionID` (the root's) because of the `run.ts` filter (`cli/cmd/run.ts:650-652`, `@99885276`).
The stdout form is sturdier: it does not depend on request ordering, and the runner already parses stdout.

**Concurrency.**
Two `task` calls in one step ran their child sessions concurrently.
In `task-parallel`, seq 1 and seq 2 were both open at once (`inflight_at_arrival: 2`), with different `X-Session-Id` values.
A per-request header handles this, and an "open request" heuristic would not.

**Scope conditions** (source only):
- With a provider id starting with `opencode`, the other header branch applies: `x-opencode-session` carries the session id and there is **no** parent header (`request.ts:177-184`).
  The rule still works with `x-opencode-session` in place of `X-Session-Id`, but it is UNVERIFIED on the wire.
  Keep the harness provider id outside the `opencode*` prefix.
- `...input.model.headers, ...headers` (from the `chat.headers` plugin hook) are spread **after** these headers (`request.ts:192-193`), so a model `headers` entry or a plugin could overwrite them.
  `--pure` and the harness config set neither.

## 2. Native recovery: yes, from the session store

`run.ts` drops child parts from stdout (`cli/cmd/run.ts:652`), and that was confirmed again here: in every scenario, stdout `step_finish` summed only the root agent steps.
The data is still persisted, though.

- The `session` table has `parent_id`, `agent` and rollup columns `tokens_input`, `tokens_output`, `tokens_reasoning`, `tokens_cache_read`, `tokens_cache_write` and `cost` (schema in `db-tables.json`, `@103287334`).
- The rollup is maintained by the `PartUpdated` projector.
  For every `step-finish` part it adds `{cost, tokens}` to **that part's own session row**, and it subtracts on removal (`@105414572` for `So()`, which extracts step-finish tokens, and `@105419598` for the add).
  It never propagates to the parent.
  UNVERIFIED which file in the `core` package holds this, because only `packages/opencode/src` was checked out.
- `opencode db [query] --format json` runs raw SQL against the store without needing `sqlite3` (`cli/cmd/db.ts:9-37`, `@99971873`).
  It exited 0 in all runs.
- `opencode export <id>` exports **one** session with its messages and `info.tokens` (`cli/cmd/export.ts:284-285`, `@99955874`), and it does not include children.
  Child ids come from `select id from session where parent_id = ?`.
  `opencode session list` lists roots only (`svc.list({ roots: true })`, `cli/cmd/session.ts:87`), so it cannot discover children.
- stdout does give the child id, though not its usage.
  The parent's `tool_use` event for `task` carries `state.metadata.sessionId` (child) and `parentSessionId` (`tool/task.ts:171-176`; seen in `task-general/stdout.jsonl`).

Cross-check.
The mock sends no cache or reasoning tokens, so prompt = `tokens_input` and completion = `tokens_output`.

| Scenario | Wire prompt total | Σ `session.tokens_input` (all sessions) | stdout `step_finish` input | Unexplained |
|---|---|---|---|---|
| `task-general` | 1028 | 921 | 614 | 107 = the title call (not stored anywhere) |
| `task-explore` | 621 | 621 | 414 | 0 |
| `task-parallel` | 1028 | 1028 | 514 | 0 |
| `task-child-compaction` | 31328 | 31328 | 614 | 0 |

Per session, the rollup equals the wire sum for every child session and for every root session that had no title call (`summary.json`, `rollup_equals_wire`).
Completion tokens agree the same way.
The child's compaction is stored as an assistant message with `agent: "compaction"` and `summary: true`, and it is counted in the child's rollup (`task-child-compaction/db-assistant-messages.json`).

Consequence for #15/#23: native = Σ over **all** sessions in the run's isolated data dir.
That equals proxy minus the title call, and it equals proxy exactly under `--title`.
Per-session attribution joins on `session.id` = `X-Session-Id`.
The formulas from `arm-retry-and-native-usage.md` still apply per row: `prompt_tokens = input + cache_read + cache_write`, and `completion_tokens = output + reasoning`.

## 3. Body features: present, but none reliable

| Feature | Observed | Why it is not reliable |
|---|---|---|
| Tool list lacks `task` | Every child request with tools lacked `task`, and every root agent step had it | Child sessions get `task` denied **unless the subagent's merged permission has a `task` rule** (`tool/task.ts:129-139`, `@100725600`). A user config naming `task` keeps it, so this depends on config. It also says nothing about tool-less child compaction |
| Tool list lacks `todowrite` | `explore` child: 7 tools, no `todowrite`. `general` child: 8 tools, **with** `todowrite` | Same config dependence. The global `"*": "allow"` in this config outranked `general`'s own `todowrite: deny` |
| System prompt | `explore` child: `You are a file search specialist…` (`agent/prompt/explore.txt`, `@100779040`). `general` child: same `You are opencode, an interactive CLI tool…` as the root | `general` has no `prompt` (`agent/agent.ts:181-193`), so it inherits the provider default, the same as `build` |
| First user message | The child's first user turn is the `task` prompt text | Arbitrary model-written text |
| Agent name | Not in the body | Stored only in the session row (`session.agent`) and the message row |

The body is a heuristic at best.
The header gives the same answer without any of these conditions.

## Alternatives and why they lose

- **`x-parent-session-id` alone.** It misses child compaction, as shown in `task-child-compaction` seq 2. Use it only as a cross-check.
- **Body heuristics (tool list, system prompt).** They depend on config and agent, and they miss tool-less child calls.
- **`opencode export`.** It covers one session per call, and it needs child ids from `db` anyway. `db` alone does the job in one call.
- **stdout alone.** It never has child usage, only child ids through `task` tool metadata.

## UNVERIFIED

- The `opencode*` provider-id header branch (`x-opencode-session`, no parent header). Source only.
- Nested subagents. `task` is denied in children by default, so a grandchild did not occur. By source, its `X-Session-Id` would be the grandchild id, so the ≠ root rule still classifies it as a subagent request, and its parent header would name the child.
- Background subagents (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true`) and `task_id` resume. A resumed task reuses the existing child id (`tool/task.ts:121-123`). Not replayed.
- Rollup state after a killed run, or after a retried and then successful child step. By #5, failed attempts write no `step-finish`, so they would be on the wire but not in the rollup, which is the same gap as for root steps.
- Which `core` source file holds the rollup projector. The binary offsets are cited instead.
- Real gateway behaviour. Every observation here is from a loopback mock.
