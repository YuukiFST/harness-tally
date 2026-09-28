> ## Documentation Index
> Fetch the complete documentation index at: https://inference-docs.cerebras.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate Limits

> Learn how rate limits are applied and measured.

<div className="compact-tables-page" style={{display: "none"}} />

Rate limits ensure fair usage and system stability by regulating how often users and applications can access our API within a specified timeframe. They help protect our service from abuse or misuse and keep your access fair and without slowdowns.

Cerebras uses a **dual-bucket model**: every organization has both an **uncached token limit** and a **total token limit**. Improving your cache hit rate lets the same uncached limit serve significantly more total tokens — see [Uncached vs. Total Tokens](#uncached-vs-total-tokens) below.

## How are rate limits measured?

We measure rate limits in requests sent and tokens used within a specified timeframe:

* Requests per minute/hour/day (RPM, RPH, RPD)
* Tokens per minute/hour/day (TPM, TPH, TPD)

Any metric can trigger rate limiting, whichever comes first. For example, you have a rate limit of 50 RPM and 200K TPM. If you submit 50 requests in one minute with just 100 tokens each, you'll hit your limit even though your total token usage (5,000) is far below the 200K token threshold.

Rate limits apply at the organization level, not the user level, and vary based on the model.

### Token Rate Limiting

When you send a request, we estimate the total tokens the request will consume by:

1. Estimating the input tokens in your prompt
2. Adding either the `max_completion_tokens` parameter or an analyzed estimate for an upper bound of the output tokens

If this estimated token consumption would exceed your available token quota, the request is rate limited before processing begins. This estimate is revised once the request is fully processed and your quota is updated to reflect actual usage.

**Best practice**: Set [`max_completion_tokens`](/api-reference/chat-completions#param-max-completion-tokens) appropriately for your use case to avoid overestimating token usage and triggering unnecessary rate limits.

### Quota Replenishment

Your quota is calculated as:

```
Available quota = min(Rate limit, Rate limit + replenished tokens by time − current usage)
```

We use the [token bucketing](https://en.wikipedia.org/wiki/Token_bucket) algorithm for rate limiting, which means your capacity replenishes continuously rather than resetting at fixed intervals. As you consume tokens or requests, your available capacity automatically refills up to your maximum limit.

This token bucketing approach ensures smoother API access and prevents the "burst at interval start, then idle" pattern.

### Uncached vs. Total Tokens

Cerebras enforces two independent token limits per organization:

| Bucket           | What counts                                     | Default                                           |
| ---------------- | ----------------------------------------------- | ------------------------------------------------- |
| **Uncached TPM** | Tokens that require full compute (cache misses) | Primary limit — the main constraint on throughput |
| **Total TPM**    | Uncached + cached tokens combined               | 3× your uncached TPM                              |

Both limits are enforced independently. A [429 error](/support/error) will indicate which bucket was exceeded.

Cached tokens don't count toward your uncached TPM limit, so a higher cache hit rate lets you process far more total tokens within the same uncached limit.

<Check>
  **Example**: With a 1M uncached TPM limit, your total limit is 3M TPM. At a 70% cache hit rate, you can effectively process up to 3M total tokens per minute — 1M uncached plus up to 2M cached — all within your standard limits.
</Check>

To maximize your effective throughput, see [Prompt Caching](/capabilities/prompt-caching).

## Limits by Tier

This provides an overview of general limits, though specific cases may vary. For precise, up-to-date rate limit information applicable to your organization, check the Limits section within your account.

<Tabs>
  <Tab title="Free Trial">
    | Model                      | RPM | Uncached TPM | Total TPM | TPH | TPD |
    | -------------------------- | --- | ------------ | --------- | --- | --- |
    | `gpt-oss-120b`             | 5   | 30K          | 90K       | 1M  | 1M  |
    | `qwen-3.8-27b`<sup>1</sup> | 5   | 30K          | 90K       | 1M  | 1M  |

    <sup>1</sup> Image limits: 2 per request, 10 MiB total request payload
  </Tab>

  <Tab title="Developer (Pay as You Go)">
    | Model                      | Uncached TPM | Total TPM        | RPM |
    | -------------------------- | ------------ | ---------------- | --- |
    | `gpt-oss-120b`             | 1M           | 3M               | 1K  |
    | `qwen-3.8-27b`<sup>1</sup> | 150K         | 750K<sup>2</sup> | 300 |

    <sup>1</sup> Image limits: 10 per request, 10 MiB total request payload

    <sup>2</sup> Temporarily increased from the standard 450K (3× uncached) to 750K (5× uncached).

    <Note>Hourly and daily restrictions don't apply to Developer (Pay as You Go) tier users. You can use as many tokens as needed within your budget.</Note>
  </Tab>

  <Tab title="Enterprise">
    Enterprise rate limits are provisioned per organization based on your usage profile. [Contact us](https://www.cerebras.ai/contact) or reach out to your account representative to discuss limits.

    `qwen-3.8-27b` supports up to 10 images per request by default for Enterprise accounts on the shared tier. Higher image limits may be available with [Dedicated Endpoints](/dedicated) or explicit organization configurations.
  </Tab>
</Tabs>

## Notes

<Note>If you exceed your rate limits, you will receive a [429 Too Many Requests error](/support/error). The error message will indicate whether your **uncached** or **total** token limit was exceeded.</Note>

If you have questions about your usage or need higher rate limits, [contact us](https://www.cerebras.ai/contact) via our website, or reach out to your account representative.

## FAQ

<AccordionGroup>
  <Accordion title="What is the Free Trial tier?">
    New accounts receive **\$5 in free credits** after adding a verified payment method. These credits expire 30 days after they're granted and can be used across all public models. There is no charge until you choose to purchase additional credits. If you skip adding a payment method at sign-up, Playground and API access remain inactive until you do.
  </Accordion>

  <Accordion title="Which models can I use on the Free Trial?">
    Every model on the public [Model Catalog](/models/overview) is available on the Free Trial tier, subject to the per-model Free Trial rate limits listed above. Additional model families listed in [Choose a Model](/models/choose-a-model) are only available through [Dedicated Endpoints](/dedicated/overview).
  </Accordion>

  <Accordion title="Is there a permanently free tier?">
    No. The Free Trial is time- and credit-bounded: \$5 in credits that expire 30 days after they're granted. Once your credits are used up or expire, you need to purchase credits (Pay as You Go) to keep using public endpoints. Cerebras doesn't currently offer a no-cost tier that renews automatically or a per-model always-free allowance.
  </Accordion>

  <Accordion title="What happens when my Free Trial credits run out or expire?">
    API and Playground access stop on the Free Trial tier until you purchase credits. Your API keys, projects, and settings remain intact. A Pay as You Go purchase reactivates access immediately and moves you to the Developer tier, which raises rate limits and removes hourly and daily token caps.
  </Accordion>

  <Accordion title="How do I get higher rate limits?">
    Purchase credits (Pay as You Go) from the **Billing** tab in the [Cloud Console](https://cloud.cerebras.ai). Your first purchase moves you to the Developer tier with significantly higher rate limits and no hourly or daily token caps. For Enterprise limits or reserved capacity, [contact us](https://www.cerebras.ai/contact).
  </Accordion>

  <Accordion title="Where can I see pricing?">
    See [cerebras.ai/pricing](https://www.cerebras.ai/pricing) or each model page (for example, [OpenAI GPT OSS](/models/openai-oss)) for per-token rates. The **Cost** tab in [Usage Monitoring](/console/usage-monitoring) breaks down your spend by model. Dedicated Endpoint pricing varies by organization — [contact us](https://www.cerebras.ai/contact) for a quote.
  </Accordion>
</AccordionGroup>
