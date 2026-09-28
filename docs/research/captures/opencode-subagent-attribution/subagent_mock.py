"""Recording mock that makes opencode 1.17.9 run a task subagent (issue #34).

Answers every request on 127.0.0.1, never forwards. Script, decided from the
request body only (never from headers, so the headers stay an observation):

- tools include `task` and no tool result is in the conversation yet:
  reply with the scenario's `task` tool call(s) (the parent's step 0);
- any other request with tools: reply with text (parent step 1, child steps);
- tool-less requests (title, compaction): reply with text.

Each response reports distinct usage (prompt 100*(seq+1)+7, completion seq+3)
so native records can be matched to wire requests one by one.
Records headers in arrival order, the raw body, tool names, the first system
message, arrival/finish times and the in-flight count.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_ID = "MOCK-2.6B"


@dataclass
class MockSettings:
    out_dir: Path
    # One dict per task call the parent's step 0 emits.
    task_calls: list[dict]
    reply_delay_s: float = 0.8
    # When set, the first request whose tools lack `task` (a child step) reports
    # this many prompt tokens, to push the child session into compaction.
    child_forced_prompt_tokens: int | None = None


@dataclass
class _State:
    lock: threading.Lock = field(default_factory=threading.Lock)
    seq: int = 0
    inflight: int = 0
    max_inflight: int = 0
    child_forced_done: bool = False
    t0: float = field(default_factory=time.monotonic)


def _tool_names(body: dict) -> list[str]:
    return sorted((t.get("function") or {}).get("name", "") for t in body.get("tools") or [])


def _first_system(body: dict) -> str:
    for m in body.get("messages") or []:
        if m.get("role") == "system":
            c = m.get("content")
            return c if isinstance(c, str) else json.dumps(c)
    return ""


def _first_user(body: dict) -> str:
    for m in body.get("messages") or []:
        if m.get("role") == "user":
            c = m.get("content")
            return c if isinstance(c, str) else json.dumps(c)
    return ""


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:
        return

    @property
    def settings(self) -> MockSettings:
        return self.server.settings  # type: ignore[attr-defined]

    @property
    def state(self) -> _State:
        return self.server.state  # type: ignore[attr-defined]

    def do_POST(self) -> None:  # noqa: N802
        with self.state.lock:
            seq = self.state.seq
            self.state.seq += 1
            self.state.inflight += 1
            self.state.max_inflight = max(self.state.max_inflight, self.state.inflight)
            inflight = self.state.inflight
            started = time.monotonic() - self.state.t0
        raw = self.rfile.read(int(self.headers.get("content-length") or 0))
        (self.settings.out_dir / f"{seq:03d}-body.json").write_bytes(raw)
        body = json.loads(raw)
        headers = [[k, v] for k, v in self.headers.items()]
        low = {k.lower(): v for k, v in headers}
        tools = _tool_names(body)
        has_tool_result = any(m.get("role") == "tool" for m in body.get("messages") or [])
        record = {
            "seq": seq,
            "path": self.path,
            "headers": headers,
            "x_session_id": low.get("x-session-id"),
            "x_session_affinity": low.get("x-session-affinity"),
            "x_parent_session_id": low.get("x-parent-session-id"),
            "user_agent": low.get("user-agent"),
            "tools": tools,
            "n_messages": len(body.get("messages") or []),
            "system_head": _first_system(body)[:160],
            "first_user_head": _first_user(body)[:160],
            "body_keys": list(body.keys()),
            "inflight_at_arrival": inflight,
        }
        usage = {"prompt_tokens": 100 * (seq + 1) + 7, "completion_tokens": seq + 3}
        if not tools:
            record["mock_kind"] = "toolless"
            reply = {"kind": "text", "text": "Mock summary"}
        elif "task" in tools and not has_tool_result:
            record["mock_kind"] = "parent_task_call"
            reply = {"kind": "tools", "calls": self.settings.task_calls}
        else:
            record["mock_kind"] = "text_step"
            reply = {"kind": "text", "text": "ok"}
            with self.state.lock:
                force = (self.settings.child_forced_prompt_tokens is not None and "task" not in tools
                         and not self.state.child_forced_done)
                if force:
                    self.state.child_forced_done = True
            if force:
                usage["prompt_tokens"] = self.settings.child_forced_prompt_tokens
                record["mock_kind"] = "child_step_forced_overflow"
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        record["usage_sent"] = usage
        time.sleep(self.settings.reply_delay_s)
        self._send_stream(reply, usage)
        with self.state.lock:
            self.state.inflight -= 1
        record["t_start_ms"] = round(started * 1000)
        record["t_end_ms"] = round((time.monotonic() - self.state.t0) * 1000)
        with (self.settings.out_dir / "requests.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def _send_stream(self, reply: dict, usage: dict) -> None:
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "close")
        self.end_headers()
        base = {"id": "chatcmpl-sub", "object": "chat.completion.chunk",
                "created": int(time.time()), "model": MODEL_ID}
        if reply["kind"] == "text":
            delta = {"role": "assistant", "content": reply["text"]}
            finish = "stop"
        else:
            delta = {"role": "assistant", "content": None, "tool_calls": [
                {"index": i, "id": f"call_task_{i}", "type": "function",
                 "function": {"name": "task", "arguments": json.dumps(call)}}
                for i, call in enumerate(reply["calls"])]}
            finish = "tool_calls"
        frames = [
            {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
            {**base, "choices": [], "usage": usage},
        ]
        for frame in frames:
            self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


class SubagentMock:
    """Recording mock on an ephemeral 127.0.0.1 port; use as a context manager."""

    def __init__(self, settings: MockSettings) -> None:
        settings.out_dir.mkdir(parents=True, exist_ok=True)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.settings = settings  # type: ignore[attr-defined]
        self.server.state = _State()  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def origin(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def max_inflight(self) -> int:
        return self.server.state.max_inflight  # type: ignore[attr-defined]

    def __enter__(self) -> "SubagentMock":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)
