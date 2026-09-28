"""Recording mock OpenAI-compatible endpoint for the arm wire survey (issue #4).

Answers every request on 127.0.0.1, never forwards, and records what arrived:
request line, headers in arrival order with their original case, the raw body,
and arrival/finish times so overlapping requests are visible.

Agent-loop requests (non-empty `tools`) follow a two-step script: the first gets
a `read` tool call on the probe file, every later one gets a text reply.
Tool-less requests (titles, summaries) get a fixed short text and do not advance
the script. Modelled on harness-bench `layer1/src/hb_layer1/mock_server.py`.
"""

from __future__ import annotations

import gzip
import json
import threading
import time
import zlib
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_ID = "MOCK-2.6B"


@dataclass
class MockSettings:
    out_dir: Path
    probe_path: str
    # Held before answering so a concurrent request shows up as an overlap.
    reply_delay_s: float = 0.8
    # When set, every response reports this many prompt tokens, to push an arm
    # over its compaction threshold without sending a large conversation.
    forced_prompt_tokens: int | None = None
    # Limit the forced count to the first N agent steps; None forces it on every
    # response. OpenCode compacts after every overflowing step, so forcing it
    # everywhere loops forever (observed on 1.17.9).
    forced_steps: int | None = None


@dataclass
class _State:
    lock: threading.Lock = field(default_factory=threading.Lock)
    seq: int = 0
    agent_steps: int = 0
    inflight: int = 0
    max_inflight: int = 0
    t0: float = field(default_factory=time.monotonic)


def _decode_body(raw: bytes, encoding: str) -> bytes:
    if encoding == "gzip":
        return gzip.decompress(raw)
    if encoding == "deflate":
        return zlib.decompress(raw)
    return raw


def _fill_arguments(parameters: dict, probe_path: str) -> dict:
    args: dict = {}
    properties = parameters.get("properties") or {}
    for name in parameters.get("required") or []:
        spec = properties.get(name) or {}
        if spec.get("type") == "string":
            args[name] = probe_path if "path" in name.lower() else "x"
    return args


def _choose_tool(tools: list) -> tuple[str, dict]:
    functions = [t.get("function") or {} for t in tools]
    chosen = next((f for f in functions if f.get("name") == "read"), functions[0])
    return chosen["name"], chosen.get("parameters") or {}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # silence the stderr access log
        return

    @property
    def settings(self) -> MockSettings:
        return self.server.settings  # type: ignore[attr-defined]

    @property
    def state(self) -> _State:
        return self.server.state  # type: ignore[attr-defined]

    def _read_body(self) -> bytes:
        if (self.headers.get("transfer-encoding") or "").lower() == "chunked":
            chunks = []
            while True:
                size = int(self.rfile.readline().strip() or b"0", 16)
                if size == 0:
                    self.rfile.readline()
                    return b"".join(chunks)
                chunks.append(self.rfile.read(size))
                self.rfile.readline()
        return self.rfile.read(int(self.headers.get("content-length") or 0))

    def _begin(self) -> tuple[int, float, int]:
        with self.state.lock:
            seq = self.state.seq
            self.state.seq += 1
            self.state.inflight += 1
            self.state.max_inflight = max(self.state.max_inflight, self.state.inflight)
            return seq, time.monotonic() - self.state.t0, self.state.inflight

    def _finish(self, record: dict, started: float) -> None:
        with self.state.lock:
            self.state.inflight -= 1
        record["t_start_ms"] = round(started * 1000)
        record["t_end_ms"] = round((time.monotonic() - self.state.t0) * 1000)
        with (self.settings.out_dir / "requests.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def _base_record(self, seq: int, inflight: int) -> dict:
        return {
            "seq": seq,
            "request_line": self.requestline,
            "method": self.command,
            "path": self.path,
            "headers": [[k, v] for k, v in self.headers.items()],
            "inflight_at_arrival": inflight,
        }

    def do_GET(self) -> None:  # noqa: N802
        seq, started, inflight = self._begin()
        record = self._base_record(seq, inflight)
        if self.path.rstrip("/").endswith("/models"):
            self._send_json(200, {"object": "list", "data": [{"id": MODEL_ID, "object": "model"}]})
        else:
            self._send_json(404, {"error": {"message": f"no route {self.path}"}})
        self._finish(record, started)

    def do_POST(self) -> None:  # noqa: N802
        seq, started, inflight = self._begin()
        record = self._base_record(seq, inflight)
        raw = self._read_body()
        body_file = f"{seq:03d}-body.json"
        (self.settings.out_dir / body_file).write_bytes(raw)
        record["body_file"] = body_file
        record["body_bytes"] = len(raw)
        try:
            body = json.loads(_decode_body(raw, (self.headers.get("content-encoding") or "").lower()))
        except Exception as exc:  # a body we cannot parse is recorded, not fatal
            record["error"] = f"undecodable body: {exc}"
            self._send_json(400, {"error": {"message": record["error"]}})
            self._finish(record, started)
            return
        record.update(self._summarise(body))
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._send_json(404, {"error": {"message": f"no route {self.path}"}})
            self._finish(record, started)
            return
        reply = self._reply_for(body, record)
        time.sleep(self.settings.reply_delay_s)
        if body.get("stream"):
            self._send_stream(reply, record)
        else:
            self._send_json(200, self._completion(reply, record))
        self._finish(record, started)

    @staticmethod
    def _summarise(body: dict) -> dict:
        return {
            "body_keys": list(body.keys()),
            "stream": body.get("stream"),
            "stream_options": body.get("stream_options"),
            "max_tokens": body.get("max_tokens"),
            "max_completion_tokens": body.get("max_completion_tokens"),
            "n_tools": len(body.get("tools") or []),
            "n_messages": len(body.get("messages") or []),
        }

    def _reply_for(self, body: dict, record: dict) -> dict:
        tools = body.get("tools") or []
        if not tools:
            record["kind"] = "auxiliary"
            return {"kind": "text", "text": "Wire survey"}
        with self.state.lock:
            step = self.state.agent_steps
            self.state.agent_steps += 1
        record["kind"] = f"agent_step_{step}"
        if step > 0:
            return {"kind": "text", "text": "Done."}
        name, parameters = _choose_tool(tools)
        arguments = _fill_arguments(parameters, self.settings.probe_path)
        return {"kind": "tool", "name": name, "arguments": json.dumps(arguments)}

    def _forced(self, record: dict) -> int | None:
        limit = self.settings.forced_steps
        if limit is None:
            return self.settings.forced_prompt_tokens
        kind = record.get("kind", "")
        if kind.startswith("agent_step_") and int(kind.rsplit("_", 1)[1]) < limit:
            return self.settings.forced_prompt_tokens
        return None

    def _usage(self, record: dict) -> dict:
        prompt = self._forced(record) or max(1, record.get("body_bytes", 4) // 4)
        return {"prompt_tokens": prompt, "completion_tokens": 5, "total_tokens": prompt + 5}

    @staticmethod
    def _message(reply: dict) -> dict:
        if reply["kind"] == "text":
            return {"role": "assistant", "content": reply["text"]}
        call = {"id": "call_wire", "type": "function",
                "function": {"name": reply["name"], "arguments": reply["arguments"]}}
        return {"role": "assistant", "content": None, "tool_calls": [call]}

    def _completion(self, reply: dict, record: dict) -> dict:
        finish = "stop" if reply["kind"] == "text" else "tool_calls"
        return {
            "id": "chatcmpl-wire", "object": "chat.completion", "created": int(time.time()),
            "model": MODEL_ID,
            "choices": [{"index": 0, "message": self._message(reply), "finish_reason": finish}],
            "usage": self._usage(record),
        }

    def _send_json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_stream(self, reply: dict, record: dict) -> None:
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "close")
        self.end_headers()
        base = {"id": "chatcmpl-wire", "object": "chat.completion.chunk",
                "created": int(time.time()), "model": MODEL_ID}
        delta = self._message(reply)
        if "tool_calls" in delta:
            delta["tool_calls"][0]["index"] = 0
        finish = "stop" if reply["kind"] == "text" else "tool_calls"
        frames = [
            {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
            {**base, "choices": [], "usage": self._usage(record)},
        ]
        for frame in frames:
            self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True


class WireMock:
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

    def __enter__(self) -> "WireMock":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)
