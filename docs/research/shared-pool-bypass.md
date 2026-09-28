# Is there a $0 path around the free models' shared-pool 429?

Ticket: [#42](https://github.com/YuukiFST/harness-tally/issues/42), part of [#1](https://github.com/YuukiFST/harness-tally/issues/1).
Builds on: `free-openrouter-pair.md` (#27), `openrouter-wire-profile.md` (#26), `zero-cost-route.md` (#32), `nvidia-trial-terms.md` (#37/#39).
Retrieval date for every web claim: **2026-09-28** (server `Date` headers 10:50Z to 11:00Z, one `.headers` file next to each capture).
Question: can a request for `qwen/qwen3.8-27b:free` (ModelRun `modelrun/fp4`) or `google/gemma-4-31b-it:free` (Google AI Studio), or the same weights, avoid the upstream 429 with `limit_source: "upstream_provider_shared_pool"` at no cost, while keeping inputs out of model training?

## Headline

**No candidate clears all three bars (no money, no training, no shared-pool dependence) for both models.**

1. **OpenRouter BYOK is not a $0 exit for this account.** The pricing page lists BYOK as "No" on the Free plan, and the account reports `is_free_tier: true`. For qwen it is impossible anyway: ModelRun has `byokEnabled: false`. For gemma, a personal Google key would carry Google's unpaid terms (trains), and OpenRouter's training filter would not catch it.
2. **A personal Gemini API key for gemma trains unless paid.** Google's unpaid quota "uses the content you submit ... to provide, improve, and develop Google products", with human review. Becoming a Paid Service requires linking billing and prepaying at least $5.
3. **ModelRun (Modular) does not sell qwen3.8-27b directly.** It sells gemma-4-31b-it on a shared endpoint, paid from one-time free credits of unpublished size, under terms with no explicit no-training promise.
4. **OpenRouter has no second free endpoint** for either model, and no other `:free` id with the same weights.

The one $0, no-training route that avoids both OpenRouter pools is **Cloudflare Workers AI serving `@cf/qwen/qwen3.8-27b` directly** (§5), with a small daily allowance (10,000 neurons, about $0.11 of list price) and its own capacity 429.
It covers qwen only, leaves OpenRouter, and needs the owner's approval as a new host.

No chat completion was sent. All access was unauthenticated GETs of docs, terms and catalogue pages (about 55 requests). No API key was read. The #41 sampler was left running untouched.

## Method

- Docs and terms fetched with `curl -sSL -A "Mozilla/5.0" -H "Accept-Encoding: identity"`, Markdown twins where the site serves them, into `captures/shared-pool-bypass/docs/`.
  HTML pages were flattened to `.txt` for line citations; the OpenRouter pricing FAQ was taken from the page's JSON-LD (`or-pricing-faq.txt`).
- Catalogue: `GET /api/v1/models`, `/api/v1/models/<id>/endpoints` for the two `:free` ids and their paid twins, `/api/v1/providers`, and `/api/frontend/v1/all-providers` (the source OpenRouter's own Provider Logging page reads for its data-policy table, `or-provider-logging.md:31`), into `captures/shared-pool-bypass/catalogue/`.
- One command regenerates every capture: `bash docs/research/captures/shared-pool-bypass/fetch.sh`.
- Account facts come from the key-free `/key` capture already on disk: `captures/openrouter-wire-profile/run-20260928T1047Z/meta/key-0-before-anything.txt`.

## 1. OpenRouter BYOK

### What BYOK does

- A BYOK key replaces OpenRouter's credential for the upstream call: "When you use OpenRouter credits, your rate limits for each provider are managed by OpenRouter. Using provider keys enables direct control over rate limits and costs via your provider account" (`docs/or-byok.md:20-23`).
- By default a failing key falls back to OpenRouter's shared capacity; the "Never use shared capacity" settings stop that (`or-byok.md:53-86`).
- BYOK requests are not counted by the 50/day free-model counter: "Accounts and endpoints exempt from free-model limits, and BYOK requests, are not gated by it" (`docs/or-limits.md`, "Free usage limits" paragraph).
- The observed gemma 429 itself says: "add your own key to accumulate your rate limits" (`openrouter-wire-profile.md`, probe 01, `is_byok: false`).
  So BYOK would move the request off the Google AI Studio shared pool and onto the key owner's own quota.

### Fee

- Docs: "5% of what the same model/provider would cost normally on OpenRouter ... deducted from your OpenRouter credits", with a plan-dependent free allowance "measured by list-price inference cost", $25,000/month on Pay-as-you-go (`or-byok.md:29-36`; same in `or-faq.md:86-98`).
- Pricing page plan table, "BYOK Limits" row: **Free: "No"** (rendered with the "not included" dash icon), Standard and Business "$25,000 of list price inference / month with no fees, 5% fee after", Enterprise "$200,000/month" (`docs/or-pricing.txt:126-128`, `:336-345`; raw cell in `or-pricing.html`).
- Standard and Business mean "you buy credits" (`or-pricing-faq.txt:8`).
- This account: `is_free_tier: true`, key `limit: 0`, `limit_remaining: 0`, `byok_usage: 0` (`key-0-before-anything.txt`).
- **Reading:** on the Free plan BYOK is listed as not included. Whether the Free plan blocks adding a key outright, or allows it and charges the 5% from a zero balance, is **UNVERIFIED** (the setting page needs a login). Either way the documented fee-free allowance belongs to plans reached by buying credits, which the product owner ruled out.

### Does BYOK apply to `:free` ids?

- No doc says so directly.
  `:free` is "its own entry in the models API ... with its own pricing, context length, and endpoints" (`docs/or-free-variant.md`).
  "A BYOK key changes the credential for the upstream request. It does not change which endpoints you can route to" (`or-byok.md:155`).
- The only evidence it does is the 429 text above, which offers BYOK as the remedy on a `:free` request. **UNVERIFIED** in the docs.
- **qwen: not applicable.** ModelRun, the only endpoint of `qwen/qwen3.8-27b:free`, has `"byokEnabled": false` (`catalogue/all-providers.json`, slug `modelrun`).
- **gemma:** Google AI Studio has `"byokEnabled": true` and OpenRouter records its policy as `training: false`, `retainsPrompts: true`, `retentionDays: 55` (`all-providers.json`, slug `google-ai-studio`).
  That record describes OpenRouter's own contract with Google, not a personal key.

### The training trap

- "Training (`data_collection`) restrictions still follow the policy that OpenRouter tracks for the endpoint" (`or-byok.md:183`), and a user's key declaration can only change retention, not training (same line).
- So with the account's "no training" setting on, OpenRouter would still route through a personal **unpaid** Google key, because the endpoint it tracks is `training: false`, while Google's Unpaid Services terms (§2) would govern that traffic.
  **The account-level training switch does not protect a BYOK request.**

**Verdict: not applicable for qwen (ModelRun has no BYOK); for gemma, costs money (BYOK not on the Free plan) and, with a free Google key, trains.**

## 2. Personal Gemini API key for `gemma-4-31b-it`

- **Data use, unpaid quota** ([Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms), "Unpaid Services" → "How Google Uses Your Data", page "Last updated 2026-04-28"; `docs/gemini-terms.txt:276-296`):
  "When you use Unpaid Services, including, for example, Google AI Studio and the unpaid quota on Gemini API, Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products and services and machine learning technologies".
  "human reviewers may read, annotate, and process your API input and output ... Do not submit sensitive, confidential, or personal information to the Unpaid Services."
- **Exception:** "If you're in the European Economic Area, Switzerland, or the United Kingdom", the Paid Services data terms apply to the unpaid quota too (`gemini-terms.txt:309-317`). Whether the account holder qualifies is not something this research can check.
- **Paid Services:** "Your access to Gemini API is a 'Paid Service' only when accessing the API through a Cloud Project associated with an active billing account" (`:328-329`); then Google "doesn't use your prompts ... or responses to improve our products" but "logs prompts and responses for a limited period of time" for abuse detection (`:336-345`).
- **Price of Gemma 4:** Free Tier "Free of charge", Paid Tier "Not available", "Used to improve our products: Yes / No" (`docs/gemini-pricing.md:1291-1304`).
- **Getting to Paid:** "Upgrading from the Free Tier to the Paid Tier means linking a billing account and prepaying to add a minimum of $5" (`docs/gemini-billing.md:43-44`, step 5 at `:59`).
  Step 5 also says some accounts are instead offered or assigned Postpay (`:60-61`). A Postpay project that calls only Gemma (no paid price exists) might cost $0 while counting as a Paid Service; that combination is **UNVERIFIED**, needs a card on file, and the plan is Google's choice, not the user's.
- **Rate limits:** per project, RPD reset at midnight Pacific; the per-model numbers are dashboard-only ("View your active rate limits in AI Studio", `docs/gemini-rate-limits.md:1-21`). Free-tier RPM/RPD/TPM for gemma-4-31b-it: **UNVERIFIED** (unchanged since `zero-cost-route.md` §2).
- A personal key does leave OpenRouter's shared Google pool: limits "are applied per project, not per API key" (`gemini-rate-limits.md:20`).

**Verdict: trains or retains (unpaid quota); costs money (paid tier, $5 minimum prepay).**

## 3. Personal ModelRun (Modular) key, or another qwen3.8-27b host

### ModelRun / Modular Cloud

- ModelRun is "ModelRun [by Modular]", base URL `https://api.modular.com/v1`, `byokEnabled: false` (`all-providers.json`).
- **qwen3.8-27b is not sold directly.** It is absent from the Modular Cloud model table (`docs/modular-models.md:25-60`) and the hosted price list, whose Qwen rows are Qwen 3 235B, 3.5 9B, 3.6 Plus, 3.7-Max (`docs/modular-pricing.txt:131-215`).
  The OpenRouter qwen endpoint looks like a deployment made for OpenRouter only; **UNVERIFIED**.
- **gemma-4-31b-it is sold** on a shared endpoint, $0.25 in / $0.65 out per 1M (`modular-pricing.txt:143-146`; `modular-models.md:35`).
- **Free tier:** "New Modular Cloud accounts include free credits"; at zero balance requests "return a 401" (`docs/modular-billing.md:33-35`, `:52-53`). The credit amount is not published (**UNVERIFIED**) and nothing says it renews. Sign-up asks for a "work email" (`docs/modular-quickstart.md:18`).
- **It is also a shared pool:** "For shared endpoints, the model's rate limit is shared by every organization using that endpoint"; gemma-4-31b-it's is 2,160,000 TPM; the Tier 1 org limit is 60 RPM / 600,000 TPM (`docs/modular-rate-limits.md:30-35`, `:49-58`).
- **Data terms** ([Modular Terms](https://www.modular.com/legal/terms)): the user grants a licence "as may be necessary for Modular to provide the Modular Platform, and a non-exclusive, perpetual, irrevocable ... license to ... use ... your User Generated Content incorporated within the Derivative Data" (`docs/modular-terms.txt:278`); Derivative Data is aggregated/anonymised data "related to or derived from Users" that "Modular may use and disclose ... for any lawful purpose" (`:133-134`, `:234-235`).
  No clause found that forbids training on inputs; whether Modular trains on them is **UNVERIFIED**.

**Verdict: not applicable for qwen (not sold, no BYOK). For gemma: $0 only until an unpublished one-time credit runs out, still a cross-customer shared limit, training terms unclear.**

### Other hosts of qwen3.8-27b with a free tier

| Host | Free allowance | Training | Fit | Source |
|---|---|---|---|---|
| **Cloudflare Workers AI** `@cf/qwen/qwen3.8-27b` | 10,000 neurons/day on Workers Free, the default plan; model not in the paid-only list | "Cloudflare does not use your Customer Content to (1) train any AI models ... or (2) improve any Cloudflare or third-party services" | See §5 | `cf-workers-ai-pricing.md:21-36`, `cf-workers-pricing.md:17`, `cf-workers-ai-privacy.md:198` |
| Groq `qwen/qwen3.8-27b` | 30 RPM, 1K RPD, **8K TPM, 200K TPD** | Model is "Preview", a Beta Service, and "Beta Services are not Cloud Services under this Agreement"; the DPA does not apply to it. §4.2 says "Groq is not permitted to use Inputs or Outputs for training", but whether §4.2 covers Beta Services is **UNVERIFIED** | Does not fit: `zero-cost-route.md` §2 showed 200K TPD is spent by about 30 opencode requests | `groq-rate-limits.md:54`, `groq-qwen.md:9`, `groq-services-agreement.md:95`, `:105`, `groq-services-terms.txt:114` |
| 15 paid hosts on OpenRouter | none ($0.05–0.45 in per 1M) | all `training: false` in OpenRouter's record | Cost money | `catalogue/endpoints-qwen3.8-27b.json` |

For gemma-4-31b-it, the other free hosts are already excluded: SambaNova free tier, 20 RPM / 20 RPD (`docs/sambanova-rate-limits.md:86`), below OpenRouter's 50/day; NVIDIA build, whose terms let NVIDIA train (`nvidia-trial-terms.md`, rejected in #39).
Cloudflare serves `gemma-4-26b-a4b-it`, not the 31B (`zero-cost-route.md` §2).

## 4. Another free endpoint on OpenRouter

- `qwen/qwen3.8-27b:free`: **one** endpoint, ModelRun `modelrun/fp4`, price 0 (`catalogue/endpoints-qwen3.8-27b-free.json`).
- `google/gemma-4-31b-it:free`: **one** endpoint, Google AI Studio, price 0 (`catalogue/endpoints-gemma-4-31b-it-free.json`).
- The paid twins have 16 and 15 endpoints, none at price 0 (`endpoints-qwen3.8-27b.json`, `endpoints-gemma-4-31b-it.json`).
- `/api/v1/models` lists 17 `:free` ids today (18 on 2026-09-25, `free-openrouter-pair.md` §2). The only other ids with these names are `google/gemma-4-26b-a4b-it:free`, which is different weights, and paid Qwen 3.8 variants (`catalogue/models.json`).
- Provider routing (`provider.order`, `allow_fallbacks`) can only pick among a model's endpoints; with one endpoint there is nothing to route to, which `free-openrouter-pair.md` §2 already noted.

**Verdict: not available.**

## 5. The one partial exit: Cloudflare Workers AI for qwen

- **Model:** `@cf/qwen/qwen3.8-27b`, 262,144-token context, function calling, reasoning `low`/`medium`/`xhigh` with **`xhigh` the default**, $0.45 in / $3.20 out / $0.05 cached-in per 1M (`docs/cf-model-qwen3.8-27b.md:20-38`); request schema has `tools` and `tool_choice` (`:239-245`).
- **Cost:** "10,000 Neurons per day at no charge"; beyond that, Workers Free fails with an error instead of billing ("N/A - Upgrade to Workers Paid") (`cf-workers-ai-pricing.md:23-31`). Error `3036`, HTTP 429: "You have used up your daily free allocation" (`docs/cf-errors.md:36`).
- **Budget:** at $0.011 per 1,000 neurons (`cf-workers-ai-pricing.md:21`), 10,000 neurons are $0.11 of list price per day. That is about 244K uncached input tokens (40,909 neurons per M, `zero-cost-route` capture `cloudflare-pricing.md:79`) or about 34K output tokens (290,909 per M).
  With reasoning at `xhigh` by default and opencode's ~6.7K-token first request (`zero-cost-route.md` §1.3), that is probably one short unit-run a day at most. Whether cached input is billed at the $0.05 rate automatically is **UNVERIFIED**.
- **Pool:** its own daily allowance, not OpenRouter's or ModelRun's. It still has "Out of capacity" `3040`, HTTP 429, "Capacity temporarily exceeded" (`cf-errors.md:37`), so a capacity 429 is not eliminated, only moved to another host. Text generation is 300 RPM (`docs/cf-limits.md:58-60`).
- **Data:** no training and no service improvement without explicit consent; content "may be stored by Cloudflare if you specifically use a storage service" (`cf-workers-ai-privacy.md:192-199`).
  OpenRouter's record for Cloudflare says `retainsPrompts: true` with no retention period (`all-providers.json`, slug `cloudflare`); the two sources disagree, which is **UNVERIFIED** either way.
- **Card at sign-up:** "By default, users have access to the Workers Free plan" (`cf-workers-pricing.md:17`); whether a card or phone is asked: **UNVERIFIED**.
- **Via OpenRouter instead of direct:** Cloudflare is an endpoint of paid `qwen/qwen3.8-27b` with `byokEnabled: true`, but that runs into the Free-plan BYOK "No" of §1.

## Verdicts

| # | Candidate | Verdict | Decisive citation |
|---|---|---|---|
| 1 | OpenRouter BYOK | **Not applicable** for qwen; **costs money** for gemma (and trains with a free Google key) | `all-providers.json` modelrun `byokEnabled: false`; `or-pricing.txt:126-128` Free plan BYOK "No"; `or-byok.md:183` |
| 2 | Personal Gemini API key, gemma | **Trains** (unpaid) / **costs money** (paid, $5 prepay) | `gemini-terms.txt:283-296`; `gemini-billing.md:43-44` |
| 3 | ModelRun direct | **Not applicable** for qwen (not sold); gemma: one-time credits, shared limit, training **UNVERIFIED** | `modular-models.md:25-60`; `modular-billing.md:33-35`; `modular-terms.txt:278` |
| 3b | Cloudflare Workers AI, qwen | **Viable at $0 with no training**, qwen only, about $0.11/day of list-price inference, own capacity 429 | `cf-workers-ai-pricing.md:23`; `cf-workers-ai-privacy.md:198`; `cf-errors.md:37` |
| 3c | Groq, qwen | Does not fit (200K TPD); training for a Preview model **UNVERIFIED** | `zero-cost-route.md` §2; `groq-services-agreement.md:95` |
| 4 | Second free OpenRouter endpoint | **Not available** | `endpoints-*-free.json`, one endpoint each |

## Consequences

1. **For gemma-4-31b-it there is no $0, no-training exit.** Every route off the Google AI Studio shared pool either trains (personal unpaid key, NVIDIA), costs money (Gemini paid tier, BYOK above Free, 15 paid hosts), or is another shared pool with finite credits (Modular). If #41 shows the pool is too often closed, the choice goes to the product owner as a Money ticket.
2. **For qwen3.8-27b the only $0, no-training exit is Cloudflare direct.** It leaves OpenRouter, so the #26 wire profile would not apply and a Cloudflare profile would be needed. It sends Finn to a host outside the approved route; the terms say no training, but that is an owner decision. The ~$0.11/day allowance likely caps it at about one unit-run a day, fewer with `xhigh` reasoning.
3. **Never add a personal Google key as BYOK while relying on the account's training switch.** OpenRouter filters training by the endpoint it tracks (`training: false`), not by the key's own terms (`or-byok.md:183`).
4. **Conflict to record for #41:** the pricing FAQ says "Failed attempts count toward that daily cap" (`or-pricing-faq.txt:35`), while three pool 429s left `free_model_daily_requests.used` at 0 (`openrouter-wire-profile.md` probe K; #41 context). The sampler's guard on the counter already covers this; the doc wording and the observed behaviour disagree.
5. **The free catalogue shrank from 18 to 17 `:free` ids in three days**, a reminder that `:free` listings are withdrawn without notice (`free-openrouter-pair.md` §3).

## UNVERIFIED

1. Whether BYOK applies to a `:free` model id at all (only the 429 text suggests it).
2. Whether a Free-plan OpenRouter account can add a BYOK key, and what it is charged if it can.
3. Gemini API free-tier RPM/RPD/TPM for gemma-4-31b-it (dashboard-only).
4. Whether a Gemini Postpay billing project using only Gemma costs $0 while counting as a Paid Service, and who is offered Postpay.
5. Modular: size and renewal of the new-account credits; whether inputs are used for training.
6. Groq: whether the §4.2 no-training sentence covers Preview (Beta) models.
7. Cloudflare: card or phone at sign-up; automatic cached-input pricing; the retention disagreement with OpenRouter's record; `stream_options` and usage frames on its OpenAI-compatible endpoint.
