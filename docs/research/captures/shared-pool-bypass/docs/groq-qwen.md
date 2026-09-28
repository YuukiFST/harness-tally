---
description: Model card for Qwen3.8-27B: a compact 27B multimodal (vision + text) model with thinking and instruct modes, frontier-level agentic coding, long-horizon tool use, and near-instant responses on Groq.
title: Qwen 3.8 27B - GroqDocs
image: https://console.groq.com/og_cloudv5.jpg
---

# Qwen/Qwen3.8-27B

Preview

`qwen/qwen3.8-27b`

[Try it in Playground](https://console.groq.com/playground?model=qwen/qwen3.8-27b)

TOKEN SPEED

\~450+ tps

Powered bygroq

INPUT

Text, images

OUTPUT

Text

CAPABILITIES

[Tool Use](https://console.groq.com/docs/tool-use), [JSON Object Mode](https://console.groq.com/docs/structured-outputs#json-object-mode), [JSON Schema Mode](https://console.groq.com/docs/structured-outputs), [Reasoning](https://console.groq.com/docs/reasoning), [Vision](https://console.groq.com/docs/vision)

![Alibaba Cloud logo](https://console.groq.com/_next/image?url=%2Fqwen_logo.png&w=96&q=75)Alibaba Cloud

[Model card](https://huggingface.co/Qwen/Qwen3.8-27B)

Qwen 3.8 27B is a 27-billion-parameter multimodal model from Alibaba's Qwen series, delivering frontier-level agentic coding, reasoning, and long-horizon task performance that rivals models many times its size. It accepts both image and text inputs for visual understanding tasks such as image analysis, OCR, and visual question answering, and supports seamless switching between thinking mode (for complex logical reasoning, math, and coding) and instruct mode (non-thinking, for efficient, general-purpose dialogue) within a single model, with a long context window and strong multilingual support.

---

### PRICING

Input

$0.80

1.3M / $1

Output

$4.00

250,000 / $1

---

### LIMITS

CONTEXT WINDOW

131,072

---

MAX OUTPUT TOKENS

16,384

---

MAX FILE SIZE

20 MB

---

MAX INPUT IMAGES

3

---

### QUANTIZATION

This uses Groq's TruePoint Numerics, which reduces precision only in areas that don't affect accuracy, preserving quality while delivering significant speedup over traditional approaches. [Learn more here](https://groq.com/blog/inside-the-lpu-deconstructing-groq-speed).

### [Key Technical Specifications](#key-technical-specifications)

### Model Architecture

A dense model with 27 billion parameters across 64 layers, using a hybrid Gated DeltaNet and Gated Attention design with a 5120 hidden dimension. Features a dual-mode system supporting both thinking mode for complex reasoning and instruct mode for efficient dialogue, with a 131K-token context window on Groq.

### Performance Metrics

Qwen 3.8 27B demonstrates frontier-level performance across reasoning, coding, and agentic benchmarks:

* GPQA Diamond (Reasoning): 89.2%
* LiveCodeBench v6 (Coding): 90.3%
* SWE-bench Pro (Agentic Coding): 61.7%
* Terminal-Bench 2.1 (Agentic Terminal Use): 73.0%
* IFBench (Instruction Following): 79.5%

### Use Cases

Agentic Coding and Software Engineering

Delivers frontier-level coding performance in a compact dense model, ideal for autonomous coding agents and full-stack development.
* Repository-level code generation and refactoring
* Bug fixing and multi-file edits
* Integration with coding assistants and agent scaffolds
* Tool calling for software engineering workflows

Long-Horizon Agents and Tool Use

Sustains multi-step agentic workflows with strong tool calling and instruction following.
* Terminal and command-line automation
* Multi-step task planning and execution
* Tool orchestration across long sessions
* Reliable structured instruction following

Multimodal Visual Understanding

Accepts image and text inputs for vision tasks alongside its text capabilities.
* Image analysis and captioning
* Optical Character Recognition (OCR)
* Visual question answering
* Chart, diagram, and document understanding

Complex Problem Solving and Dialogue

Switches between deep reasoning and efficient conversation within a single model.
* Multi-step reasoning and mathematical problem solving
* Creative writing and multi-turn dialogue
* Multilingual content generation
* Strategic planning and decision support

### Best Practices

* Mode Selection: use thinking mode (reasoning\_effort="default") for complex reasoning, math, and coding, and instruct mode (reasoning\_effort="none") for efficient, general-purpose dialogue. Tune thinking depth with reasoning\_effort="low", "medium", or "high".
* Thinking Mode: temperature=1.0, top\_p=0.95, top\_k=20, min\_p=0.
* Instruct Mode: temperature=0.7, top\_p=0.80, top\_k=20, min\_p=0, presence\_penalty=1.5.
* Math Problems: include 'Please reason step by step, and put your final answer within \\boxed{}' in the prompt.
* History Management: in multi-turn conversations, only include final outputs without thinking content.
* Reasoning Format: set reasoning\_format to hidden to return only the final answer, or parsed to include the reasoning in a separate field.
* Image Inputs: each image counts as 2048 input tokens.
* Use the full 131K context window for repository-scale code and multi-document workflows.

### [Get Started with Qwen 3.8 27B](#get-started-with-qwen-38-27b)

Experience state-of-the-art reasoning and agentic coding with Qwen 3.8 27B at Groq speed:

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
    model="qwen/qwen3.8-27b",
    messages=[
        {
            "role": "user",
            "content": "Explain why fast inference is critical for reasoning models"
        }
    ]
)
print(completion.choices[0].message.content)
```