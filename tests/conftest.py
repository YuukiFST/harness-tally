"""Fixtures: a stub gateway and the proxy started through its real CLI."""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest

from stub_upstream import StubUpstream

SRC = Path(__file__).resolve().parents[1] / "src"


@dataclass
class ProxyProcess:
    process: subprocess.Popen[bytes]
    ready: dict
    out: Path

    @property
    def port(self) -> int:
        return self.ready["port"]

    def post(self, model: str, headers: dict[str, str] | None = None, body: bytes | None = None) -> tuple[int, bytes]:
        payload = body if body is not None else json.dumps({"model": model, "stream": True, "max_completion_tokens": 64, "messages": [{"role": "user", "content": "hi"}]}).encode()
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.request("POST", "/chat/completions", body=payload, headers={"Content-Type": "application/json", **(headers or {})})
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, data

    def stop(self, timeout: float = 20) -> int:
        assert self.process.stdin is not None
        self.process.stdin.close()
        return self.process.wait(timeout)

    def records(self) -> list[dict]:
        return [json.loads(line) for line in (self.out / "records.jsonl").read_text(encoding="utf-8").splitlines()]


def start_proxy(upstream: str, out: Path, run_id: str = "run-1", extra: list[str] | None = None, env: dict[str, str] | None = None) -> subprocess.Popen[bytes]:
    cmd = [sys.executable, "-m", "harness_tally", "serve", "--upstream", upstream, "--run-id", run_id, "--out", str(out), *(extra or [])]
    full_env = {**os.environ, "PYTHONPATH": str(SRC), **(env or {})}
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=full_env)


def wait_ready(process: subprocess.Popen[bytes]) -> dict:
    assert process.stdout is not None
    line = process.stdout.readline()
    assert line, f"no ready line; stderr: {process.stderr.read() if process.stderr else b''!r}"
    return json.loads(line)


@pytest.fixture
def stub() -> Iterator[StubUpstream]:
    upstream = StubUpstream()
    upstream.start()
    yield upstream
    upstream.stop()


@pytest.fixture
def proxy(stub: StubUpstream, tmp_path: Path) -> Iterator[ProxyProcess]:
    out = tmp_path / "run"
    process = start_proxy(stub.url, out)
    running = ProxyProcess(process, wait_ready(process), out)
    yield running
    if process.poll() is None:
        running.stop()
