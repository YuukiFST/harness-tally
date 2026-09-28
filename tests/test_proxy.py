"""Black-box tests: drive the proxy through its CLI against the stub gateway."""

from __future__ import annotations

import hashlib
import http.client
import json
import threading
from pathlib import Path
from typing import Callable

import pytest

from conftest import ProxyProcess, start_proxy, wait_ready
from stub_upstream import GEMMA_OK, POOL_429, QWEN_OK, StubUpstream


def test_ready_line_reports_a_bound_port(proxy: ProxyProcess) -> None:
    assert proxy.ready["event"] == "ready"
    assert proxy.ready["base_url"] == f"http://127.0.0.1:{proxy.port}"
    assert proxy.ready["upstream_auth"] == "forwarded"


@pytest.mark.parametrize(
    ("model", "body", "usage"),
    [
        ("qwen/qwen3.8-27b:free", QWEN_OK, (403, 37, 35, "ModelRun")),
        ("google/gemma-4-31b-it:free", GEMMA_OK, (127, 1, 0, "Google AI Studio")),
    ],
)
def test_captured_stream_passes_byte_exact_and_usage_is_recorded(
    proxy: ProxyProcess, stub: StubUpstream, model: str, body: bytes, usage: tuple
) -> None:
    status, received = proxy.post(model)
    assert proxy.stop() == 0
    assert status == 200
    assert received == body
    [record] = proxy.records()
    prompt, completion, reasoning, provider = usage
    assert (record["prompt_tokens"], record["completion_tokens"], record["reasoning_tokens"]) == (prompt, completion, reasoning)
    assert record["provider"] == provider
    assert record["model_requested"] == record["model_echoed"] == model
    assert record["finish_reason"] == "stop"
    assert record["flags"] == []
    assert record["cost"] == 0
    assert record["max_tokens"] == 64


def test_request_body_reaches_upstream_unchanged_and_is_archived(proxy: ProxyProcess, stub: StubUpstream) -> None:
    body = b'{"model":"qwen/qwen3.8-27b:free",  "stream":true,"messages":[{"role":"user","content":"\\u00e9"}]}'
    proxy.post("", body=body)
    proxy.stop()
    [record] = proxy.records()
    assert stub.received[0].body == body
    assert (proxy.out / "bodies" / "0.json").read_bytes() == body
    assert record["body_sha256"] == hashlib.sha256(body).hexdigest()
    assert record["request_body_bytes"] == len(body)


def test_upstream_sees_identity_encoding_its_own_host_and_the_base_path(proxy: ProxyProcess, stub: StubUpstream) -> None:
    proxy.post("qwen/qwen3.8-27b:free", headers={"Accept-Encoding": "gzip, br", "X-Custom": "kept"})
    proxy.stop()
    got = stub.received[0]
    headers = {k.lower(): v for k, v in got.headers.items()}
    assert got.path == "/api/v1/chat/completions"
    assert headers["accept-encoding"] == "identity"
    assert headers["host"] == stub.url.split("/")[2]
    assert headers["x-custom"] == "kept"


def test_pool_refusal_is_forwarded_and_recorded_with_its_limit_source(proxy: ProxyProcess) -> None:
    status, received = proxy.post("stub/pool-429")
    proxy.stop()
    assert status == 429
    assert received == POOL_429
    [record] = proxy.records()
    assert record["status"] == 429
    assert record["flags"] == ["non_2xx", "error_payload"]
    assert record["error"]["limit_source"] == "upstream_provider_shared_pool"
    assert record["error"]["provider"] == "ModelRun"
    assert "user_id" not in json.dumps(record)


def test_error_payload_inside_a_200_stream_is_flagged(proxy: ProxyProcess) -> None:
    status, _ = proxy.post("stub/error-200")
    proxy.stop()
    assert status == 200
    [record] = proxy.records()
    assert record["flags"] == ["error_payload"]
    assert record["error"]["code"] == 502


def test_model_substitution_is_flagged(proxy: ProxyProcess) -> None:
    proxy.post("stub/substituted")
    proxy.stop()
    [record] = proxy.records()
    assert record["model_echoed"] == "qwen/qwen3.8-27b:free"
    assert "model_substituted" in record["flags"]


def test_upstream_disconnect_aborts_the_client_and_still_writes_a_record(proxy: ProxyProcess) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", proxy.port)
    conn.request("POST", "/chat/completions", body=json.dumps({"model": "stub/disconnect", "stream": True}).encode())
    response = conn.getresponse()
    with pytest.raises((http.client.IncompleteRead, ConnectionError)):
        response.read()
    conn.close()
    proxy.stop()
    [record] = proxy.records()
    assert "upstream_disconnect" in record["flags"]
    assert record["finish_reason"] is None
    assert record["prompt_tokens"] is None


def test_non_streaming_json_response_is_parsed(proxy: ProxyProcess) -> None:
    status, _ = proxy.post("stub/json")
    proxy.stop()
    assert status == 200
    [record] = proxy.records()
    assert (record["prompt_tokens"], record["completion_tokens"], record["tool_calls"]) == (10, 4, 2)
    assert record["finish_reason"] == "tool_calls"
    assert record["flags"] == []


def test_get_is_forwarded_and_recorded_without_completion_flags(proxy: ProxyProcess) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", proxy.port)
    conn.request("GET", "/models")
    response = conn.getresponse()
    assert response.status == 200
    assert b"qwen" in response.read()
    conn.close()
    proxy.stop()
    [record] = proxy.records()
    assert (record["method"], record["path"], record["flags"]) == ("GET", "/models", [])


def test_session_id_header_is_recorded(proxy: ProxyProcess) -> None:
    proxy.post("qwen/qwen3.8-27b:free", headers={"X-Session-Id": "ses_abc"})
    proxy.post("qwen/qwen3.8-27b:free")
    proxy.stop()
    assert [r["client_session_id"] for r in proxy.records()] == ["ses_abc", None]


def test_concurrent_requests_each_get_one_record(proxy: ProxyProcess) -> None:
    threads = [threading.Thread(target=proxy.post, args=("qwen/qwen3.8-27b:free",)) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    proxy.stop()
    assert sorted(r["seq"] for r in proxy.records()) == list(range(6))


def test_injected_key_replaces_the_arm_key_and_never_reaches_disk(stub: StubUpstream, tmp_path: Path) -> None:
    sentinel = "sk-sentinel-1f2e3d4c5b6a"
    out = tmp_path / "run"
    process = start_proxy(stub.url, out, extra=["--upstream-key-env", "HT_TEST_KEY"], env={"HT_TEST_KEY": sentinel})
    proxy = ProxyProcess(process, wait_ready(process), out)
    assert proxy.ready["upstream_auth"] == "injected"
    proxy.post("qwen/qwen3.8-27b:free", headers={"Authorization": "Bearer harness-tally"})
    assert proxy.stop() == 0
    auth = [v for k, v in stub.received[0].headers.items() if k.lower() == "authorization"]
    assert auth == [f"Bearer {sentinel}"]
    for path in out.rglob("*"):
        if path.is_file():
            assert sentinel.encode() not in path.read_bytes(), path


def test_missing_key_env_exits_1_without_a_ready_line(stub: StubUpstream, tmp_path: Path) -> None:
    process = start_proxy(stub.url, tmp_path / "run", extra=["--upstream-key-env", "HT_TEST_UNSET"], env={"HT_TEST_UNSET": ""})
    stdout, stderr = process.communicate(timeout=20)
    assert process.returncode == 1
    assert stdout == b""
    assert json.loads(stderr)["event"] == "error"


def test_a_resumed_session_continues_the_same_log(stub: StubUpstream, tmp_path: Path) -> None:
    out = tmp_path / "run"
    for _ in range(2):
        process = start_proxy(stub.url, out, run_id="session-7")
        proxy = ProxyProcess(process, wait_ready(process), out)
        proxy.post("qwen/qwen3.8-27b:free")
        assert proxy.stop() == 0
    assert [(r["run_id"], r["seq"]) for r in proxy.records()] == [("session-7", 0), ("session-7", 1)]
    assert sorted(p.name for p in (out / "bodies").iterdir()) == ["0.json", "1.json"]


def test_a_log_of_another_run_is_refused(stub: StubUpstream, tmp_path: Path) -> None:
    out = tmp_path / "run"
    process = start_proxy(stub.url, out, run_id="a")
    proxy = ProxyProcess(process, wait_ready(process), out)
    proxy.post("qwen/qwen3.8-27b:free")
    proxy.stop()
    other = start_proxy(stub.url, out, run_id="b")
    stdout, _ = other.communicate(timeout=20)
    assert other.returncode == 1
    assert stdout == b""


def test_drain_timeout_records_the_request_in_flight(stub: StubUpstream, tmp_path: Path) -> None:
    stub.slow_seconds = 5
    out = tmp_path / "run"
    process = start_proxy(stub.url, out, extra=["--drain-timeout", "0.5"])
    proxy = ProxyProcess(process, wait_ready(process), out)
    threading.Thread(target=lambda: _swallow(proxy.post, "stub/slow"), daemon=True).start()
    while not stub.received:
        threading.Event().wait(0.05)
    assert proxy.stop() == 3
    [record] = proxy.records()
    assert "shutdown_in_flight" in record["flags"]


def _swallow(func: Callable[..., object], *args: object) -> None:
    try:
        func(*args)
    except OSError:
        pass
