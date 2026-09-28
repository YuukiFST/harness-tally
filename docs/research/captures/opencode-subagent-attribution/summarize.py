"""Reduce each scenario capture to summary.json (issue #34).

    python docs/research/captures/opencode-subagent-attribution/summarize.py

Classifies every wire request with the header rule under test and checks it
against the session store read back by run.py:

- root session = X-Session-Id of the run's first request;
- a request is a child-session request iff its X-Session-Id differs from root;
- x-parent-session-id is recorded to show where it is and is not present.

Then compares, per session id, the wire prompt/completion sums with the native
rollup (`session.tokens_*`) and with the stdout `step_finish` events.
On this mock there is no cache or reasoning, so prompt = input, completion = output.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def summarize(out: Path) -> dict:
    reqs = [json.loads(line) for line in (out / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    reqs.sort(key=lambda r: r["seq"])
    root = reqs[0]["x_session_id"]
    wire: dict[str, dict] = defaultdict(lambda: {"requests": 0, "prompt": 0, "completion": 0, "kinds": []})
    rows = []
    for r in reqs:
        sid = r["x_session_id"]
        w = wire[sid]
        w["requests"] += 1
        w["prompt"] += r["usage_sent"]["prompt_tokens"]
        w["completion"] += r["usage_sent"]["completion_tokens"]
        w["kinds"].append(r["mock_kind"])
        rows.append({"seq": r["seq"], "class": "root" if sid == root else "child", "session": sid,
                     "parent_header": r["x_parent_session_id"], "mock_kind": r["mock_kind"],
                     "has_task_tool": "task" in r["tools"], "n_tools": len(r["tools"]),
                     "system_head": r["system_head"][:60]})
    sessions = json.loads((out / "db-sessions.json").read_text(encoding="utf-8"))
    native = {s["id"]: {"parent_id": s["parent_id"], "agent": s["agent"],
                        "input": s["tokens_input"], "output": s["tokens_output"]} for s in sessions}
    stdout = [json.loads(line) for line in (out / "stdout.jsonl").read_text(encoding="utf-8").splitlines() if line]
    stdout_sum = {"input": 0, "output": 0, "events": 0}
    for e in stdout:
        if e.get("type") == "step_finish":
            stdout_sum["events"] += 1
            stdout_sum["input"] += e["part"]["tokens"]["input"]
            stdout_sum["output"] += e["part"]["tokens"]["output"]
    per_session = {}
    for sid in sorted(set(wire) | set(native)):
        w, n = wire.get(sid), native.get(sid)
        per_session[sid] = {"wire": w, "native_rollup": n,
                            "rollup_equals_wire": bool(w and n and w["prompt"] == n["input"]
                                                       and w["completion"] == n["output"])}
    child_wire = [r for r in rows if r["class"] == "child"]
    return {
        "root_session": root,
        "requests": rows,
        "per_session": per_session,
        "stdout_step_finish": stdout_sum,
        "child_requests": len(child_wire),
        "child_requests_without_parent_header": sum(1 for r in child_wire if not r["parent_header"]),
        "root_requests_with_parent_header": sum(1 for r in rows if r["class"] == "root" and r["parent_header"]),
        "wire_prompt_total": sum(w["prompt"] for w in wire.values()),
        "native_rollup_input_total": sum(n["input"] for n in native.values()),
    }


def main() -> None:
    for out in sorted(p for p in HERE.iterdir() if (p / "requests.jsonl").exists()):
        summary = summarize(out)
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        mismatched = [sid for sid, v in summary["per_session"].items() if not v["rollup_equals_wire"]]
        print(json.dumps({"scenario": out.name, "child_requests": summary["child_requests"],
                          "child_without_parent_header": summary["child_requests_without_parent_header"],
                          "root_with_parent_header": summary["root_requests_with_parent_header"],
                          "wire_prompt_total": summary["wire_prompt_total"],
                          "native_rollup_input_total": summary["native_rollup_input_total"],
                          "stdout_input": summary["stdout_step_finish"]["input"],
                          "sessions_rollup_ne_wire": mismatched}))


if __name__ == "__main__":
    main()
