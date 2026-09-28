"""Fault-scripted OpenAI-compatible mock upstream for the #5 retry/usage survey.

One scenario per process. Every request that carries tool schemas (an agent
step) gets the scenario's response; a tool-less request (opencode's title call)
always gets a normal reply with its own distinctive usage, so it can be told
apart in the harness's native totals. Every request is logged as one JSON line
with arrival and completion times, so attempts and backoff gaps are read from
the log rather than from the harness.

Usage: python mock_upstream.py <scenario> <port> <log.jsonl>
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCENARIOS = (
    "ok",
    "no_finish",
    "no_usage",
    "usage_after_done",
    "r429",
    "r429_wrapped",
    "r500",
    "err200_json",
    "err200_sse",
    "disconnect",
)

MODEL = "MOCK-2.6B"
# Deliberately non-summing values: total_tokens=999 shows whether a harness
# passes the upstream total through or recomputes it.
STEP_USAGE = {
    "prompt_tokens": 137,
    "completion_tokens": 11,
    "total_tokens": 999,
    "prompt_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 7},
    "completion_tokens_details": {"reasoning_tokens": 3},
}
AUX_USAGE = {"prompt_tokens": 50, "completion_tokens": 2, "total_tokens": 52}
FREE_LIMIT_BODY = {"type": "FreeUsageLimitError", "message": "Rate limit exceeded. Please try again later."}
SERVER_ERROR_BODY = {"error": {"type": "server_error", "message": "Internal Server Error"}}
# Verbatim from harness-bench docs/research/11-second-free-model.md:577 (#31).
ERROR_200_BODY = {
    "error": {
        "type": "server_error",
        "message": "Error from provider (Console): Upstream request failed: [502] Upstream error from Nvidia: "
        "ResourceExhausted: Worker local total request limit reached (32/32)",
    }
}

T0 = time.monotonic()
LOCK = threading.Lock()
COUNTER = {"n": 0}


def now_ms() -> float:
    return round((time.monotonic() - T0) * 1000, 1)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    scenario = "ok"
    log_path = ""

    def log_message(self, *args) -> None:
        return

    def _log(self, record: dict) -> None:
        with LOCK:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")

    def do_GET(self) -> None:  # noqa: N802
        t = now_ms()
        body = json.dumps({"object": "list", "data": [{"id": MODEL, "object": "model", "owned_by": "mock"}]}).encode()
        self._plain(200, body)
        self._log({"t_in_ms": t, "t_out_ms": now_ms(), "method": "GET", "path": self.path})

    def do_POST(self) -> None:  # noqa: N802
        t_in = now_ms()
        raw = self.rfile.read(int(self.headers.get("content-length") or 0))
        body = json.loads(raw or b"{}")
        with LOCK:
            idx = COUNTER["n"]
            COUNTER["n"] += 1
        has_tools = bool(body.get("tools"))
        messages = body.get("messages") or []
        record = {
            "idx": idx,
            "t_in_ms": t_in,
            "method": "POST",
            "path": self.path,
            "kind": "step" if has_tools else "aux",
            "n_messages": len(messages),
            "max_tokens": body.get("max_tokens", body.get("max_completion_tokens")),
            "messages_hash": hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:16],
            "stream": body.get("stream"),
            "stream_options": body.get("stream_options"),
            "retry_headers": {k: v for k, v in self.headers.items() if "retry" in k.lower()},
        }
        action = self.scenario if has_tools else "aux_ok"
        record["action"] = action
        try:
            getattr(self, f"_do_{action}")(body)
            record["outcome"] = "sent"
        except Exception as exc:  # the harness may hang up first; record it, never lose the line
            record["outcome"] = f"exception: {exc!r}"
        record["t_out_ms"] = now_ms()
        self._log(record)

    # --- transport helpers -------------------------------------------------

    def _plain(self, status: int, raw: bytes, content_type: str = "application/json") -> None:
        # send_response_only: no Server/Date headers, so "no retry headers" is literal.
        self.send_response_only(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
        self.wfile.flush()

    def _sse_open(self) -> None:
        self.send_response_only(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("transfer-encoding", "chunked")
        self.end_headers()

    def _chunk(self, payload: str) -> None:
        data = payload.encode()
        self.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
        self.wfile.flush()

    def _frame(self, obj: dict | str) -> None:
        self._chunk("data: " + (obj if isinstance(obj, str) else json.dumps(obj)) + "\n\n")

    def _sse_close(self) -> None:
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()
        self.close_connection = True

    def _base(self) -> dict:
        return {"id": f"chatcmpl-{COUNTER['n']}", "object": "chat.completion.chunk", "created": int(time.time()), "model": MODEL}

    def _content(self, text: str = "done") -> None:
        self._frame({**self._base(), "choices": [{"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": None}]})

    def _finish(self) -> None:
        self._frame({**self._base(), "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})

    def _usage(self, usage: dict) -> None:
        self._frame({**self._base(), "choices": [], "usage": usage})

    # --- scenarios ---------------------------------------------------------

    def _do_aux_ok(self, body: dict) -> None:
        self._sse_open()
        self._content("Mock title")
        self._finish()
        self._usage(AUX_USAGE)
        self._frame("[DONE]")
        self._sse_close()

    def _do_ok(self, body: dict) -> None:
        self._sse_open()
        self._content()
        self._finish()
        self._usage(STEP_USAGE)
        self._frame("[DONE]")
        self._sse_close()

    def _do_no_finish(self, body: dict) -> None:
        self._sse_open()
        self._content()
        self._usage(STEP_USAGE)
        self._frame("[DONE]")
        self._sse_close()

    def _do_no_usage(self, body: dict) -> None:
        self._sse_open()
        self._content()
        self._finish()
        self._frame("[DONE]")
        self._sse_close()

    def _do_usage_after_done(self, body: dict) -> None:
        self._sse_open()
        self._content()
        self._finish()
        self._frame("[DONE]")
        self._usage(STEP_USAGE)
        self._sse_close()

    def _do_r429(self, body: dict) -> None:
        self._plain(429, json.dumps(FREE_LIMIT_BODY).encode())

    def _do_r429_wrapped(self, body: dict) -> None:
        # Control for r429: same body nested under "error", the shape the OpenAI SDK reads.
        self._plain(429, json.dumps({"error": FREE_LIMIT_BODY}).encode())

    def _do_r500(self, body: dict) -> None:
        self._plain(500, json.dumps(SERVER_ERROR_BODY).encode())

    def _do_err200_json(self, body: dict) -> None:
        self._plain(200, json.dumps(ERROR_200_BODY).encode())

    def _do_err200_sse(self, body: dict) -> None:
        self._sse_open()
        self._frame(ERROR_200_BODY)
        self._frame("[DONE]")
        self._sse_close()

    def _do_disconnect(self, body: dict) -> None:
        self._sse_open()
        self._content()
        # Abort mid-chunked-body: no terminating 0-chunk, RST instead of FIN.
        sock = self.connection
        linger = struct.pack("HH" if os.name == "nt" else "ii", 1, 0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
        self.close_connection = True
        sock.close()


def main() -> None:
    scenario, port, log_path = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    if scenario not in SCENARIOS:
        raise SystemExit(f"unknown scenario {scenario!r}; one of {SCENARIOS}")
    Handler.scenario = scenario
    Handler.log_path = log_path
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mock {scenario} on 127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
