#!/usr/bin/env bash
# Regenerates every capture behind docs/research/openrouter-wire-profile.md.
# Usage: bash docs/research/captures/openrouter-wire-profile/capture.sh
# Spends up to 17 free-model chat completions of the account's 50/day.
# Guards: <=24 completions (requests.log), >=5 s between completions, hard stop on any 429.
# The key comes from OPENROUTER_API_KEY or the Windows user env var; it is passed to
# curl on stdin (-H @-), never on the command line and never written to disk.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
BASE=https://openrouter.ai/api/v1
LOG=$D/requests.log
K=${OPENROUTER_API_KEY:-$(powershell.exe -NoProfile -Command '[Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY","User")' | tr -d '\r\n')}
[ -n "$K" ] || { echo "no OPENROUTER_API_KEY"; exit 2; }
PYTHONUTF8=1 python make_requests.py
mkdir -p meta

auth() { printf 'Authorization: Bearer %s\n' "$K"; }

# GET authenticated: /key (label dropped), /models/user, /generation. Not completions.
aget() { # name path
  local H B; H=$(mktemp); B=$(mktemp)
  auth | curl -sS -H @- -H 'Accept-Encoding: identity' -D "$H" -o "$B" "$BASE$2"
  { echo "# GET $BASE$2 at $(date -u +%Y-%m-%dT%H:%M:%SZ) (Authorization sent, not recorded)"
    echo "# ---- response headers ----"; cat "$H"
    echo "# ---- response body ----"
    PYTHONUTF8=1 python -c "
import json,sys
t=open(sys.argv[1],encoding='utf-8').read()
try:
  d=json.loads(t)
  if isinstance(d.get('data'),dict): d['data'].pop('label',None)
  print(json.dumps(d,indent=1))
except Exception: print(t)" "$B"
  } > "meta/$1.txt"
  rm -f "$H" "$B"; echo "saved meta/$1.txt"
}

probe() { # NN name body.json [extra curl args...]
  local NN=$1 NAME=$2 BODY=$3; shift 3
  [ -f "$D/STOP_429" ] && { echo "REFUSED: a 429 was recorded"; return 3; }
  local N; N=$( [ -f "$LOG" ] && wc -l < "$LOG" || echo 0 )
  [ "$N" -ge 24 ] && { echo "REFUSED: budget exhausted ($N)"; return 3; }
  if [ -f "$D/.last_end" ]; then
    local W=$(( $(cat "$D/.last_end") + 6 - $(date +%s) ))
    [ "$W" -gt 0 ] && sleep "$W"
  fi
  local OUT=$D/$NN-$NAME.txt H B TS
  H=$(mktemp); B=$(mktemp); TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$((N+1)) $TS $NN $NAME" >> "$LOG"
  auth | curl -sS -N --raw --max-time 240 -H @- -H 'Content-Type: application/json' \
    -H 'Accept-Encoding: identity' --data-binary @"$BODY" -D "$H" -o "$B" \
    -w '%{http_code} ttfb=%{time_starttransfer} total=%{time_total}' "$@" \
    "$BASE/chat/completions" > "$B.meta" 2>&1
  local RC=$?
  date +%s > "$D/.last_end"
  { echo "# completion $((N+1)) sent $TS curl_rc=$RC meta=$(cat "$B.meta")"
    echo "# POST $BASE/chat/completions"
    echo "# request headers: Authorization (not recorded), Content-Type: application/json, Accept-Encoding: identity, curl default User-Agent"
    echo "# request body ($BODY):"; cat "$BODY"; echo
    echo "# ---- response headers ----"; cat "$H"
    echo "# ---- response body (raw bytes follow) ----"; cat "$B"
  } > "$OUT"
  cp "$B" "$OUT.body"
  local CODE; CODE=$(grep -m1 '^HTTP' "$H" | awk '{print $2}')
  [ "$CODE" = "429" ] && { touch "$D/STOP_429"; echo "!!! 429 at $NN-$NAME"; }
  echo "saved $OUT (completion #$((N+1)), status $CODE, rc $RC, $(cat "$B.meta"))"
  rm -f "$H" "$B" "$B.meta"
}

rm -f "$LOG" "$D/STOP_429" "$D/.last_end"

# Item 12: does /key or /models/user move the counter?
aget key-0-before-anything /key
aget models-user /models/user
aget key-1-after-models-user /key

# Items 1-9, 11 per model.
n=1
# qwen first: gemma's Google AI Studio pool 429'd twice on 2026-09-25 and would hide qwen.
for m in qwen gemma; do
  for f in requests/$m-p*.json; do
    name=$(basename "$f" .json)
    probe "$(printf %02d $n)" "$name" "$f" || break 2
    n=$((n+1))
  done
done
probe "$(printf %02d $n)" unknown-model requests/unknown-model.json

sleep 10
aget key-2-after-completions /key

# Item 11: generation lookup for the first completion of each model (not a completion).
# The id comes from the X-Generation-Id response header, which is present even on a 429.
for f in [0-9][0-9]-*-p1-pi-stream-usage.txt; do
  [ -f "$f" ] || continue
  id=$(grep -m1 -i '^X-Generation-Id:' "$f" | awk '{print $2}' | tr -d '\r')
  [ -n "$id" ] && aget "generation-${f%%-p1*}" "/generation?id=$id"
done
sleep 5
aget key-3-after-generation-lookups /key

# /models/user is ~750 KB; keep headers, count, :free ids and the two probed entries.
PYTHONUTF8=1 python - <<'EOF'
import json
p = 'meta/models-user.txt'
head, body = open(p, encoding='utf-8').read().split('# ---- response body ----\n', 1)
d = json.loads(body)['data']
keep = [m for m in d if m['id'] in ('google/gemma-4-31b-it:free', 'qwen/qwen3.8-27b:free')]
free = [m['id'] for m in d if m['id'].endswith(':free')]
open(p, 'w', encoding='utf-8', newline='\n').write(
    head + '# ---- response body (extract: model count, :free ids, the two probed entries; full list not kept) ----\n'
    + json.dumps({'count': len(d), 'free_ids': free, 'entries': keep}, indent=1) + '\n')
EOF

# Item 10: Accept-Encoding on an unauthenticated catalogue GET (not a completion).
EP="$BASE/models/google/gemma-4-31b-it:free/endpoints"
curl -sS -D meta/ae-identity.headers.txt -o meta/ae-identity.body -H 'Accept-Encoding: identity' "$EP"
curl -sS -D meta/ae-offered.headers.txt -o meta/ae-offered.body -H 'Accept-Encoding: gzip, deflate, br' "$EP"

PYTHONUTF8=1 python summarize.py > meta/summary.md
echo "done; completions sent: $(wc -l < "$LOG")"
