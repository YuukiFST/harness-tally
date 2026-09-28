#!/usr/bin/env bash
# Samples how often the free shared pools accept a request (ticket #41).
# Usage: bash docs/research/captures/pool-availability/sample.sh
# One p1 request (from #26) per model per round, qwen first, 6 s apart; rounds 20 min apart; <=24 h.
# A pool 429 (limit_source=upstream_provider_shared_pool) ends only that attempt: 3/3 observed
# pool 429s left free_model_daily_requests.used at 0 (#26). Any other 429, or the counter
# moving past our own success count, stops everything. <=2 successes per model (<=4 of 50/day).
# The key is piped to curl on stdin (-H @-), never on the command line or on disk.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
BASE=https://openrouter.ai/api/v1
REQ=$D/../openrouter-wire-profile/requests
ROUND_S=${ROUND_S:-1200}
MAX_ROUNDS=${MAX_ROUNDS:-72}
MAX_OK=2
K=${OPENROUTER_API_KEY:-$(powershell.exe -NoProfile -Command '[Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY","User")' | tr -d '\r\n')}
[ -n "$K" ] || { echo "no OPENROUTER_API_KEY"; exit 2; }
mkdir -p attempts
TSV=$D/attempts.tsv
[ -f "$TSV" ] || printf 'utc\tround\tmodel\tstatus\tlimit_source\tttfb_s\tused_after\tfile\n' > "$TSV"
echo $$ > "$D/sampler.pid"

auth() { printf 'Authorization: Bearer %s\n' "$K"; }
used() {
  auth | curl -sS -H @- -H 'Accept-Encoding: identity' "$BASE/key" |
    PYTHONUTF8=1 python -c "import json,sys; print(json.load(sys.stdin)['data']['free_model_daily_requests']['used'])"
}
field() { # file -> limit_source of a JSON error body, or '-'
  PYTHONUTF8=1 python - "$1" <<'EOF'
import json, sys
t = open(sys.argv[1], encoding='utf-8', errors='replace').read()
i = t.find('{')
try:
    print(json.loads(t[i:t.rfind('}') + 1])['error']['metadata'].get('limit_source') or '-')
except Exception:
    print('NOT_JSON')
EOF
}
stop() { echo "$(date -u +%FT%TZ) STOP: $1" | tee -a "$D/sampler.log"; rm -f "$D/sampler.pid"; exit "${2:-0}"; }

declare -A OK=([qwen]=0 [gemma]=0)
U0=$(used) || stop "cannot read /key" 1
echo "$(date -u +%FT%TZ) start used=$U0 round_s=$ROUND_S max_rounds=$MAX_ROUNDS" | tee -a "$D/sampler.log"
for r in $(seq 1 "$MAX_ROUNDS"); do
  for m in qwen gemma; do
    [ "${OK[$m]}" -ge "$MAX_OK" ] && continue
    TS=$(date -u +%Y%m%dT%H%M%SZ); OUT=attempts/$TS-$m.txt; H=$(mktemp); B=$(mktemp)
    META=$(auth | curl -sS -N --raw --max-time 240 -H @- -H 'Content-Type: application/json' \
      -H 'Accept-Encoding: identity' --data-binary @"$REQ/$m-p1-pi-stream-usage.json" \
      -D "$H" -o "$B" -w '%{http_code} %{time_starttransfer}' "$BASE/chat/completions" 2>&1)
    { echo "# $TS round $r $m p1; Authorization sent, not recorded"; echo "# ---- response headers ----"
      cat "$H"; echo "# ---- response body (raw bytes follow) ----"; cat "$B"; } > "$OUT"
    CODE=${META%% *}; TTFB=${META##* }
    LS=-; [ "$CODE" = 429 ] && LS=$(field "$B")
    rm -f "$H" "$B"
    [ "$CODE" = 200 ] && OK[$m]=$((OK[$m] + 1))
    sleep 5
    U=$(used) || stop "cannot read /key" 1
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$TS" "$r" "$m" "$CODE" "$LS" "$TTFB" "$U" "$OUT" >> "$TSV"
    [ "$CODE" = 429 ] && [ "$LS" != upstream_provider_shared_pool ] && stop "429 with limit_source=$LS at $OUT" 3
    [ "$U" -gt $((U0 + OK[qwen] + OK[gemma])) ] && stop "counter moved: used=$U start=$U0 ok=$((OK[qwen] + OK[gemma]))" 3
    sleep 1
  done
  [ "${OK[qwen]}" -ge "$MAX_OK" ] && [ "${OK[gemma]}" -ge "$MAX_OK" ] && stop "both models reached $MAX_OK successes"
  [ "$r" -lt "$MAX_ROUNDS" ] && sleep "$ROUND_S"
done
stop "max rounds reached"
