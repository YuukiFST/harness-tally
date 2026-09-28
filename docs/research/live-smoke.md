# Does one live pi session go through harness-tally to OpenRouter free?

Question ([#23](https://github.com/YuukiFST/harness-tally/issues/23), re-scoped by [#43](https://github.com/YuukiFST/harness-tally/issues/43)): does pi 0.80.10 reach OpenRouter's free tier through the proxy over HTTPS, with the key injected by the proxy, and does the proxy's gateway `usage` equal pi's native `message_end` usage?

## Answer

Yes, for `qwen/qwen3.8-27b:free` on the first attempt, 2026-09-28 14:49Z.
The proxy recorded 1593 input / 25 output / 23 reasoning tokens; pi's `message_end` reported the same 1593 / 25 / 23.
`google/gemma-4-31b-it:free` was refused 5 times out of 5 by its shared pool, and each refusal was recorded as one `non_2xx` record with `limit_source: upstream_provider_shared_pool`.

## Method

- Script: `captures/live-smoke/run.py <model>`, one prompt ("Reply with the single word: ok"), pi agent retry off, so one attempt is one request.
- Budget stated before the first attempt: at most 1 accepted completion per model, at most 15 attempts per model, spaced 60 to 90 s, stop at any 429 other than `upstream_provider_shared_pool`.
  Spent: 1 accepted completion (qwen), 5 pool refusals (gemma).
- The pool sampler had stopped (no `sampler.pid`) before the first attempt, so no two live probes overlapped.
- The arm held only the literal key `harness-tally`; the proxy injected the real key from `--upstream-key-env OPENROUTER_API_KEY`.
  The script scanned every file it wrote for the key and found none.

## Results

| Run | Model | Status | Proxy usage (in / out / reasoning) | pi `message_end` usage | pi exit |
|---|---|---|---|---|---|
| `run-20260928T144919Z-qwen` | qwen | 200, `model_echoed` = requested, provider ModelRun | 1593 / 25 / 23 | 1593 / 25 / 23 | 0 |
| `run-20260928T145052Z-google` | gemma | 429 pool | none | 0 / 0 | 0 |
| `run-20260928T145236Z-google` | gemma | 429 pool | none | 0 / 0 | 0 |
| `run-20260928T145411Z-google` | gemma | 429 pool | none | 0 / 0 | 0 |
| `run-20260928T145550Z-google` | gemma | 429 pool | none | 0 / 0 | 0 |
| `run-20260928T145731Z-google` | gemma | 429 pool | none | 0 / 0 | 0 |

- `GET /api/v1/key` after the last run: `free_model_daily_requests.used` = 3, which is 2 sampler successes plus the one qwen success.
  The five pool refusals spent nothing, as in [the pool measurement](pool-availability.md).
- The proxy exited 0 on stdin EOF in all six runs.

## What this settles

1. HTTPS upstream, key injection, and the gateway `usage` as the count work end to end on the live route.
2. **pi exits 0 after a refused request.** A caller cannot tell a refusal from a finished session by pi's exit code; it must read the proxy's records (`refused` in `summary.json`).
3. Byte-exact forwarding is checked by the test suite against captured OpenRouter bytes; live, pi parsed the forwarded stream and its native usage matched.

## Unverified

- A gemma success through the proxy.
- A multi-step session with tool calls on the live route.
