# How often do the two free models' shared pools accept a request?

Question ([#41](https://github.com/YuukiFST/harness-tally/issues/41)): over paced single requests, what share do the shared free pools of `qwen/qwen3.8-27b:free` (ModelRun) and `google/gemma-4-31b-it:free` (Google AI Studio) accept, at which hours, and is that enough for one build to finish?

## Answer

Each pool accepted **1 of 11** paced attempts (9%).
Every refusal was a 429 with `limit_source: upstream_provider_shared_pool`.
Refusals spent no account quota: `free_model_daily_requests.used` went from 0 to 2, exactly the two successes.
The free route can carry a build only as a session that retries refused requests; it cannot carry a run that any refusal discards.

## Method

- Sampler: `docs/research/captures/pool-availability/sample.sh`, started 2026-09-28 10:50:22Z.
- Each round sent the p1 request of [#26](https://github.com/YuukiFST/harness-tally/issues/26) once per model, qwen first, about 8 s apart; rounds 20 minutes apart.
- Planned for up to 72 rounds (24 h).
  The author stopped it after round 11 at 14:31:58Z, because [#43](https://github.com/YuukiFST/harness-tally/issues/43) made refusals non-fatal (`sampler.log`).
- Raw data: `captures/pool-availability/attempts.tsv`, one byte-exact response per attempt under `captures/pool-availability/attempts/`.

## Results

| Model | Attempts | 200 | 429 `upstream_provider_shared_pool` | Other 429 | Success at (UTC) |
|---|---|---|---|---|---|
| `qwen/qwen3.8-27b:free` | 11 | 1 | 10 | 0 | 11:10:37 (round 2) |
| `google/gemma-4-31b-it:free` | 11 | 1 | 10 | 0 | 12:31:59 (round 6) |

- Window covered: 10:50Z to 14:13Z on Monday 2026-09-28, about 3.4 hours of one weekday.
  No night or weekend hours were sampled.
- Counter `free_model_daily_requests.used`: 0 before round 1; 0 right after the qwen 200 (round 2); 1 from round 3; 2 from round 7 onward.
  It lags a success by up to one round, then matches the success count exactly.
- TTFB: refusals 0.37 to 1.38 s; successes 0.96 s (qwen) and 1.04 s (gemma).
- No two consecutive rounds succeeded for the same model, and the two successes were 81 minutes apart.

## What this settles

1. **Pool 429s are free.** 20 refusals, 0 quota spent.
   This contradicts the pricing FAQ line "Failed attempts count toward that daily cap" (`captures/shared-pool-bypass/docs/or-pricing-faq.txt:35`) for this 429 kind; the observed counter wins.
   The binding account limit stays 50 accepted requests a day.
2. **No retry window exists at 20-minute spacing.** Successes are isolated, not clustered in an hour.
   A capture that stops at the first 429 cannot plan around a window; it has to retry.
3. **A discard-on-refusal run cannot finish.** At 1 in 11 per attempt, a run of n requests with zero refusals has probability about 0.09^n.
4. **A retrying session can finish, at a cost in wall time.** At the sampled rate a session needs about 11 attempts per accepted request.
   Whether back-to-back retries do better or worse than 20-minute spacing is not measured here; the live smoke in [#23](https://github.com/YuukiFST/harness-tally/issues/23) is the first data point.

## Unverified

- The acceptance rate at short retry spacing (seconds) and at other hours or days.
- Whether pool 429s count toward the 20 requests/minute limit.
