> ## Documentation Index
> Fetch the complete documentation index at: https://docs.modular.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Supported models

> Modular Cloud supports models on shared and dedicated endpoints

<div class="max-w-xl">
  This page lists all Modular Cloud's supported models and endpoint availability.
  You can also find comprehensive information in the console's
  [Models](https://console.modular.com/models) page.

  ## Endpoints

  Modular Cloud supports two endpoint types:

  * **Shared endpoints** provide serverless, pay-as-you-go inference on
    multi-tenant infrastructure. They are automatically available to all
    organizations. Models with shared endpoints are marked on the table
    below.
  * **Dedicated endpoints** originate from [dedicated deployments](/deployments).
    Modular Cloud can provision a dedicated deployment for any supported model.
    Use dedicated endpoints for production inference.
</div>

## Models

Modular Cloud supports the following models:

<div class="models-table">
  | Name                                                                                                                     | Provider          |      Shared endpoint     | Type               | Context |
  | ------------------------------------------------------------------------------------------------------------------------ | ----------------- | :----------------------: | ------------------ | ------- |
  | [GLM 5.2](https://www.modular.com/models/glm-5-2)<br />`z-ai/glm-5.2`                                                    | Z.ai              | <div class="yes">✓</div> | LLM                | 1M      |
  | [Gemma 4 31B](https://www.modular.com/models/google-gemma-4-31b-it)<br />`google/gemma-4-31b-it`                         | Google            | <div class="yes">✓</div> | LLM, Vision        | 256K    |
  | [MiniMax M3](https://www.modular.com/models/minimax-m3-public)<br />`minimax/minimax-m3`                                 | MiniMax           | <div class="yes">✓</div> | LLM, Vision        | 1M      |
  | [Kimi K2.7 Code](https://www.modular.com/models/moonshotai-kimi-k2-7-code)<br />`moonshotai/kimi-k2.7-code`              | Moonshot AI       | <div class="yes">✓</div> | LLM, Vision        | 256K    |
  | [FLUX.2 Klein 4B](https://www.modular.com/models/flux2-klein-4b-fp4)<br />`black-forest-labs/FLUX.2-klein-4B`            | Black Forest Labs | <div class="yes">✓</div> | Image              | —       |
  | [DeepSeek V3.2](https://www.modular.com/models/deepseek-v3-2)<br />`deepseek-ai/DeepSeek-V3.2`                           | DeepSeek          |  <div class="no">x</div> | LLM                | 128K    |
  | [DeepSeek V4 Flash](https://www.modular.com/models/deepseek-v4-flash)<br />`deepseek-ai/DeepSeek-V4-Flash`               | DeepSeek          |  <div class="no">x</div> | LLM                | 1M      |
  | [DeepSeek V4 Pro](https://www.modular.com/models/deepseek-v4-pro)<br />`deepseek-ai/DeepSeek-V4-Pro`                     | DeepSeek          |  <div class="no">x</div> | LLM                | 1M      |
  | [Mistral Nemo](https://www.modular.com/models/mistral-nemo)<br />`mistralai/Mistral-Nemo-Instruct-2407`                  | Mistral AI        |  <div class="no">x</div> | LLM                | 128K    |
  | [Nemotron 3 Ultra](https://www.modular.com/models/nemotron-3-ultra)<br />`nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16` | NVIDIA            |  <div class="no">x</div> | LLM                | 1M      |
  | [gpt-oss-120b](https://www.modular.com/models/gpt-oss-120b)<br />`openai/gpt-oss-120b`                                   | OpenAI            |  <div class="no">x</div> | LLM                | 128K    |
  | [gpt-oss-20b](https://www.modular.com/models/gpt-oss-20b)<br />`openai/gpt-oss-20b`                                      | OpenAI            |  <div class="no">x</div> | LLM                | 128K    |
  | [MiMo-V2.5-Pro](https://www.modular.com/models/mimo-v2.5-pro)<br />`XiaomiMiMo/MiMo-V2.5-Pro`                            | Xiaomi            |  <div class="no">x</div> | LLM                | 256K    |
  | [GLM 5.3](https://www.modular.com/models/z-glm-5-3)<br />`zai-org/GLM-5.3`                                               | Z.ai              |  <div class="no">x</div> | LLM                | 1M      |
  | [Qwen3.5-397B-A17B](https://www.modular.com/models/qwen3-5-397b-a17b)<br />`Qwen/Qwen3.5-397B-A17B`                      | Alibaba           |  <div class="no">x</div> | LLM, Vision        | 262K    |
  | [Gemma 4 26B A4B](https://www.modular.com/models/google-gemma-4-26b-a4b-it)<br />`google/gemma-4-26B-A4B-it`             | Google            |  <div class="no">x</div> | LLM, Vision        | 256K    |
  | [Llama 4 Maverick](https://www.modular.com/models/llama-4-maverick)<br />`meta-llama/Llama-4-Maverick-17B-128E-Instruct` | Meta              |  <div class="no">x</div> | LLM, Vision        | 1M      |
  | [Llama 4 Scout](https://www.modular.com/models/llama-4-scout)<br />`meta-llama/Llama-4-Scout-17B-16E-Instruct`           | Meta              |  <div class="no">x</div> | LLM, Vision        | 10M     |
  | [Kimi K2.5](https://www.modular.com/models/moonshotai-kimi-k2-5)<br />`moonshotai/Kimi-K2.5`                             | Moonshot AI       |  <div class="no">x</div> | LLM, Vision        | 256K    |
  | [Kimi K2.6](https://www.modular.com/models/moonshotai-kimi-k2-6)<br />`moonshotai/Kimi-K2.6`                             | Moonshot AI       |  <div class="no">x</div> | LLM, Vision        | 256K    |
  | [GLM 5.3 Flash](https://www.modular.com/models/glm-5-3-flash)<br />`zai-org/GLM-5.3-Flash`                               | Z.ai              |  <div class="no">x</div> | LLM, Vision        | 1M      |
  | [Inkling](https://www.modular.com/models/thinkingmachines-inkling)<br />`thinkingmachines/Inkling`                       | Thinking Machines |  <div class="no">x</div> | LLM, Vision, Audio | 1M      |
  | [FLUX.2 Dev](https://www.modular.com/models/flux2-dev-fp4)<br />`black-forest-labs/FLUX.2-dev`                           | Black Forest Labs |  <div class="no">x</div> | Image              | —       |
  | [FLUX.2 Klein 9B](https://www.modular.com/models/flux2-klein-9b-fp4)<br />`black-forest-labs/FLUX.2-klein-9B`            | Black Forest Labs |  <div class="no">x</div> | Image              | —       |
  | [Wan 2.2 I2V A14B](https://www.modular.com/models/wan2-2-i2v-a14b-diffusers)<br />`Wan-AI/Wan2.2-I2V-A14B-Diffusers`     | Wan AI            |  <div class="no">x</div> | Video              | —       |
  | [Wan 2.2 T2V A14B](https://www.modular.com/models/wan2-2-t2v-a14b-diffusers)<br />`Wan-AI/Wan2.2-T2V-A14B-Diffusers`     | Wan AI            |  <div class="no">x</div> | Video              | —       |
  | [Wan 2.2 TI2V 5B](https://www.modular.com/models/wan2-2-ti2v-5b-diffusers)<br />`Wan-AI/Wan2.2-TI2V-5B-Diffusers`        | Wan AI            |  <div class="no">x</div> | Video              | —       |
  | [LTX-2.3](https://www.modular.com/models/ltx-2-3-nvfp4)<br />`Lightricks/LTX-2.3-nvfp4`                                  | Lightricks        |  <div class="no">x</div> | Video, Audio       | —       |
</div>
