"""Replay every mock scenario against one arm and keep the evidence.

For each scenario: start mock_upstream.py on its own port, launch the arm in a
fresh isolated sandbox (the harness-bench layer1 `isolated` recipe from
layer1/src/hb_layer1/arms.py @ 9c0fe11), wait for exit or the timeout, then
write <arm>-<scenario>/{mock.jsonl,stdout.jsonl,stderr.txt,meta.json} next to
this file.

Usage: python run_matrix.py <pi|opencode> <base_port> <sandbox_root> [scenario ...]
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS_BIN = Path(os.environ.get("HB_ARMS_DIR", "C:/hbarms")) / "node_modules" / ".bin"
PROVIDER, MODEL = "mockollama", "MOCK-2.6B"
PROMPT = "Reply with the single word done."
ALL = ["ok", "no_finish", "no_usage", "usage_after_done", "r429", "r429_wrapped", "r500", "err200_json", "err200_sse", "disconnect"]
# opencode has no attempt cap (see the write-up), so its retry scenarios are cut off here.
TIMEOUT_S = {"pi": 90, "opencode": 150}


def isolated_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("HOME", "USERPROFILE"):
        env[key] = str(home)
    for key, sub in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"),
                     ("XDG_STATE_HOME", ".local/state"), ("XDG_CACHE_HOME", ".cache"), ("TEMP", "tmp"),
                     ("TMP", "tmp"), ("TMPDIR", "tmp")):
        (home / sub).mkdir(parents=True, exist_ok=True)
        env[key] = str(home / sub)
    return env


def pi_invocation(sandbox: Path, base_url: str) -> tuple[list[str], dict[str, str]]:
    agent = sandbox / "agent"
    agent.mkdir(parents=True, exist_ok=True)
    models = {"providers": {PROVIDER: {
        "baseUrl": base_url, "api": "openai-completions", "apiKey": "layer1",
        "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
        "models": [{"id": MODEL, "name": "mock", "reasoning": False, "input": ["text"],
                    "contextWindow": 32768, "maxTokens": 4096,
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]}}}
    (agent / "models.json").write_text(json.dumps(models), encoding="utf-8")
    env = isolated_env(sandbox / "home")
    env["PI_CODING_AGENT_DIR"] = str(agent)
    env["PI_OFFLINE"] = "1"
    cmd = [str(ARMS_BIN / "pi.cmd"), "--mode", "json", "--no-session", "--model", f"{PROVIDER}/{MODEL}", PROMPT]
    return cmd, env


def opencode_invocation(sandbox: Path, base_url: str, workspace: Path) -> tuple[list[str], dict[str, str]]:
    env = isolated_env(sandbox / "home")
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "provider": {PROVIDER: {"npm": "@ai-sdk/openai-compatible", "name": "mock",
                                "options": {"baseURL": base_url, "apiKey": "layer1", "timeout": 120000, "chunkTimeout": 60000},
                                "models": {MODEL: {"limit": {"context": 32768, "output": 4096}}}}},
        "model": f"{PROVIDER}/{MODEL}", "small_model": f"{PROVIDER}/{MODEL}",
        "permission": {"*": "allow", "external_directory": "deny", "question": "deny", "webfetch": "deny",
                       "websearch": "deny", "doom_loop": "deny"},
    })
    # Keep the run offline: no models.dev fetch, no self-update check.
    env["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
    cmd = [str(ARMS_BIN / "opencode.cmd") if (ARMS_BIN / "opencode.cmd").exists() else str(ARMS_BIN / "opencode"),
           "run", "--format", "json", "--dir", str(workspace), "--pure", "-m", f"{PROVIDER}/{MODEL}",
           "--dangerously-skip-permissions", PROMPT]
    return cmd, env


def kill_tree(proc: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def run_one(arm: str, scenario: str, port: int, root: Path) -> dict:
    out = HERE / f"{arm}-{scenario}"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    sandbox = root / f"{arm}-{scenario}"
    shutil.rmtree(sandbox, ignore_errors=True)
    workspace = sandbox / "ws"
    workspace.mkdir(parents=True)
    log = out / "mock.jsonl"
    mock = subprocess.Popen([sys.executable, str(HERE / "mock_upstream.py"), scenario, str(port), str(log)],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    mock.stdout.readline()  # wait until listening
    base_url = f"http://127.0.0.1:{port}/v1"
    if arm == "pi":
        cmd, env = pi_invocation(sandbox, base_url)
    else:
        cmd, env = opencode_invocation(sandbox, base_url, workspace)
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=workspace, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT_S[arm])
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(proc)
        stdout, stderr = proc.communicate()
    wall = round(time.monotonic() - t0, 2)
    mock.terminate()
    mock.wait()
    (out / "stdout.jsonl").write_bytes(stdout)
    (out / "stderr.txt").write_bytes(stderr[-20000:])
    meta = {"arm": arm, "scenario": scenario, "exit_code": None if timed_out else proc.returncode,
            "timed_out_after_s": TIMEOUT_S[arm] if timed_out else None, "wall_s": wall,
            "command": [Path(cmd[0]).name, *cmd[1:]]}
    (out / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    arm, base_port, root = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    scenarios = sys.argv[4:] or ALL
    for i, scenario in enumerate(scenarios):
        print(json.dumps(run_one(arm, scenario, base_port + i, root)), flush=True)


if __name__ == "__main__":
    main()
