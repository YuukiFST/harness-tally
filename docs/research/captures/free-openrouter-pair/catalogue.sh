#!/usr/bin/env bash
# Regenerates the unauthenticated catalogue captures for free-openrouter-pair.md.
# GET /api/v1/models and /api/v1/models/{id}/endpoints are free and need no key.
# Usage: bash docs/research/captures/free-openrouter-pair/catalogue.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p meta endpoints
BASE=https://openrouter.ai/api/v1

curl -sS -D meta/models.headers.txt -o meta/models.json "$BASE/models"

# Every :free id, plus the id with :free stripped (the candidate paid twin).
# tr strips the CR that Windows python prints, which otherwise breaks the URL.
ids=$(PYTHONUTF8=1 python -c "
import json
for m in json.load(open('meta/models.json'))['data']:
    if m['id'].endswith(':free'):
        print(m['id']); print(m['id'][:-5])
" | tr -d '\r')
for id in $ids; do
  f="endpoints/$(echo "$id" | tr '/:' '__').json"
  curl -sS -o "$f" "$BASE/models/$id/endpoints"
  sleep 1
done

PYTHONUTF8=1 python summarize.py > meta/summary.md
