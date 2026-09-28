"""Live smoke: one pi 0.80.10 prompt through harness-tally to OpenRouter free.

Budget: exactly one chat completion per run (pi's agent retry is switched off in
its settings), so a shared-pool 429 ends the run after one request.

    python docs/research/captures/live-smoke/run.py qwen/qwen3.8-27b:free

Refuses to start while the pool sampler runs, so two live probes never overlap.
Writes run-<UTC>-<model>/ next to this file: the proxy's out dir (records,
bodies, summary), pi's stdout and stderr, and meta.json. The key reaches only
the proxy's environment; the script fails if it finds the key in any file it wrote.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SAMPLER_PID = REPO / "docs" / "research" / "captures" / "pool-availability" / "sampler.pid"
ARMS_BIN = Path(os.environ.get("HB_ARMS_DIR", "C:/hbarms")) / "node_modules" / ".bin"
# HT_SMOKE_UPSTREAM points the same flow at a local stub for a dry run.
UPSTREAM = os.environ.get("HT_SMOKE_UPSTREAM", "https://openrouter.ai/api/v1")
LIVE = UPSTREAM.startswith("https://openrouter.ai")
PROMPT = "Reply with the single word: ok"


def read_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key or os.name != "nt":
        return key
    command = '[Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY","User")'
    return subprocess.run(["powershell.exe", "-NoProfile", "-Command", command], capture_output=True, text=True).stdout.strip()


def isolated_env(sandbox: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    home = sandbox / "home"
    for key in ("HOME", "USERPROFILE"):
        env[key] = str(home)
    for key, sub in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"), ("XDG_STATE_HOME", ".local/state"), ("XDG_CACHE_HOME", ".cache")):
        (home / sub).mkdir(parents=True, exist_ok=True)
        env[key] = str(home / sub)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        env[key] = str(home / "tmp")
    env["PI_CODING_AGENT_DIR"] = str(sandbox / "agent")
    env["PI_OFFLINE"] = "1"
    return env


def write_pi_config(agent_dir: Path, base_url: str, model: str) -> None:
    agent_dir.mkdir(parents=True, exist_ok=True)
    provider = {
        "baseUrl": base_url,
        "api": "openai-completions",
        "apiKey": "harness-tally",
        "models": [{"id": model, "name": model, "reasoning": False, "input": ["text"], "contextWindow": 262144, "maxTokens": 2048, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}],
    }
    (agent_dir / "models.json").write_text(json.dumps({"providers": {"tally": provider}}, indent=2), encoding="utf-8")
    (agent_dir / "settings.json").write_text(json.dumps({"retry": {"enabled": False}}, indent=2), encoding="utf-8")


def main(model: str) -> int:
    if LIVE and SAMPLER_PID.exists():
        print("pool sampler is running; refusing to start a second live probe", file=sys.stderr)
        return 2
    key = read_key() if LIVE else "sk-dry-run-sentinel"
    if not key:
        print("OPENROUTER_API_KEY not found", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = HERE / f"run-{stamp}-{model.split('/')[0]}"
    sandbox = Path(os.environ.get("TEMP", "/tmp")) / f"ht-smoke-{stamp}"
    proxy = subprocess.Popen(
        [sys.executable, "-m", "harness_tally", "serve", "--upstream", UPSTREAM, "--run-id", f"smoke-{stamp}", "--out", str(run_dir / "out"), "--upstream-key-env", "OPENROUTER_API_KEY"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, "OPENROUTER_API_KEY": key},
    )
    assert proxy.stdout is not None and proxy.stdin is not None
    ready = json.loads(proxy.stdout.readline())
    write_pi_config(sandbox / "agent", ready["base_url"], model)
    pi = shutil.which("pi", path=str(ARMS_BIN)) or "pi"
    workspace = sandbox / "ws"
    workspace.mkdir(parents=True, exist_ok=True)
    arm = subprocess.run([pi, "--mode", "json", "--no-session", "--provider", "tally", "--model", model, PROMPT], cwd=workspace, env=isolated_env(sandbox), stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
    proxy.stdin.close()
    proxy_exit = proxy.wait(60)
    (run_dir / "pi-stdout.jsonl").write_bytes(arm.stdout)
    (run_dir / "pi-stderr.txt").write_bytes(arm.stderr)
    subprocess.run([sys.executable, "-m", "harness_tally", "summarize", str(run_dir / "out")], capture_output=True, check=True)
    meta = {"utc": stamp, "model": model, "pi_exit": arm.returncode, "proxy_exit": proxy_exit, "ready": ready, "prompt": PROMPT, "budget": "1 completion, pi retry disabled"}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    leaks = [p for p in run_dir.rglob("*") if p.is_file() and key.encode() in p.read_bytes()]
    if leaks:
        print(f"KEY FOUND in {leaks}; delete {run_dir} before committing", file=sys.stderr)
        return 3
    print(json.dumps({"run_dir": str(run_dir.relative_to(REPO)), "pi_exit": arm.returncode, "proxy_exit": proxy_exit}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3.8-27b:free"))
