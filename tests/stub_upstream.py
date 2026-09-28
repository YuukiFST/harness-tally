"""A stub gateway that replays captured OpenRouter responses, chosen by model id.

Every request it receives is kept in `received` (headers and body bytes) so tests
compare the proxy against ground truth, not against a second observer.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CAPTURES = Path(__file__).resolve().parents[1] / "docs" / "research" / "captures" / "pool-availability" / "attempts"
BODY_MARKER = b"# ---- response body (raw bytes follow) ----"


def dechunk_capture(name: str) -> bytes:
    """Body bytes of a `curl --raw` capture, with the HTTP chunk framing removed."""
    raw = (CAPTURES / name).read_bytes()
    rest = raw[raw.index(BODY_MARKER) + len(BODY_MARKER) :].lstrip(b"\r\n")
    body = b""
    while True:
        size_line, rest = rest.split(b"\r\n", 1)
        size = int(size_line, 16)
        if size == 0:
            return body
        body, rest = body + rest[:size], rest[size + 2 :]


QWEN_OK = dechunk_capture("20260928T111037Z-qwen.txt")
GEMMA_OK = dechunk_capture("20260928T123159Z-gemma.txt")
POOL_429 = dechunk_capture("20260928T105022Z-qwen.txt")


@dataclass
class Scenario:
    status: int = 200
    content_type: str = "text/event-stream"
    body: bytes = b""
    cut_after: int | None = None  # reset the socket after this many body bytes


SCENARIOS: dict[str, Scenario] = {
    "qwen/qwen3.8-27b:free": Scenario(body=QWEN_OK),
    "google/gemma-4-31b-it:free": Scenario(body=GEMMA_OK),
    "stub/pool-429": Scenario(status=429, content_type="application/json", body=POOL_429),
    "stub/error-200": Scenario(
        body=b'data: {"id":"x","model":"stub/error-200","choices":[],"error":{"code":502,"message":"Upstream error"}}\n\ndata: [DONE]\n\n'
    ),
    "stub/substituted": Scenario(body=QWEN_OK),  # echoes qwen's id while stub/substituted was asked for
    "stub/disconnect": Scenario(body=QWEN_OK, cut_after=900),
    "stub/json": Scenario(
        content_type="application/json",
        body=json.dumps(
            {
                "model": "stub/json",
                "choices": [{"message": {"role": "assistant", "content": "ok", "tool_calls": [{"id": "a"}, {"id": "b"}]}, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
            }
        ).encode(),
    ),
    "stub/slow": Scenario(body=QWEN_OK),
}


@dataclass
class Received:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@dataclass
class StubUpstream:
    received: list[Received] = field(default_factory=list)
    slow_seconds: float = 0.0
    url: str = ""

    def start(self) -> str:
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: object) -> None:
                return

            def do_GET(self) -> None:
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                stub.received.append(Received(self.command, self.path, dict(self.headers.items()), body))
                if self.command == "GET":
                    payload = b'{"data":[{"id":"qwen/qwen3.8-27b:free"}]}'
                    self._reply(Scenario(content_type="application/json", body=payload), chunked=False)
                    return
                model = json.loads(body).get("model")
                if model == "stub/slow":
                    time.sleep(stub.slow_seconds)
                self._reply(SCENARIOS[model], chunked=True)

            do_POST = do_GET

            def _reply(self, scenario: Scenario, chunked: bool) -> None:
                self.send_response(scenario.status)
                self.send_header("Content-Type", scenario.content_type)
                self.send_header("Transfer-Encoding" if chunked else "Content-Length", "chunked" if chunked else str(len(scenario.body)))
                self.end_headers()
                if not chunked:
                    self.wfile.write(scenario.body)
                    return
                body = scenario.body if scenario.cut_after is None else scenario.body[: scenario.cut_after]
                for start in range(0, len(body), 300):
                    piece = body[start : start + 300]
                    self.wfile.write(b"%x\r\n" % len(piece) + piece + b"\r\n")
                    self.wfile.flush()
                if scenario.cut_after is not None:
                    # SO_LINGER 0: RST mid-body, as the #5 survey mock did.
                    linger = struct.pack("HH" if os.name == "nt" else "ii", 1, 0)
                    self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)
                    self.connection.close()
                    self.close_connection = True
                    return
                self.wfile.write(b"0\r\n\r\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/v1"
        return self.url

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
