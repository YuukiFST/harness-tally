> ## Documentation Index
> Fetch the complete documentation index at: https://docs.modular.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Rate limits

> Learn when rate limits apply and how to increase your organization's limits

Rate limits determine the maximum number of inference requests your
organization can send in a given timeframe. They are measured in requests per
minute (RPM) and tokens per minute (TPM).

## How rate limits work

Rate limits are enforced at two levels:

* **Tier limits** apply to all requests made by your organization across every
  model. Every request counts toward the same organization-wide budget.
* **Model limits** apply independently to each model and are enforced per
  endpoint.

Your request succeeds only if both limits have available capacity. If either
limit is exceeded, the request fails with an HTTP 429 response. You'll have to
wait before future requests run successfully. If this happens frequently,
[contact us](https://console.modular.com/signup) to increase your limits.

## Tier limits

The following table shows the rate limits for
[Starter plan](/administration/billing) tiers.

| Tier   | Requests per minute (RPM) | Tokens per minute (TPM) | Qualification                              |
| ------ | ------------------------- | ----------------------- | ------------------------------------------ |
| Tier 1 | 60                        | 600,000                 | Sign up for Modular Cloud                  |
| Tier 2 | 180                       | 1,800,000               | Add a payment method for your organization |

Enterprise plans include Tier 3 and Tier 4, which raise rate limits above the
Starter plan tiers. [Contact us](https://console.modular.com/signup) when you're
ready for more capacity.

## Model limits

Some models have their own rate limit. The limit is enforced separately for
each endpoint serving that model.

* For **dedicated endpoints**, the model's rate limit is shared by all users in
  your
  organization.
* For **shared endpoints**, the model's rate limit is shared by every
  organization using that endpoint.

The following table lists models that have their own rate limit.

| Model                          | Requests per minute (RPM) | Tokens per minute (TPM) |
| ------------------------------ | ------------------------- | ----------------------- |
| `black-forest-labs/FLUX.2-dev` | 100                       | No limit                |
| `google/gemma-4-26b-a4b-it`    | No limit                  | 1,080,000               |
| `google/gemma-4-31b-it`        | No limit                  | 2,160,000               |
| `moonshotai/Kimi-K2.6`         | No limit                  | 1,800,000               |
| `moonshotai/kimi-k2.7-code`    | No limit                  | 1,800,000               |
