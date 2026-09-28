"""Reduce every <arm>-<scenario>/ capture to one summary line (and summary.json).

Attempts and gaps come from the mock log only; the native view comes from the
arm's own stdout. Gap = next request arrival minus previous response end, in ms.

Usage: python summarize.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def mock_view(rows: list[dict]) -> dict:
    posts = [r for r in rows if r.get("method") == "POST"]
    steps = [r for r in posts if r["kind"] == "step"]
    gaps = [round(b["t_in_ms"] - a["t_out_ms"]) for a, b in zip(steps, steps[1:])]
    return {
        "step_requests": len(steps),
        "aux_requests": len([r for r in posts if r["kind"] == "aux"]),
        "distinct_step_hashes": len({r["messages_hash"] for r in steps}),
        "step_gaps_ms": gaps,
        "first_to_last_step_ms": round(steps[-1]["t_in_ms"] - steps[0]["t_in_ms"]) if steps else None,
        "stainless_retry_count": sorted({r["retry_headers"].get("X-Stainless-Retry-Count") for r in steps} - {None}),
    }


def pi_view(events: list[dict]) -> dict:
    ends = [e["message"] for e in events if e.get("type") == "message_end" and e["message"].get("role") == "assistant"]
    agent_ends = [e for e in events if e.get("type") == "agent_end"]
    final = agent_ends[-1] if agent_ends else {}
    final_assistants = [m for m in final.get("messages", []) if m.get("role") == "assistant"]
    return {
        "assistant_message_end": [
            {k: m["usage"].get(k) for k in ("input", "output", "cacheRead", "cacheWrite", "reasoning", "totalTokens")}
            | {"stopReason": m.get("stopReason"), "errorMessage": (m.get("errorMessage") or "")[:120]}
            for m in ends
        ],
        "agent_end_count": len(agent_ends),
        "agent_end_willRetry": [e.get("willRetry") for e in agent_ends],
        "final_agent_end_assistant_usage": [
            {k: m["usage"].get(k) for k in ("input", "output", "totalTokens")} for m in final_assistants
        ],
        "auto_retry_start": [
            {"attempt": e.get("attempt"), "maxAttempts": e.get("maxAttempts"), "delayMs": e.get("delayMs")}
            for e in events if e.get("type") == "auto_retry_start"
        ],
        "auto_retry_end": [
            {"success": e.get("success"), "attempt": e.get("attempt"), "finalError": (e.get("finalError") or "")[:120]}
            for e in events if e.get("type") == "auto_retry_end"
        ],
    }


def opencode_view(events: list[dict]) -> dict:
    return {
        "step_finish": [
            {"reason": e["part"].get("reason"), "tokens": e["part"].get("tokens")}
            for e in events if e.get("type") == "step_finish"
        ],
        "errors": [
            {"name": e["error"].get("name"), "message": str((e["error"].get("data") or {}).get("message"))[:160]}
            for e in events if e.get("type") == "error"
        ],
        "event_types": sorted({e.get("type") for e in events}),
    }


def main() -> None:
    for capture in sorted(p for p in HERE.iterdir() if (p / "meta.json").exists()):
        meta = json.loads((capture / "meta.json").read_text(encoding="utf-8"))
        events = read_jsonl(capture / "stdout.jsonl")
        view = pi_view(events) if meta["arm"] == "pi" else opencode_view(events)
        summary = {
            "arm": meta["arm"],
            "scenario": meta["scenario"],
            "exit_code": meta["exit_code"],
            "timed_out_after_s": meta["timed_out_after_s"],
            "mock": mock_view(read_jsonl(capture / "mock.jsonl")),
            "native": view,
        }
        (capture / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
