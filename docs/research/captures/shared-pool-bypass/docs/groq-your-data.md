---
description: Learn how GroqCloud handles data retention, including standard 30-day retention, Zero Data Retention (ZDR) options, prompt caching, and compliance requirements for prompts and outputs.
title: Your Data in GroqCloud - GroqDocs
image: https://console.groq.com/og_cloudv5.jpg
---

# Your Data in GroqCloud

Understand how Groq uses customer data and the controls you have.

## [What Data Groq Retains](#what-data-groq-retains)

Groq handles two distinct types of information:

1. **Usage Metadata (always retained)**

  * We collect usage metadata for all users to measure service activity and system performance.
  * This metadata does **not** contain customer inputs or outputs.
2. **Customer Data (retained only in limited circumstances)**

  * **By default, Groq does not retain customer data for inference requests.**
  * Customer data (inputs, outputs, and related state) is only retained in two cases:  
    1. **If you use features that require data retention to function** (e.g., batch jobs, fine-tuning and LoRAs).
    2. **If needed to protect platform reliability** (e.g., to troubleshoot system failures or investigate abuse).
  
You can control these settings yourself in the [Data Controls settings](https://console.groq.com/settings/data-controls).

## [When Customer Data May Be Retained](#when-customer-data-may-be-retained)

Review the [Data Location](#data-location) section below to learn where data is retained.

### [1\. Application State](#1-application-state)

Certain API features require data retention to function:

* **Batch Processing (`/openai/v1/batches`)**: Input and output files retained for 30 days unless deleted earlier by the customer.
* **Fine-tuning (`/openai/v1/fine_tunings`)**: Model weights and training datasets retained until deleted by the customer.

To prevent data retention for application state, you can disable these features for all users in your organization in [Data Controls settings](https://console.groq.com/settings/data-controls).

### [2\. System Reliability and Abuse Monitoring](#2-system-reliability-and-abuse-monitoring)

As noted above, inference requests are not retained by default. We may temporarily log inputs and outputs **only when**:

* Troubleshooting errors that degrade platform reliability, or
* Investigating suspected abuse (e.g. rate-limit circumvention).

These logs are retained for up to **30 days**, unless legally required to retain longer. You may opt out of this storage in [Data Controls settings](https://console.groq.com/settings/data-controls), but you remain responsible for ensuring safe, compliant usage of the services in accordance with [the terms](https://groq.com/terms-of-use) and [Acceptable Use & Responsible AI Policy](https://console.groq.com/docs/legal/ai-policy).

## [Summary Table](#summary-table)

| Product     | Endpoints                                                                                                                          | Data Retention Type                     | Retention Period | ZDR Eligible           |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ---------------- | ---------------------- |
| Inference   | /openai/v1/chat/completions/openai/v1/responses/openai/v1/audio/transcriptions/openai/v1/audio/translations/openai/v1/audio/speech | System reliability and abuse monitoring | Up to 30 days    | Yes                    |
| Batch       | /openai/v1/batches/openai/v1/files (purpose: batch)                                                                                | Application state                       | Up to 30 days    | Yes (feature disabled) |
| Fine-tuning | /openai/v1/fine\_tunings/openai/v1/files (purpose: fine\_tuning)                                                                   | Application state                       | Until deleted    | Yes (feature disabled) |

## [Zero Data Retention](#zero-data-retention)

All customers may enable Zero Data Retention (ZDR) in [Data Controls settings](https://console.groq.com/settings/data-controls). When ZDR is enabled, Groq will not retain customer data for system reliability and abuse monitoring. As noted above, this also means that features that rely on data retention to function will be disabled. Organization admins can decide to enable ZDR globally or on a per-feature basis at any time on the Data Controls page in [Data Controls settings](https://console.groq.com/settings/data-controls).

## [Data Location](#data-location)

All customer data is retained in Google Cloud Platform (GCP) buckets located in the United States. Groq maintains strict access controls and security standards as detailed in the [Groq Trust Center](https://trust.groq.com/). Where applicable, Customers can rely on standard contractual clauses (SCCs) for transfers between third countries and the U.S.

## [Key Takeaways](#key-takeaways)

* **Usage metadata**: always collected, never includes customer data.
* **Customer data**: not retained by default. Only retained if you opt into persistence features, or in cases for system reliability and abuse monitoring.
* **Controls**: You can manage data retention in [Data Controls settings](https://console.groq.com/settings/data-controls), including opting into **Zero Data Retention**.