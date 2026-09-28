"""The measuring proxy: forward every request verbatim, write one record per request.

Rules this file keeps (spec 25 §8 as re-scoped by harness-tally #43):
- body bytes pass through untouched, in both directions;
- each upstream chunk reaches the client before a copy is parsed;
- `Accept-Encoding: identity` upstream, so the copy is parseable;
- an upstream disconnect aborts the client connection instead of ending it cleanly;
- every accepted request gets exactly one record, failures included.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .observe import USAGE_FIELDS, ResponseObserver

SCHEMA = "harness-tally/record/1"
COMPLETIONS_SUFFIX = "/chat/completions"
HOP_BY_HOP = frozenset(
    {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"}
)
READ_SIZE = 65536


@dataclass(frozen=True)
class Upstream:
    scheme: str
    host: str
    port: int
    base_path: str

    @classmethod
    def parse(cls, url: str) -> "Upstream":
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"--upstream must be an http(s) URL, got {url!r}")
        port = parts.port or (443 if parts.scheme == "https" else 80)
        return cls(parts.scheme, parts.hostname, port, parts.path.rstrip("/"))

    def connect(self) -> http.client.HTTPConnection:
        if self.scheme == "https":
            return http.client.HTTPSConnection(self.host, self.port)
        return http.client.HTTPConnection(self.host, self.port)

    @property
    def host_header(self) -> str:
        default = 443 if self.scheme == "https" else 80
        return self.host if self.port == default else f"{self.host}:{self.port}"


class RecordLog:
    """Append-only `records.jsonl` plus `bodies/<seq>.json`, safe across threads.

    A session may outlive one proxy process (the daily cap stops it, the next day
    resumes it), so an existing log of the same run is continued, never mixed
    with another run.
    """

    def __init__(self, out_dir: Path, run_id: str) -> None:
        self.out_dir = out_dir
        self.run_id = run_id
        self.bodies = out_dir / "bodies"
        self.path = out_dir / "records.jsonl"
        self._lock = threading.Lock()
        self._next_seq = self._resume()

    def _resume(self) -> int:
        self.bodies.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return 0
        last = -1
        for line in self.path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["run_id"] != self.run_id:
                raise ValueError(f"{self.path} belongs to run {record['run_id']!r}, not {self.run_id!r}")
            last = max(last, record["seq"])
        return last + 1

    def next_seq(self) -> int:
        with self._lock:
            seq, self._next_seq = self._next_seq, self._next_seq + 1
            return seq

    def save_body(self, seq: int, body: bytes) -> None:
        (self.bodies / f"{seq}.json").write_bytes(body)

    def write(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line)


@dataclass
class Exchange:
    """One request in flight; becomes exactly one record."""

    seq: int
    method: str
    path: str
    utc: str
    started: float
    request: dict[str, Any] = field(default_factory=dict)
    status: int | None = None
    ttfb: float | None = None
    observer: ResponseObserver | None = None
    flags: list[str] = field(default_factory=list)
    written: bool = False

    def to_record(self, run_id: str) -> dict[str, Any]:
        obs = self.observer
        usage = obs.usage if obs else {}
        flags = list(self.flags)
        is_completion = self.method == "POST" and self.path.split("?")[0].endswith(COMPLETIONS_SUFFIX)
        if self.status is not None and not 200 <= self.status < 300:
            flags.append("non_2xx")
        if obs and obs.error:
            flags.append("error_payload")
        if obs and obs.model_echoed and self.request.get("model_requested") and obs.model_echoed != self.request["model_requested"]:
            flags.append("model_substituted")
        if obs and obs.usage_after_done:
            flags.append("usage_after_done")
        ok = self.status is not None and 200 <= self.status < 300 and not (obs and obs.error)
        if is_completion and ok and "upstream_disconnect" not in flags:
            if usage.get("prompt_tokens") is None:
                flags.append("no_usage")
            if not (obs and obs.finish_reason):
                flags.append("missing_finish_reason")
        return {
            "schema": SCHEMA,
            "run_id": run_id,
            "seq": self.seq,
            "utc": self.utc,
            "method": self.method,
            "path": self.path,
            "status": self.status,
            **self.request,
            "model_echoed": obs.model_echoed if obs else None,
            "provider": obs.provider if obs else None,
            **{name: usage.get(name) for name in USAGE_FIELDS},
            "finish_reason": obs.finish_reason if obs else None,
            "tool_calls": obs.tool_calls if obs else 0,
            "error": obs.error if obs else None,
            "ttfb_s": None if self.ttfb is None else round(self.ttfb - self.started, 6),
            "duration_s": round(time.monotonic() - self.started, 6),
            "flags": flags,
        }


def describe_request(body: bytes, headers: Any) -> dict[str, Any]:
    """Request-side fields of the record. Reads the body, never rewrites it."""
    fields: dict[str, Any] = {
        "model_requested": None,
        "stream": None,
        "max_tokens": None,
        "client_session_id": headers.get("X-Session-Id"),
        "request_body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
    }
    try:
        parsed = json.loads(body) if body else None
    except ValueError:
        return fields
    if isinstance(parsed, dict):
        fields["model_requested"] = parsed.get("model")
        fields["stream"] = parsed.get("stream")
        # pi sends max_completion_tokens, opencode max_tokens (arm-wire-surface.md §3).
        fields["max_tokens"] = parsed.get("max_tokens", parsed.get("max_completion_tokens"))
    return fields


class TallyServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], upstream: Upstream, log: RecordLog, api_key: str | None) -> None:
        super().__init__(address, TallyHandler)
        self.upstream = upstream
        self.log = log
        self.api_key = api_key
        self.inflight: dict[int, Exchange] = {}
        self.inflight_lock = threading.Condition()

    def finish_exchange(self, exchange: Exchange) -> None:
        with self.inflight_lock:
            if exchange.written:
                return
            exchange.written = True
            self.inflight.pop(exchange.seq, None)
            self.inflight_lock.notify_all()
        self.log.write(exchange.to_record(self.log.run_id))

    def drain(self, timeout: float) -> bool:
        """Wait for handlers; flag and record the ones still running. True if none were cut."""
        deadline = time.monotonic() + timeout
        with self.inflight_lock:
            while self.inflight and time.monotonic() < deadline:
                self.inflight_lock.wait(deadline - time.monotonic())
            stuck = list(self.inflight.values())
        for exchange in stuck:
            exchange.flags.append("shutdown_in_flight")
            self.finish_exchange(exchange)
        return not stuck


class TallyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: TallyServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return  # stdout carries only the ready line; records are the log.

    def do_GET(self) -> None:
        self._proxy()

    do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_GET

    def _proxy(self) -> None:
        server = self.server
        exchange = Exchange(
            seq=server.log.next_seq(),
            method=self.command,
            path=self.path,
            utc=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            started=time.monotonic(),
        )
        with server.inflight_lock:
            server.inflight[exchange.seq] = exchange
        try:
            body = self._read_body()
            server.log.save_body(exchange.seq, body)
            exchange.request = describe_request(body, self.headers)
            self._forward(exchange, body)
        finally:
            server.finish_exchange(exchange)

    def _read_body(self) -> bytes:
        if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
            parts = []
            while True:
                size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                if size == 0:
                    while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    return b"".join(parts)
                parts.append(self.rfile.read(size))
                self.rfile.readline()
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _upstream_headers(self, body: bytes) -> dict[str, str]:
        server = self.server
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP | {"host", "content-length", "accept-encoding"}}
        headers["Host"] = server.upstream.host_header
        headers["Accept-Encoding"] = "identity"
        headers["Content-Length"] = str(len(body))
        if server.api_key is not None:
            for name in [k for k in headers if k.lower() == "authorization"]:
                del headers[name]
            headers["Authorization"] = f"Bearer {server.api_key}"
        return headers

    def _forward(self, exchange: Exchange, body: bytes) -> None:
        upstream = self.server.upstream
        conn = upstream.connect()
        try:
            conn.request(self.command, upstream.base_path + self.path, body=body, headers=self._upstream_headers(body))
            response = conn.getresponse()
        except OSError:
            # No response to relay: abort rather than invent one.
            exchange.flags.append("upstream_unreachable")
            self._abort_client()
            conn.close()
            return
        exchange.status = response.status
        exchange.ttfb = time.monotonic()
        is_sse = "text/event-stream" in (response.getheader("Content-Type") or "")
        exchange.observer = ResponseObserver(is_sse=is_sse)
        try:
            self._relay(exchange, response)
        finally:
            conn.close()

    def _relay(self, exchange: Exchange, response: http.client.HTTPResponse) -> None:
        length = response.getheader("Content-Length")
        chunked = length is None and self.command != "HEAD"
        self.send_response_only(response.status, response.reason)
        for name, value in response.getheaders():
            if name.lower() not in HOP_BY_HOP and name.lower() != "content-length":
                self.send_header(name, value)
        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        elif length is not None:
            self.send_header("Content-Length", length)
        self.end_headers()
        observer = exchange.observer
        assert observer is not None  # set by _forward just before
        while True:
            try:
                data = response.read1(READ_SIZE)
            except (OSError, http.client.HTTPException):
                exchange.flags.append("upstream_disconnect")
                self._abort_client()
                observer.finish()
                return
            if not data:
                break
            if not self._send(data, chunked):
                exchange.flags.append("client_disconnect")
                observer.feed(data)
                observer.finish()
                return
            observer.feed(data)
        observer.finish()
        if chunked:
            self._write(b"0\r\n\r\n")

    def _send(self, data: bytes, chunked: bool) -> bool:
        if chunked:
            return self._write(b"%x\r\n" % len(data) + data + b"\r\n")
        return self._write(data)

    def _write(self, data: bytes) -> bool:
        try:
            self.wfile.write(data)
            self.wfile.flush()
            return True
        except OSError:
            self.close_connection = True
            return False

    def _abort_client(self) -> None:
        # spec 25 §6.3: never end a truncated stream cleanly; the client must see an error.
        self.close_connection = True
        try:
            self.connection.shutdown(2)
        except OSError:
            pass

