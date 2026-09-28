# Writes the request bodies probed by capture.sh into requests/.
# Shapes mimic what the arms send (docs/research/arm-wire-surface.md):
#   pi 0.80.10      -> max_completion_tokens, store:false, stream_options.include_usage
#   opencode 1.17.9 -> max_tokens, tool_choice:"auto", stream_options.include_usage
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "requests")
os.makedirs(OUT, exist_ok=True)

SYSTEM = "You are a coding agent. Use tools when the user asks you to act on files. Be brief."
TOOLS = [
    {"type": "function", "function": {
        "name": "read", "description": "Read a file from disk and return its contents.",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "Path to the file"}},
                       "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "bash", "description": "Run a shell command and return stdout.",
        "parameters": {"type": "object",
                       "properties": {"command": {"type": "string"}},
                       "required": ["command"]}}},
]

# model slug, short name, published max output, provider slug for pinning, small cap.
# qwen reasons at effort xhigh by default, so its small cap leaves room for reasoning
# before content; gemma has reasoning off by default.
MODELS = [
    ("google/gemma-4-31b-it:free", "gemma", 32768, "google-ai-studio", 64, 256),
    ("qwen/qwen3.8-27b:free", "qwen", 235929, "modelrun/fp4", 2048, 2048),
]


def msgs(user):
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def pi(model, cap, user="Reply with the single word: ok", stream=True, usage=True):
    b = {"model": model, "messages": msgs(user), "tools": TOOLS}
    if stream:
        b["stream"] = True
        if usage:
            b["stream_options"] = {"include_usage": True}
    b["max_completion_tokens"] = cap
    b["store"] = False
    return b


def oc(model, cap, user):
    return {"model": model, "messages": msgs(user), "tools": TOOLS, "tool_choice": "auto",
            "max_tokens": cap, "stream": True, "stream_options": {"include_usage": True}}


def write(name, body):
    with open(os.path.join(OUT, name + ".json"), "w", newline="\n") as f:
        json.dump(body, f, separators=(",", ":"))


for model, short, pub_cap, pin, small, tool_cap in MODELS:
    write(f"{short}-p1-pi-stream-usage", pi(model, small))
    write(f"{short}-p2-pi-stream-nousage", pi(model, small, usage=False))
    write(f"{short}-p3-oc-tool-single", oc(model, tool_cap, "Call the read tool on the path notes.txt."))
    write(f"{short}-p4-oc-tool-parallel", oc(
        model, tool_cap,
        "Call the read tool twice in this one response, in parallel: once on a.txt and once on b.txt."))
    write(f"{short}-p5-pi-nonstream", pi(model, small, stream=False))
    cap = oc(model, pub_cap, "Reply with the single word: ok")
    write(f"{short}-p6-oc-at-cap", cap)
    over = dict(cap, max_tokens=pub_cap + 1)
    write(f"{short}-p7-oc-over-cap", over)
    pinned = pi(model, small)
    pinned["provider"] = {"only": [pin], "allow_fallbacks": False}
    write(f"{short}-p8-pi-provider-pin", pinned)

unknown = pi("google/gemma-4-31b-it-nonexistent:free", 64)
write("unknown-model", unknown)
