---
description: OpenAI&#x27;s flagship open-weight MoE model with 120B total parameters. Designed for high-capability agentic use.
title: OpenAI GPT-OSS 120B - GroqDocs
image: https://console.groq.com/og_cloudv5.jpg
---

# GPT OSS 120B

`openai/gpt-oss-120b`

[Try it in Playground](https://console.groq.com/playground?model=openai/gpt-oss-120b)

TOKEN SPEED

\~500 tps

Powered bygroq

INPUT

Text

OUTPUT

Text

CAPABILITIES

[Tool Use](https://console.groq.com/docs/tool-use), [Browser Search](https://console.groq.com/docs/browser-search), [Code Execution](https://console.groq.com/docs/code-execution), [JSON Object Mode](https://console.groq.com/docs/structured-outputs#json-object-mode), [JSON Schema Mode](https://console.groq.com/docs/structured-outputs), [Reasoning](https://console.groq.com/docs/reasoning)

![OpenAI logo](https://console.groq.com/_next/static/media/openailogo.523c87a0.svg)OpenAI

[Model card](https://openai.com/index/gpt-oss-model-card/)

OpenAI's flagship open-weight MoE model with 120B total parameters. Designed for high-capability agentic use, it matches or surpasses proprietary models like OpenAI o4-mini on many benchmarks. With long-context reasoning, competitive math/coding performance, and robust health knowledge, it is ideal for advanced research, autonomous tools, and agentic applications.

---

### PRICING

Input

$0.15

6.7M / $1

Cached Input

$0.075

13M / $1

Output

$0.60

1.7M / $1

---

### LIMITS

CONTEXT WINDOW

131,072

---

MAX OUTPUT TOKENS

65,536

---

### QUANTIZATION

This uses Groq's TruePoint Numerics, which reduces precision only in areas that don't affect accuracy, preserving quality while delivering significant speedup over traditional approaches. [Learn more here](https://groq.com/blog/inside-the-lpu-deconstructing-groq-speed).

### [Key Technical Specifications](#key-technical-specifications)

### Model Architecture

Built on a Mixture-of-Experts (MoE) architecture with 120B total parameters (5.1B active per forward pass). Features 36 layers with 128 MoE experts using Top-4 routing per token. Equipped with Grouped Query Attention and rotary embeddings, using RMSNorm pre-layer normalization with 2880 residual width.

### Performance Metrics

The GPT-OSS 120B model demonstrates exceptional performance across key benchmarks:

* MMLU (General Reasoning): 90.0%
* SWE-Bench Verified (Coding): 62.4%
* HealthBench Realistic (Health): 57.6%
* MMMLU (Multilingual): 81.3% average

### Use Cases

Frontier-Grade Agentic Applications

Deploy for high-capability autonomous agents with advanced reasoning, tool use, and multi-step problem solving that matches proprietary model performance.

Advanced Research & Scientific Computing

Ideal for research applications requiring robust health knowledge, biosecurity analysis, and scientific reasoning with strong safety alignment.

High-Accuracy Mathematical & Coding Tasks

Excels at competitive programming, complex mathematical reasoning, and software engineering tasks with state-of-the-art benchmark performance.

Multilingual AI Assistants

Build sophisticated multilingual applications with strong performance across 81+ languages and cultural contexts.

### Best Practices

* Utilize variable reasoning modes (low, medium, high) to balance performance and latency based on your specific use case requirements.
* Leverage the Harmony chat format with proper role hierarchy (System > Developer > User > Assistant) for optimal instruction following and safety compliance.
* Take advantage of the model's preparedness testing for biosecurity and alignment research while respecting safety boundaries.
* Use the full 131K context window for complex, multi-step workflows and comprehensive document analysis.
* Structure tool definitions clearly when using web browsing, Python execution, or function calling capabilities for best results.

### [Get Started with GPT-OSS 120B](#get-started-with-gptoss-120b)

Experience `openai/gpt-oss-120b` on Groq:

curlJavaScriptPythonJSON

shell

```
pip install groq
```

Python

```
from groq import Groq
client = Groq()
completion = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {
            "role": "user",
            "content": "Explain why fast inference is critical for reasoning models"
        }
    ]
)
print(completion.choices[0].message.content)
```