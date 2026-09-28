> ## Documentation Index
> Fetch the complete documentation index at: https://docs.sambanova.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# SambaNova model rate limits

Rate limits are a mechanism to help manage SambaNova API usage to provide stable performance and reliable service. They limit how many times each user can call the SambaNova API within a given interval.

Rate limits are measured in:

* RPM: Requests per minute
* RPD: Requests per day
* TPD: Tokens per day (Free tier only)

## Basics

* A **request** is defined by a call to the SambaNova API
* You can hit either limit type (RPM or RPD) depending on which one you reach first
* You will be notified in every request response what the status of your rate limits are ([see rate limit response headers for more information](#rate-limit-response-headers))
* If you hit a rate limit, the API returns an error message in the response ([see API error codes](/docs/en/api-reference/using-the-api/api-error-codes))

## SambaStack rate limits

For SambaStack deployments, rate limits are optional and applied to user groups by the administrator.

## SambaCloud rate limit tiers

SambaNova provides a few different rate limit tier offerings:

* **Free Tier**: Applied when there is no payment method linked with your account
* **Developer Tier**: Applied when a payment method is linked with your account

For higher rate limit access, please [contact the SambaNova sales team](https://sambanova.ai/contact).

<Info>
  Please see the [Billing page](https://cloud.sambanova.ai/plans/billing) to link a payment method to your account.
</Info>

<Note>
  Developer Tier accounts are limited to 20M tokens per day across all models.
</Note>

***

## Production model rate limits

Production models are intended for use in production environments and meet SambaNova's high standards for speed and quality.

<Tabs>
  <Tab title="Developer Tier">
    | **Developer** | **Model ID**                  | **Requests per minute (RPM)** | **Requests per day (RPD)** |
    | :------------ | :---------------------------- | :---------------------------- | :------------------------- |
    | **MiniMax**   | `MiniMax-M2.7`                | 60                            | 12000                      |
    | **DeepSeek**  | `DeepSeek-V3.1`               | 60                            | 12000                      |
    | **Meta**      | `Meta-Llama-3.3-70B-Instruct` | 240                           | 48000                      |
    | **OpenAI**    | `gpt-oss-120b`                | 60                            | 12000                      |
  </Tab>

  <Tab title="Free Tier">
    | **Developer** | **Model ID**                  | **RPM** | **RPD** | **TPD** |
    | :------------ | :---------------------------- | :------ | :------ | :------ |
    | **DeepSeek**  | `DeepSeek-V3.1`               | 20      | 20      | 200000  |
    | **Meta**      | `Meta-Llama-3.3-70B-Instruct` | 20      | 20      | 200000  |
    | **OpenAI**    | `gpt-oss-120b`                | 20      | 20      | 200000  |
  </Tab>
</Tabs>

***

## Preview model rate limits

Preview models are intended for evaluation purposes and developer experimentation only, and should not be used in production environments. These models have limited capacity and may be removed at short notice.

<Tabs>
  <Tab title="Developer Tier">
    | **Developer** | **Model ID**     | **Requests per minute (RPM)** | **Requests per day (RPD)** |
    | :------------ | :--------------- | :---------------------------- | :------------------------- |
    | **DeepSeek**  | `DeepSeek-V3.2`  | 60                            | 12000                      |
    | **Google**    | `gemma-4-31B-it` | 60                            | 12000                      |
  </Tab>

  <Tab title="Free Tier">
    | **Developer** | **Model ID**     | **RPM** | **RPD** | **TPD** |
    | :------------ | :--------------- | :------ | :------ | :------ |
    | **DeepSeek**  | `DeepSeek-V3.2`  | 20      | 20      | 200000  |
    | **Google**    | `gemma-4-31B-it` | 20      | 20      | 200000  |
  </Tab>
</Tabs>

***

## Rate limit response headers

These headers are found in every request response and give information about the current status of rate limit usage.

### RPM (Requests per minute)

* `x-ratelimit-limit-requests` – Maximum requests allowed per minute
* `x-ratelimit-remaining-requests` – Remaining requests in current minute
* `x-ratelimit-reset-requests` – Time until reset

### RPD (Requests per day)

* `x-ratelimit-limit-requests-day` – Maximum requests allowed per day
* `x-ratelimit-remaining-requests-day` – Remaining requests in current day
* `x-ratelimit-reset-requests-day` – Time until reset
