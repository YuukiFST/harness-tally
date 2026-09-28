# Do NVIDIA's API Trial Terms allow the benchmark?

Ticket: [#37](https://github.com/YuukiFST/harness-tally/issues/37).
Builds on: `zero-cost-route.md` §2.1 (NVIDIA build.nvidia.com as the $0 route).
Access date for every web claim: **2026-09-25** (server `Date` headers 14:40Z to 14:41Z, kept next to each capture; the trial-terms PDF came from a CDN cache stamped `Date: Thu, 24 Sep 2026 20:11:17 GMT`, `Last-Modified: Wed, 23 Sep 2026 16:02:11 GMT`).
Question: can the free endpoints at `https://integrate.api.nvidia.com/v1` be used for an automated benchmark of pi and opencode on `nvidia/nemotron-3-super-120b-a12b` and `google/gemma-4-31b-it` (84 to 120 agent sessions over several days, tens to hundreds of requests each), which sends a private product specification plus the code the agents write, and whose token counts are published?

## Headline

1. **Conditional yes.** The purpose fits.
   The trial terms allow "internal testing and evaluation purposes, not in production" (§1.4), and NVIDIA's NIM FAQ defines production as "any use of NIM for purposes other than development, testing, research or evaluation".
   None of the fetched documents forbids benchmarking or publishing benchmark results. The word "benchmark" does not appear in the trial terms, the developer terms, the Trustworthy AI terms, or either model license.
2. **The blocking clause is §2.6(a): you agree not to "include any confidential information" in User Content.**
   If the product specification is confidential (trade secret, under NDA, or owned by an employer or client who has not agreed), sending it breaks the terms.
   If the owner treats it as unpublished but not confidential and consents, the clause is not triggered. This repo does not say which case applies, so the user has to decide.
3. **Prompts and outputs may be used for training.** §3.3 says NVIDIA "will collect ... (iv) User Content and Generated Content to improve NVIDIA products and services, including AI models".
   That conflicts with §2.3 ("will not store or use User Content or Generated Content at the end of each API Service session"), and the terms do not settle the conflict. The terms give no retention period for the chat endpoints and no opt-out.
   Treat everything sent as disclosed to NVIDIA.
4. Automation is not forbidden in terms. §2.6(h) bans "any robot, spider, data scrapping or extraction tool". Read in context it targets scraping, but the wording is broad. No volume cap is published in the terms beyond "use limits defined by NVIDIA" (§1.1).
5. Publishing the agents' code (Generated Content) is less clear than publishing token counts. §4.2 says you "may not ... distribute or make available to others any portion of the API Service or Generated Content".
   Token counts are measurements, not Generated Content.

No authenticated request and no completion was sent. All access was unauthenticated GETs of public legal pages (10 requests).

## Method

- Existing captures from #32: `captures/zero-cost-route/docs/nvidia-build-super.{html,md}`, `nvidia-build-gemma4.html` (each model's "GOVERNING TERMS" line and the `rateLimits` copy), and `nvidia-nim-faq.html` (canonical `https://docs.api.nvidia.com/nim/docs/product`, `Date: Fri, 25 Sep 2026 14:30:36 GMT`).
- New captures in `captures/nvidia-trial-terms/`, fetched with `curl -sSL -A "Mozilla/5.0" -D <f>.headers -o <f> <url>`. Text twins (`.txt`) came from `pdftotext -layout` for the PDF and a small HTML-to-text pass for the pages. Line numbers below refer to the `.txt` files.

| Capture | URL |
|---|---|
| `api-trial-tos.pdf` / `.txt` | https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf (version footer "v. September 19, 2025", `.txt:446`) |
| `nemotron-open-model-license.*` | https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/ ("Last Modified: December 15, 2025") |
| `nvidia-open-model-license.*` | https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/ ("Last Modified: October 24, 2025") |
| `gemma4-license.*` | https://ai.google.dev/gemma/docs/gemma_4_license (301 to `/gemma/apache_2`, Apache License 2.0) |
| `gemma-terms.*`, `gemma-prohibited-use.*` | https://ai.google.dev/gemma/terms, https://ai.google.dev/gemma/prohibited_use_policy |
| `trustworthy-ai-terms.*` | https://www.nvidia.com/en-us/agreements/trustworthy-ai/terms/ ("Last Modified: June 27, 2024") |
| `nvidia-privacy-policy.*` | https://www.nvidia.com/en-us/about-nvidia/privacy-policy/ ("Effective date September 22, 2025") |
| `developer-terms.*` | https://developer.nvidia.com/legal/terms ("Last updated: August 20, 2026") |
| `product-specific-terms-ai.*` | https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-ai-products/ (checked; nothing specific to the API Catalog trial) |

To regenerate, re-run the `curl` above for each URL, then `pdftotext -layout api-trial-tos.pdf api-trial-tos.txt`.

## 0. Which documents govern

- Nemotron page: "The trial service is governed by the NVIDIA API Trial Terms of Service. Use of this model is governed by the NVIDIA Nemotron Open Model License." (`captures/zero-cost-route/docs/nvidia-build-super.md:59`).
- Gemma 4 page: "This trial service is governed by the NVIDIA API Trial Terms of Service. Use of this model is governed by the NVIDIA Open Model License Agreement. Additional Information: Apache License, Version 2.0." (embedded copy in `nvidia-build-gemma4.html`).
- The Gemma Terms of Use and the Gemma Prohibited Use Policy **do not apply to Gemma 4**. "The terms below apply to Gemma models listed in the Appendix at bottom of this page. For Gemma 4 terms, see the Gemma 4 license." (`gemma-terms.txt:234`). The appendix lists Gemma 1 through Gemma 3n and variants, not Gemma 4 (`:372-384`). The Gemma 4 license link redirects to the Apache 2.0 page.
- The Developer Terms of Use give way to product agreements: "where present, those Product Agreement(s) will govern your use of the Technology" (`developer-terms.txt:22`). The trial terms are that product agreement.
- Trial terms §9: "you are responsible for your compliance with third-party AI model licenses" (`api-trial-tos.txt:255-256`).

## 1. Permitted purposes

| Clause | Text | Bearing |
|---|---|---|
| Trial ToS §1.2 (`:26-27`) | "NVIDIA will provide you access to the API Service for limited trial purposes only and without use of the API Service or Generated Content in production." | Non-production use is permitted |
| Trial ToS §1.4 (`:49-51`) | "Unless you purchase a Subscription from NVIDIA or a Service Provider (as applicable), you may only use the API Service for internal testing and evaluation purposes, not in production." | Evaluation is explicitly allowed. "Internal" is the only word that could be read against a published write-up. It qualifies the *use*, not the publication of measurements |
| NIM FAQ (`nvidia-nim-faq.html`, docs.api.nvidia.com/nim/docs/product) | "Production use involves any use of NIM for purposes other than development, testing, research or evaluation such as conducting business transactions and any non-testing activity including activity serving real end-users." Also: "NIM access through the NVIDIA Developer Program is for prototyping, research, development and testing purposes only" | Research and evaluation are named as non-production. This is an FAQ, not the contract |
| Trial ToS §4.1 (`:173-174`) | "You will not use the API Service for any purpose other than as described in Section 1 above" | Ties purpose to §1.2/§1.4 |
| Trial ToS §4.2 (`:176-178`) | "Except as indicated in the Section 1.2 ('Trial Access Rights') above, you may not copy, sell, rent, sublicense, transfer or distribute or make available to others any portion of the API Service or Generated Content." | Publishing token counts is not publishing Generated Content. Publishing the agents' code or transcripts would be "make available to others ... Generated Content". §6.3 (`:229-234`) says "you own all Generated Content", which pulls the other way. The two are not reconciled |
| Trial ToS §4.12 (`:214-215`) | "You will not use (or allow others to use) the API Service including Generated Content to develop or improve products or services that compete with the API Service." | Benchmarking coding agents does not build a competing inference API |
| Trustworthy AI terms (`trustworthy-ai-terms.txt:632`) | Prohibits use "for any purpose in violation of applicable law or regulation, including but not limited to (a) illegal surveillance, (b) illegal collection or processing of biometric information ..., or (c) illegal harassment ..." | Not triggered |
| Nemotron Open Model License | "Works are commercially usable." "NVIDIA does not claim ownership to any outputs generated using the Works" (`nemotron-open-model-license.txt:633-635`) | No use restriction relevant here |
| NVIDIA Open Model License (Gemma page) | "NVIDIA claims no ownership rights in outputs. You are responsible for outputs and their subsequent uses." (`nvidia-open-model-license.txt:650`); guardrail-bypass clause (`:647`) | Not triggered by a normal agent loop |

**Benchmarking and publication.** No clause in any fetched document forbids benchmarking or publishing benchmark results, and none permits it by name. The ban-on-benchmark wording common in commercial licences ("you will not publish benchmark results without consent") is absent. Search: `grep -il benchmark captures/nvidia-trial-terms/*.txt` matches only site navigation, not any clause.

**Automated or scripted use.** Nothing permits it by name. §2.6(h) says User Content or Generated Content must not "use any robot, spider, data scrapping or extraction tool or other similar mechanism" (`:112`), and the Developer Terms ban "any data scraping or extraction tool such as a robot, spider, or other similar mechanism with NVIDIA servers" (`developer-terms.txt:61`). Both aim at scraping. An API used through an API key is scripted by nature, and the model pages publish OpenAPI specs and code samples for exactly that use. Reading §2.6(h) as a ban on programmatic API clients is **UNVERIFIED** either way; no NVIDIA statement addressing it was found.

## 2. Rate, volume and automation limits beyond the published rpm

- Trial ToS §1.1: "Subject to use limits defined by NVIDIA" (`:21`).
- §1.4: "The API Services are available for your limited use for a limited time. Your use of an API Service may be limited to a certain number of API access instances or by API access duration. NVIDIA may extend trial service credits ('Credits') ... NVIDIA will deduct Credits based on your usage" (`:41-45`). The OpenAPI specs still carry a 402 example "You have reached your limit of credits." (both model pages).
- §3.1: past "a certain number of sessions or designated period of time, in each case to be determined by NVIDIA", NVIDIA "will require certain personal information such as name and email address" (`:138-141`).
- §4.5 "misuse, disrupt, or exploit the API Service" and §4.9 availability (`:191-192`, `:205-206`). A benchmark that stays within the published limits does not obviously hit these, but neither clause defines a threshold.
- §4.6 "unsolicited automated bulk communication" (`:194`) is about spam and does not apply.
- The only numbers are site copy: "Up to 40 rpm", "10,000 requests per day", "Rate limits may vary by model and traffic from other users may cause throttling" (`zero-cost-route.md` §2). **No contractual number exists.** The trial length ("limited time") and any credit balance for these endpoints are **UNVERIFIED**.

## 3. Retention, logging, human review, training

| Clause | Text |
|---|---|
| §2.2 (`:62-68`) | You grant NVIDIA "a worldwide license ... to use, host, store, reproduce, modify, create derivative works ..., display and transmit such User Content and Generated Content during your API Service session solely to provide you with the API Service and as otherwise described in this Agreement" |
| §2.3 (`:70-71`) | "Except as stated below in Section 2.4 or unless expressly disclosed to you for an API Service, NVIDIA will not store or use User Content or Generated Content at the end of each API Service session." |
| §2.4 (`:73-78`) | For "certain API Services, such as the Fine Tuning API Service or as expressly disclosed in the NVIDIA API Catalog", NVIDIA "will store User Content for thirty (30) days ... except that NVIDIA may log and store User Content and Generated Content to monitor for security or to prevent fraud or abuse as stated in Section 3.3." |
| §2.7 (`:128-130`) | "NVIDIA may, but is not obligated to, block, monitor, scan or review communications or User Content or Generated Content transmitted through the API Service" |
| §3.3 (`:152-158`) | "NVIDIA will collect the following data, without identifying specific users, to operate and improve the API Services and other products and services: (i) session metrics ...; (ii) error logs and execution logs ...; (iii) your feedback ...; and (iv) User Content and Generated Content to improve NVIDIA products and services, including AI models. Your use of the API Services will be logged for security, fraud or abuse monitoring and shared with third party service providers for this purpose." |
| §2.6(a) (`:89-92`) | You agree not to "include any confidential information, controlled or sensitive data, including protected health information, personal data (unless expressly permitted by an API Service), ..." |
| §4.3 (`:180-186`) | No personal, financial, health or government data; NVIDIA "specifically disclaims, that NVIDIA servers are appropriate for processing of any data" |
| §1.3 (`:32-35`) | Pre-release services "may have reduced or different security, privacy, availability, and reliability standards" |
| §7 (`:239-240`) | Feedback "will not create any confidentiality obligation" |

What this means for the benchmark:

- **Training use: permitted to NVIDIA by §3.3(iv)**, stated "without identifying specific users". §2.3 says content is not stored or used after the session. The terms do not say how the two fit together.
  The safe reading is that prompts and outputs may be kept and used to improve models.
- **Logging: yes** (§3.3, for security, fraud and abuse, shared with third-party providers). **Human review: possible** (§2.7 "review").
- **Retention period** for chat completions on these two endpoints: **UNVERIFIED**. The only numbers (30 days input, 90 days output) are for Fine Tuning and services "expressly disclosed in the NVIDIA API Catalog". Neither model page contains such a disclosure; a search of both captured pages for storage or retention wording found none.
- **Opt-out** from training or logging: **none in the trial terms. UNVERIFIED** whether an account setting exists (it would need an authenticated look).
- The privacy policy covers personal data, not prompt content. Its only AI-training section covers "public images, audio-video, and survey data" and licensed datasets (`nvidia-privacy-policy.txt:883-892`). General retention is "as long as our engagement with you continues ... We erase customer and enterprise personal data if there has been no engagement with you for more than five years." (`:917`). It does not describe API prompts.
- Confidentiality: nothing in the trial terms promises NVIDIA will keep User Content confidential. §2.6(a) puts the burden on the user not to send confidential material.

## 4. Jurisdiction and where data is processed

- Trial ToS §14.5: "governed by the Federal Arbitration Act, in addition to the internal substantive laws of the State of Delaware and the United States" (`:382-386`). §14.2: binding JAMS arbitration "conducted in Santa Clara County, California"; fallback courts "in Santa Clara County, California" (`:335-358`). Class-action and jury waiver §14.3, with a 30-day written opt-out §14.4 (`:366-380`). Liability cap US$10 (§13.2, `:306-307`).
- Privacy policy, cross-border transfer: "NVIDIA is located in California, and in most cases we need to securely transfer and store your information in the United States", under Standard Contractual Clauses and the EU-U.S. Data Privacy Framework (`nvidia-privacy-policy.txt:914`). This is about personal data.
- **Where inference for these two endpoints actually runs (country, region, NVIDIA vs a third-party host): UNVERIFIED.** §1.4 mentions third-party "Service Providers" and §3.3 sharing with "third party service providers", but no region is named for these endpoints.
- §15.4 export and sanctions compliance (`:423-426`).

## 5. Termination, suspension and quota changes

- §8: "NVIDIA may at any time change, discontinue, or deprecate any part, or all, of the API Service ... the API Service may be temporarily unavailable, inaccessible, or slow" (`:244-247`).
- §11.2: rights end "automatically without notice" on non-compliance, and "Additionally, NVIDIA may at any time terminate the availability, or your use, of the API Service." (`:273-277`).
- §1.3: pre-release services may be abandoned "at any time without liability" (`:38-39`).
- §15.7: terms change "effective when published", and continued use counts as acceptance (`:439-444`).
- Developer Terms §15: "NVIDIA may suspend or terminate your access to specific Technology at any time at NVIDIA's sole discretion" (`developer-terms.txt:102`); §7 promotional offerings may be discontinued "at any time" (`:73`).
- No notice period, no quota guarantee, no SLA. For the benchmark this means a run spread over several days can lose the route or have its quota cut mid-matrix, and the terms give no remedy.

## 6. Verdict for the proposed use

| Element of the use | Verdict | Deciding clause |
|---|---|---|
| Evaluating two agents on two models, not serving users | Allowed | §1.2, §1.4; FAQ definition of production |
| Scripted agent sessions through the API | Allowed in practice, not named | §2.6(h) is about scraping; UNVERIFIED |
| 84 to 120 sessions over several days | Allowed if within NVIDIA's limits, which can change | §1.1, §1.4, §8, §11.2 |
| Publishing token counts and derived metrics | Not forbidden | No benchmark or publication clause exists |
| Publishing the agents' code or transcripts | Unclear | §4.2 vs §6.3 |
| Sending the private product specification | **Allowed only if it is not confidential** and you have the rights to it | §2.6(a), §2.2 "own or have the appropriate rights" |
| Expecting prompts to stay private | **No** | §3.3(iv), §2.7 |

## UNVERIFIED

1. Whether §2.6(h) ("robot ... or other similar mechanism") is meant to reach programmatic API clients. No NVIDIA statement found.
2. How §2.3 (not stored after session) and §3.3(iv) (content collected to improve models) fit together. No NVIDIA clarification found.
3. Retention period for chat-completion prompts and outputs on these two endpoints. No per-model disclosure found.
4. Any opt-out from training or logging. None in the terms; an account-level setting would need an authenticated check.
5. Region or host that serves `nvidia/nemotron-3-super-120b-a12b` and `google/gemma-4-31b-it`.
6. Trial length ("limited time") and whether a credit balance applies to these free endpoints.
7. Whether the product specification is confidential. That is a fact about the spec's owner, not about NVIDIA, and this repo does not record it.
