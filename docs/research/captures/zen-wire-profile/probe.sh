#!/usr/bin/env bash
# Usage: probe.sh NN model probe body.json [extra curl args...]
# Enforces: <=24 live requests, >=30 s spacing, hard stop after any 429.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
LOG=$D/requests.log
URL=${URL:-https://opencode.ai/zen/v1/chat/completions}
NN=$1; MODEL=$2; PROBE=$3; BODY=$4; shift 4
[ -f "$D/STOP_429" ] && { echo "REFUSED: a 429 was recorded"; exit 3; }
N=$( [ -f "$LOG" ] && wc -l < "$LOG" || echo 0 )
[ "$N" -ge 24 ] && { echo "REFUSED: budget exhausted ($N)"; exit 3; }
if [ -f "$LOG" ]; then
  LAST=$(tail -1 "$LOG" | cut -d' ' -f2)
  NOW=$(date +%s); WAIT=$(( LAST + 45 - NOW ))
  [ "$WAIT" -gt 0 ] && { echo "waiting ${WAIT}s"; sleep "$WAIT"; }
fi
OUT=$D/$NN-$MODEL-$PROBE.txt
H=$(mktemp); B=$(mktemp)
TS=$(date +%s)
echo "$((N+1)) $TS $(date -u +%Y-%m-%dT%H:%M:%SZ) $NN $MODEL $PROBE" >> "$LOG"
curl -sS -N --raw -D "$H" -o "$B" -w '%{http_code} %{time_starttransfer} %{time_total}' \
  $( [ "$BODY" = "-" ] || echo "-H Content-Type:application/json --data-binary @$BODY" ) "$@" "$URL" > "$B.meta" 2>&1
RC=$?
{
  echo "# request $((N+1)) at $(date -u -d @$TS +%Y-%m-%dT%H:%M:%SZ) curl_rc=$RC meta(http ttfb total)=$(cat $B.meta)"
  echo "# POST $URL extra_args: $*"
  echo "# request body:"; [ "$BODY" = "-" ] && echo "(none, GET)" || cat "$BODY"; echo
  echo "# ---- response headers ----"; cat "$H"
  echo "# ---- response body (raw) ----"; cat "$B"
} > "$OUT"
cp "$B" "$OUT.body"
CODE=$(head -1 "$H" | awk '{print $2}')
[ "$CODE" = "429" ] && { touch "$D/STOP_429"; echo "!!! 429 recorded"; }
echo "saved $OUT (req #$((N+1)), status $CODE, rc $RC, meta $(cat $B.meta))"
rm -f "$H" "$B" "$B.meta"
