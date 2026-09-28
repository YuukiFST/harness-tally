#!/usr/bin/env bash
# Regenerates every capture cited by docs/research/shared-pool-bypass.md (#42).
# Unauthenticated GETs of docs, terms and catalogue pages only: no API key, no completion.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p docs catalogue

f() { curl -sSL -A "Mozilla/5.0" -H "Accept-Encoding: identity" -D "$1.headers" -o "$1" "$2"; }

# OpenRouter docs and pricing
f docs/or-byok.md https://openrouter.ai/docs/guides/overview/auth/byok.md
f docs/or-use-cases-byok.md https://openrouter.ai/docs/use-cases/byok.md
f docs/or-provider-logging.md https://openrouter.ai/docs/guides/privacy/provider-logging.md
f docs/or-data-collection.md https://openrouter.ai/docs/guides/privacy/data-collection.md
f docs/or-zdr.md https://openrouter.ai/docs/guides/features/zdr.md
f docs/or-limits.md https://openrouter.ai/docs/api/reference/limits.md
f docs/or-free-variant.md https://openrouter.ai/docs/guides/routing/model-variants/free.md
f docs/or-provider-selection.md https://openrouter.ai/docs/guides/routing/provider-selection.md
f docs/or-faq.md https://openrouter.ai/docs/faq.md
f docs/or-pricing.html https://openrouter.ai/pricing

# OpenRouter catalogue
f catalogue/endpoints-qwen3.8-27b-free.json https://openrouter.ai/api/v1/models/qwen/qwen3.8-27b:free/endpoints
f catalogue/endpoints-qwen3.8-27b.json https://openrouter.ai/api/v1/models/qwen/qwen3.8-27b/endpoints
f catalogue/endpoints-gemma-4-31b-it-free.json https://openrouter.ai/api/v1/models/google/gemma-4-31b-it:free/endpoints
f catalogue/endpoints-gemma-4-31b-it.json https://openrouter.ai/api/v1/models/google/gemma-4-31b-it/endpoints
f catalogue/providers.json https://openrouter.ai/api/v1/providers
f catalogue/all-providers.json https://openrouter.ai/api/frontend/v1/all-providers
f catalogue/models.json https://openrouter.ai/api/v1/models

# Google Gemini API
f docs/gemini-terms.html https://ai.google.dev/gemini-api/terms
f docs/gemini-rate-limits.md https://ai.google.dev/gemini-api/docs/rate-limits.md.txt
f docs/gemini-pricing.md https://ai.google.dev/gemini-api/docs/pricing.md.txt
f docs/gemini-billing.md https://ai.google.dev/gemini-api/docs/billing.md.txt
f docs/gemini-api-key.md https://ai.google.dev/gemini-api/docs/api-key.md.txt
f docs/gemini-gemma.md https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api.md.txt

# Modular (ModelRun)
f docs/modular-pricing.html https://www.modular.com/pricing
f docs/modular-terms.html https://www.modular.com/legal/terms
f docs/modular-privacy.html https://www.modular.com/legal/privacy
f docs/modular-models.html https://www.modular.com/models
f docs/modular-docs-llms.txt https://docs.modular.com/llms.txt
f docs/modular-quickstart.md https://docs.modular.com/quickstart.md
f docs/modular-rate-limits.md https://docs.modular.com/administration/rate-limits.md
f docs/modular-models.md https://docs.modular.com/models.md
f docs/modular-billing.md https://docs.modular.com/administration/billing.md

# Other hosts of the same weights
f docs/groq-your-data.md https://console.groq.com/docs/your-data.md
f docs/groq-rate-limits.md https://console.groq.com/docs/rate-limits.md
f docs/groq-qwen.md https://console.groq.com/docs/model/qwen/qwen3.8-27b.md
f docs/groq-services-terms.html https://groq.com/terms-of-use
f docs/groq-services-agreement.md https://console.groq.com/docs/legal/services-agreement.md
f docs/cf-workers-ai-privacy.md https://developers.cloudflare.com/workers-ai/platform/privacy/index.md
f docs/cf-workers-ai-pricing.md https://developers.cloudflare.com/workers-ai/platform/pricing/index.md
f docs/cf-model-qwen3.8-27b.md https://developers.cloudflare.com/workers-ai/models/qwen3.8-27b/index.md
f docs/cf-errors.md https://developers.cloudflare.com/workers-ai/platform/errors/index.md
f docs/cf-limits.md https://developers.cloudflare.com/workers-ai/platform/limits/index.md
f docs/cf-workers-pricing.md https://developers.cloudflare.com/workers/platform/pricing/index.md
f docs/sambanova-rate-limits.md https://docs.sambanova.ai/docs/en/models/rate-limits.md

# Plain-text extracts of HTML pages (the .txt files cited by line number)
python - <<'EOF'
import html, re
for f in ["docs/or-pricing.html", "docs/gemini-terms.html", "docs/modular-pricing.html",
          "docs/modular-terms.html", "docs/modular-privacy.html", "docs/groq-services-terms.html"]:
    t = open(f, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<(h\d)[^>]*>", "\n## ", t)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    open(f.rsplit(".", 1)[0] + ".txt", "w", encoding="utf-8").write(t)
# OpenRouter pricing FAQ lives in JSON-LD
import json
t = open("docs/or-pricing.html", encoding="utf-8").read()
out = []
for s in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', t, flags=re.S):
    try:
        d = json.loads(s)
    except ValueError:
        continue
    for q in d.get("mainEntity", []) if isinstance(d, dict) else []:
        out.append("Q: " + q["name"] + "\nA: " + q["acceptedAnswer"]["text"] + "\n")
open("docs/or-pricing-faq.txt", "w", encoding="utf-8").write("\n".join(out))
EOF
