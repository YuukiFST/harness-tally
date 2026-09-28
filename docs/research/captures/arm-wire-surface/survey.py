"""Regenerate the arm wire-survey captures (issue #4) with one command.

    python docs/research/captures/arm-wire-surface/survey.py [scenario ...]

Runs each scenario against a fresh recording mock (`wire_mock.py`) on
127.0.0.1, with the arm boxed into a fresh HOME / XDG / TEMP /
PI_CODING_AGENT_DIR under HB_WIRE_SANDBOX (default C:/tmp/hbwire-sandbox, which
must sit outside any git repository). The invocations mirror harness-bench
`layer1/src/hb_layer1/arms.py` (isolated profile). Arms come from HB_ARMS_DIR
(default C:/hbarms). Output lands next to this file, one directory per scenario.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True  # keep a path-bearing __pycache__ out of the captures
from wire_mock import MODEL_ID, MockSettings, WireMock  # noqa: E402

HERE = Path(__file__).resolve().parent
ARMS_DIR = Path(os.environ.get("HB_ARMS_DIR", "C:/hbarms"))
SANDBOX_ROOT = Path(os.environ.get("HB_WIRE_SANDBOX", "C:/tmp/hbwire-sandbox"))
PROVIDER_ID = "mockollama"
PROMPT = "Read hello.txt and reply with its first line."
RUN_TAGS = {"HB_RUN_ID": "run-0001", "HB_UNIT_ID": "unit-01"}


@dataclass
class Scenario:
    name: str
    arm: str
    base_path: str = "/v1"
    headers: bool = True
    tags_in_env: bool = True
    model_max_tokens: bool = True
    compat_max_tokens_field: str | None = None
    title: str | None = None
    forced_prompt_tokens: int | None = None
    forced_steps: int | None = None
    # Written to <PI_CODING_AGENT_DIR>/settings.json when set.
    pi_settings: dict | None = None
    extra_env: dict[str, str] = field(default_factory=dict)


SCENARIOS = [
    Scenario("pi-baseline", "pi"),
    Scenario("pi-trailing-slash", "pi", base_path="/v1/", headers=False),
    Scenario("pi-missing-env", "pi", tags_in_env=False),
    # keepRecentTokens is lowered so a two-step conversation has something older
    # than the kept tail to summarise; the trigger itself is the default rule.
    Scenario("pi-compaction", "pi", forced_prompt_tokens=30000,
             pi_settings={"compaction": {"keepRecentTokens": 10}}),
    Scenario("pi-default-maxtokens", "pi", model_max_tokens=False, compat_max_tokens_field="max_tokens"),
    Scenario("opencode-baseline", "opencode"),
    Scenario("opencode-title", "opencode", title="unit-01"),
    Scenario("opencode-trailing-slash", "opencode", base_path="/v1/", headers=False),
    Scenario("opencode-missing-env", "opencode", tags_in_env=False),
    Scenario("opencode-compaction", "opencode", forced_prompt_tokens=30000, forced_steps=1),
    Scenario("opencode-default-output", "opencode", model_max_tokens=False),
    Scenario("opencode-output-env", "opencode", extra_env={"OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX": "1234"}),
]


def isolated_env(home: Path) -> dict[str, str]:
    """Same boxing as arms.py `_env_for(ISOLATED, ...)`."""
    env = {k: v for k, v in os.environ.items() if k not in RUN_TAGS}
    env["HOME"] = env["USERPROFILE"] = str(home)
    for key, sub in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"),
                     ("XDG_STATE_HOME", ".local/state"), ("XDG_CACHE_HOME", ".cache")):
        (home / sub).mkdir(parents=True, exist_ok=True)
        env[key] = str(home / sub)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        env[key] = str(home / "tmp")
    return env


def binary(name: str) -> str:
    suffix = ".cmd" if os.name == "nt" else ""
    return str(ARMS_DIR / "node_modules" / ".bin" / f"{name}{suffix}")


def pi_config(s: Scenario, base_url: str) -> dict:
    model: dict = {"id": MODEL_ID, "name": "Wire mock", "reasoning": False, "input": ["text"],
                   "contextWindow": 32768,
                   "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}
    if s.model_max_tokens:
        model["maxTokens"] = 4096
    compat: dict = {"supportsDeveloperRole": False, "supportsReasoningEffort": False}
    if s.compat_max_tokens_field:
        compat["maxTokensField"] = s.compat_max_tokens_field
    provider: dict = {"baseUrl": base_url, "api": "openai-completions", "apiKey": "layer1",
                      "compat": compat, "models": [model]}
    if s.headers:
        provider["headers"] = {"x-hb-run": "$HB_RUN_ID", "x-hb-unit": "${HB_UNIT_ID}",
                               "x-hb-static": "literal-value"}
        model["headers"] = {"x-hb-model-header": "model-level"}
    return {"providers": {PROVIDER_ID: provider}}


def opencode_config(s: Scenario, base_url: str) -> dict:
    options: dict = {"baseURL": base_url, "apiKey": "layer1", "timeout": 120000, "chunkTimeout": 60000}
    # 1.17.9 rejects a `limit` block without `output`, so the no-cap case omits `limit`.
    model: dict = {"limit": {"context": 32768, "output": 4096}} if s.model_max_tokens else {}
    if s.headers:
        options["headers"] = {"x-hb-run": "{env:HB_RUN_ID}", "x-hb-unit": "{env:HB_UNIT_ID}",
                              "x-hb-static": "literal-value"}
        model["headers"] = {"x-hb-model-header": "model-level"}
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {PROVIDER_ID: {"npm": "@ai-sdk/openai-compatible", "name": "Wire mock",
                                   "options": options, "models": {MODEL_ID: model}}},
        "model": f"{PROVIDER_ID}/{MODEL_ID}",
        "small_model": f"{PROVIDER_ID}/{MODEL_ID}",
        "permission": {"*": "allow", "external_directory": "deny", "question": "deny",
                       "webfetch": "deny", "websearch": "deny", "doom_loop": "deny"},
    }


def prepare(s: Scenario, sandbox: Path, base_url: str) -> tuple[list[str], dict[str, str], dict]:
    env = isolated_env(sandbox / "home")
    if s.tags_in_env:
        env.update(RUN_TAGS)
    env.update(s.extra_env)
    workspace = sandbox / "ws"
    if s.arm == "pi":
        config = pi_config(s, base_url)
        agent_dir = sandbox / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "models.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        if s.pi_settings is not None:
            (agent_dir / "settings.json").write_text(json.dumps(s.pi_settings), encoding="utf-8")
        env["PI_CODING_AGENT_DIR"] = str(agent_dir)
        env["PI_OFFLINE"] = "1"
        command = [binary("pi"), "--mode", "json", "--no-session", "--model",
                   f"{PROVIDER_ID}/{MODEL_ID}", PROMPT]
        return command, env, config
    config = opencode_config(s, base_url)
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
    command = [binary("opencode"), "run", "--format", "json", "--dir", str(workspace), "--pure",
               "-m", f"{PROVIDER_ID}/{MODEL_ID}", "--dangerously-skip-permissions"]
    if s.title is not None:
        command += ["--title", s.title]
    return command + [PROMPT], env, config


def run_arm(command: list[str], env: dict[str, str], cwd: Path, timeout_s: int = 180):
    """Run the arm; on timeout kill the whole tree, because on Windows the .cmd
    shim's child (opencode.exe) survives a plain kill and keeps the pipes open."""
    proc = subprocess.Popen(command, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        return subprocess.CompletedProcess(command, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            proc.kill()
        stdout, stderr = proc.communicate()
        return subprocess.CompletedProcess(command, "timeout", stdout, stderr)


def run(s: Scenario) -> dict:
    out = HERE / s.name
    shutil.rmtree(out, ignore_errors=True)
    sandbox = SANDBOX_ROOT / s.name
    shutil.rmtree(sandbox, ignore_errors=True)
    workspace = sandbox / "ws"
    workspace.mkdir(parents=True)
    probe = workspace / "hello.txt"
    probe.write_text("wire survey probe line\n", encoding="utf-8")
    settings = MockSettings(out_dir=out, probe_path=str(probe),
                            forced_prompt_tokens=s.forced_prompt_tokens, forced_steps=s.forced_steps)
    with WireMock(settings) as mock:
        command, env, config = prepare(s, sandbox, mock.origin + s.base_path)
        started = time.monotonic()
        result = run_arm(command, env, workspace)
        wall = time.monotonic() - started
        max_inflight = mock.max_inflight
    (out / "stdout.jsonl").write_bytes(result.stdout)
    (out / "stderr.txt").write_bytes(result.stderr)
    meta = {"scenario": s.name, "arm": s.arm, "command": [Path(command[0]).name, *command[1:]],
            "env_tags": {k: env.get(k) for k in RUN_TAGS},
            "extra_env": s.extra_env, "pi_settings": s.pi_settings, "exit_code": result.returncode,
            "wall_s": round(wall, 2), "max_inflight": max_inflight, "provider_config": config}
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(names: list[str]) -> None:
    for s in SCENARIOS:
        if names and s.name not in names:
            continue
        meta = run(s)
        print(json.dumps({k: meta[k] for k in ("scenario", "exit_code", "wall_s", "max_inflight")}), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
