# harness-tally

Coding harnesses each count their own tokens their own way, so harness-tally sits between the harness and the model gateway and writes down the token count the gateway itself reports, one line per request.

It is a small reverse proxy on the Python standard library.
It forwards every byte unchanged, keeps a copy of each request body, and never retries, repairs or fills in anything.
A session interrupted by a refusal or by the daily cap continues the same log when the proxy is started again with the same run id.

## Use

```bash
python -m harness_tally serve \
  --upstream https://openrouter.ai/api/v1 \
  --run-id pi-build-01 \
  --out runs/pi-build-01 \
  --upstream-key-env OPENROUTER_API_KEY
```

The proxy prints one JSON line when it is ready, for example `{"event":"ready","port":53817,"base_url":"http://127.0.0.1:53817",...}`.
Point the harness's OpenAI-compatible provider at that `base_url` (no `/v1`), with the literal key `harness-tally`: the proxy injects the real key, so the harness never holds it.
Close the proxy's stdin (or press Ctrl-C) to stop it.

```bash
python -m harness_tally summarize runs/pi-build-01
```

writes `runs/pi-build-01/summary.json`: requests answered and refused, tokens (input, cached, output, reasoning), tool calls, and a count of every flag.

## What gets written

- `records.jsonl`: one record per request, including refused and broken ones (`harness-tally/record/1`).
- `bodies/<seq>.json`: the request body exactly as the harness sent it.
- `summary.json`: sums over the records (`harness-tally/summary/1`).

Flags mark what a reader should not trust blindly: `non_2xx`, `error_payload`, `model_substituted`, `no_usage`, `missing_finish_reason`, `usage_after_done`, `upstream_disconnect`, `upstream_unreachable`, `client_disconnect`, `shutdown_in_flight`.

## Install and test

```bash
pip install "harness-tally @ git+https://github.com/YuukiFST/harness-tally@<commit sha>"
python -m pip install -e ".[dev]" && python -m pytest
```

Design notes and the decisions behind them are in `docs/` and in [the map](https://github.com/YuukiFST/harness-tally/issues/1).
