> ## Documentation Index
> Fetch the complete documentation index at: https://docs.modular.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Billing

> Manage billing and learn how to update your plan

Modular Cloud offers credit or contract-based billing plans. This page explains
how to manage billing depending on your billing plan.

[Set up billing in the console →](https://console.modular.com/billing)

## Compare plans

There are two billing plans:

| Plan       | Billing method                     | Access                         | Rate limit tier |
| ---------- | ---------------------------------- | ------------------------------ | --------------- |
| Starter    | Buy credits                        | Shared endpoints only          | Tiers 1 and 2   |
| Enterprise | Contract and usage-based invoicing | Shared and dedicated endpoints | Tiers 3 and 4   |

You can't create dedicated endpoints on the Starter plan. To deploy models on
dedicated infrastructure, you need an Enterprise plan.
[Contact us](https://console.modular.com/signup) to learn more about
Enterprise plans.

For specific rate limits per tier, see
[Rate limits](/administration/rate-limits).

## Use credits

On the Starter plan, you must have credits to send inference requests. New
Modular Cloud accounts include free credits, so you can start making requests
right away.

Each request deducts credits for input and output tokens. Token prices vary by
model deployment—check prices for each model on the **Models** and
**Endpoints** pages in the console. Prices shown are the cost per 1 million
tokens used.

Dedicated deployments are priced separately based on the configuration you
choose.

<Note>
  One credit equals one US dollar (USD). There's no separate conversion rate for
  credits, so your credit balance and all model prices are in the same units.
</Note>

## Add credits

If your credit balance reaches zero, requests that use your API keys
return a 401 response.

When you need to add credits, follow these steps:

1. Open the console [**Billing** page](https://console.modular.com/billing).
2. In the **Payment method** section, click **Add card**.
3. Complete the checkout form in Stripe. Stripe then returns you to the
   **Billing** page.
4. In the **Credit balance** section, click **Buy credits**.
5. In the **Amount (USD)** field, enter the amount you want to buy, then click
   **Buy credits**.

Credits usually appear right away. If the payment takes longer to clear, the
console confirms the purchase and adds the credits once it settles.

## Monitor billing

The Billing page also lets you monitor billing activity for your organization.

* **Current billing cycle**: monitor the state of the current billing cycle for
  all models.
* **Past invoices**: review and export past invoices.
* **Transaction history**: inspect and export individual transactions.
