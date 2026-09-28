"""Regenerate the opencode subagent-attribution captures (issue #34).

    python docs/research/captures/opencode-subagent-attribution/run.py [scenario ...]

Each scenario runs opencode 1.17.9 against a fresh `subagent_mock.py` on
127.0.0.1 (no gateway), boxed like harness-bench `layer1/src/hb_layer1/arms.py`
(isolated profile) plus OPENCODE_DISABLE_MODELS_FETCH / _AUTOUPDATE, under
HB_SUB_SANDBOX (default C:/tmp/hbsub-sandbox, outside any git repo).
After the run it reads the isolated session store back with `opencode db`
and `opencode export`, using the same environment. Output lands next to this
file, one directory per scenario.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True
from subagent_mock import MODEL_ID, MockSettings, SubagentMock  # noqa: E402

HERE = Path(__file__).resolve().parent
ARMS_DIR = Path(os.environ.get("HB_ARMS_DIR", "C:/hbarms"))
SANDBOX_ROOT = Path(os.environ.get("HB_SUB_SANDBOX", "C:/tmp/hbsub-sandbox"))
PROVIDER_ID = "mockollama"
PROMPT = "Delegate one probe task to a subagent, then reply with the single word done."


def task(subagent: str, tag: str) -> dict:
    return {"description": f"probe {tag}", "prompt": f"SUBTASK-PROBE-{tag}: reply with ok",
            "subagent_type": subagent}


@dataclass
class Scenario:
    name: str
    task_calls: list[dict]
    title: str | None = "unit-01"
    child_forced_prompt_tokens: int | None = None


SCENARIOS = [
    # No --title, so the title side-call is on the wire next to the subagent.
    Scenario("task-general", [task("general", "A")], title=None),
    Scenario("task-explore", [task("explore", "B")]),
    Scenario("task-parallel", [task("general", "C"), task("explore", "D")]),
    Scenario("task-child-compaction", [task("general", "E")], child_forced_prompt_tokens=30000),
]

# Read back after each run with `opencode db <sql> --format json`.
DB_QUERIES = {
    "db-tables": "select name, sql from sqlite_master where type='table' order by name",
    "db-sessions": ("select id, parent_id, agent, title, tokens_input, tokens_output, tokens_reasoning,"
                    " tokens_cache_read, tokens_cache_write from session order by time_created"),
    "db-assistant-messages": (
        "select id, session_id, json_extract(data,'$.agent') as agent, json_extract(data,'$.mode') as mode,"
        " json_extract(data,'$.summary') as summary, json_extract(data,'$.tokens') as tokens"
        " from message where json_extract(data,'$.role')='assistant' order by time_created"),
    "db-step-finish": (
        "select session_id, message_id, json_extract(data,'$.tokens') as tokens from part"
        " where json_extract(data,'$.type')='step-finish' order by time_created"),
}


def isolated_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = env["USERPROFILE"] = str(home)
    for key, sub in (("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share"),
                     ("XDG_STATE_HOME", ".local/state"), ("XDG_CACHE_HOME", ".cache")):
        (home / sub).mkdir(parents=True, exist_ok=True)
        env[key] = str(home / sub)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    for key in ("TEMP", "TMP", "TMPDIR"):
        env[key] = str(home / "tmp")
    env["OPENCODE_DISABLE_MODELS_FETCH"] = "1"
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "1"
    return env


def opencode_bin() -> str:
    return str(ARMS_DIR / "node_modules" / "opencode-ai" / "bin" / "opencode.exe")


def opencode_config(base_url: str) -> dict:
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {PROVIDER_ID: {
            "npm": "@ai-sdk/openai-compatible", "name": "Subagent mock",
            "options": {"baseURL": base_url, "apiKey": "layer1", "timeout": 120000, "chunkTimeout": 60000},
            "models": {MODEL_ID: {"limit": {"context": 32768, "output": 4096}}}}},
        "model": f"{PROVIDER_ID}/{MODEL_ID}",
        "small_model": f"{PROVIDER_ID}/{MODEL_ID}",
        "permission": {"*": "allow", "external_directory": "deny", "question": "deny",
                       "webfetch": "deny", "websearch": "deny", "doom_loop": "deny"},
    }


def run_proc(command: list[str], env: dict[str, str], cwd: Path, timeout_s: int = 180):
    proc = subprocess.Popen(command, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        stdout, stderr = proc.communicate()
        return "timeout", stdout, stderr


def read_back(out: Path, env: dict[str, str], workspace: Path) -> dict:
    """Recover native usage from the isolated store after the run."""
    results = {}
    for name, sql in DB_QUERIES.items():
        code, stdout, stderr = run_proc([opencode_bin(), "db", sql, "--format", "json"], env, workspace, 60)
        (out / f"{name}.json").write_bytes(stdout)
        results[name] = code
        if stderr.strip():
            (out / f"{name}.stderr.txt").write_bytes(stderr)
    sessions = json.loads((out / "db-sessions.json").read_bytes() or b"[]")
    for s in sessions:
        code, stdout, stderr = run_proc([opencode_bin(), "export", s["id"]], env, workspace, 60)
        kind = "child" if s["parent_id"] else "root"
        (out / f"export-{kind}-{s['id']}.json").write_bytes(stdout)
        results[f"export-{s['id']}"] = code
    return results


def run(s: Scenario) -> dict:
    out = HERE / s.name
    shutil.rmtree(out, ignore_errors=True)
    sandbox = SANDBOX_ROOT / s.name
    shutil.rmtree(sandbox, ignore_errors=True)
    workspace = sandbox / "ws"
    workspace.mkdir(parents=True)
    (workspace / "hello.txt").write_text("subagent probe line\n", encoding="utf-8")
    env = isolated_env(sandbox / "home")
    settings = MockSettings(out_dir=out, task_calls=s.task_calls,
                            child_forced_prompt_tokens=s.child_forced_prompt_tokens)
    with SubagentMock(settings) as mock:
        config = opencode_config(mock.origin + "/v1")
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config)
        command = [opencode_bin(), "run", "--format", "json", "--dir", str(workspace), "--pure",
                   "-m", f"{PROVIDER_ID}/{MODEL_ID}", "--dangerously-skip-permissions"]
        if s.title is not None:
            command += ["--title", s.title]
        command.append(PROMPT)
        started = time.monotonic()
        code, stdout, stderr = run_proc(command, env, workspace)
        wall = time.monotonic() - started
        max_inflight = mock.max_inflight
    (out / "stdout.jsonl").write_bytes(stdout)
    (out / "stderr.txt").write_bytes(stderr)
    readback = read_back(out, env, workspace)
    meta = {"scenario": s.name, "command": ["opencode.exe", *command[1:]], "exit_code": code,
            "wall_s": round(wall, 2), "max_inflight": max_inflight, "task_calls": s.task_calls,
            "child_forced_prompt_tokens": s.child_forced_prompt_tokens, "readback_exit": readback,
            "provider_config": config}
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(names: list[str]) -> None:
    for s in SCENARIOS:
        if names and s.name not in names:
            continue
        meta = run(s)
        print(json.dumps({k: meta[k] for k in ("scenario", "exit_code", "wall_s", "max_inflight", "readback_exit")}),
              flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
