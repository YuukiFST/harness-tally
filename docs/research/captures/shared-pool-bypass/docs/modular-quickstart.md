> ## Documentation Index
> Fetch the complete documentation index at: https://docs.modular.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Get free credits and start running inference

In just a few minutes, you'll be chatting with the latest open source models
and sending inference requests with the Modular Cloud API.

## Try the playground

Here's how to play with some models without writing any code.

<Steps>
  <Step title="Log in">
    Sign up with your work email at [console.modular.com](https://console.modular.com/signup).
  </Step>

  <Step title="Create an API key">
    Click **API keys** in the sidebar and create a new **Personal key**.

    Make sure to enable **Model access**, and copy the key to a safe
    place—you'll need it again below to call the API.
  </Step>

  <Step title="Chat with a model">
    Click **Playground** in the sidebar and select your API key at the top.

    Now start chatting with a model!
  </Step>
</Steps>

You can try different models using the menu at the top of the chat.

## Run inference with the API

Here's a quick guide to running inference with the chat completions API.

<Steps>
  <Step title="Set your API key">
    Insert the API key you created above or
    [create a new key](https://console.modular.com/api_keys).

    <CodeGroup>
      ```bash macOS/Linux theme={null}
      export MODULAR_API_KEY="your_api_key"
      ```

      ```bash Windows theme={null}
      $env:MODULAR_API_KEY="your_api_key"
      ```
    </CodeGroup>
  </Step>

  <Step title="Install the OpenAI client">
    You can skip this if you're going to use cURL.

    <CodeGroup>
      ```bash Python (pip) theme={null}
      pip install openai
      ```

      ```bash Python (uv) theme={null}
      uv init quickstart && cd quickstart
      uv add openai
      ```

      ```bash Python (pixi) theme={null}
      pixi init quickstart && cd quickstart
      pixi add openai
      ```

      ```bash TypeScript (npm) theme={null}
      mkdir quickstart && cd quickstart
      npm init -y && npm install openai
      ```
    </CodeGroup>
  </Step>

  <Step title="Copy this code">
    <CodeGroup>
      ```python Python theme={null}
      import os
      from openai import OpenAI

      client = OpenAI(
          base_url="https://api.modular.com/v1",
          api_key=os.environ.get("MODULAR_API_KEY"),
      )

      response = client.chat.completions.create(
          model="minimax/minimax-m3",
          messages=[{"role": "user", "content": "Hello, how are you?"}],
      )

      print(response.choices[0].message.content)
      ```

      ```typescript TypeScript theme={null}
      import process from "node:process";
      import OpenAI from "openai";

      const client = new OpenAI({
        baseURL: "https://api.modular.com/v1",
        apiKey: process.env.MODULAR_API_KEY,
      });

      async function main() {
        const response = await client.chat.completions.create({
          model: "minimax/minimax-m3",
          messages: [{ role: "user", content: "Hello, how are you?" }],
        });

        console.log(response.choices[0].message.content);
      }

      main();
      ```

      ```bash cURL theme={null}
      curl -X POST https://api.modular.com/v1/chat/completions \
        -H "Authorization: Bearer $MODULAR_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
          "model": "minimax/minimax-m3",
          "messages": [{"role": "user", "content": "Hello, how are you?"}]
        }'
      ```
    </CodeGroup>
  </Step>

  <Step title="Run it">
    <CodeGroup>
      ```bash Python (pip) theme={null}
      python main.py
      ```

      ```bash Python (uv) theme={null}
      uv run main.py
      ```

      ```bash Python (pixi) theme={null}
      pixi run python main.py
      ```

      ```bash TypeScript (npm) theme={null}
      npx tsx main.ts
      ```
    </CodeGroup>

    You should quickly see the response.
  </Step>
</Steps>

That's it! You're up and running.

To try a different model, just change the code's `model` parameter:
Browse the available [shared endpoints](https://console.modular.com/endpoints)
and click a model, then copy the **Model ID** shown on the right.

## Next steps

Check out these guides to learn more about using the Modular Cloud APIs:

* [Text inference](inference/text): text-to-text, image-to-text, and
  video-to-text
* [Image inference](inference/image): generate and transform images with FLUX
* [Video inference](inference/video): generate video from text with Wan
* [AI tool integration](coding-assistants/cursor): use Modular Cloud models in
  Cursor, Codex, TRAE, and other AI tools
