"""Summaries built from records the proxy actually wrote."""

from __future__ import annotations

import json
import os
import subprocess
import sys

from conftest import SRC, ProxyProcess


def test_summary_sums_a_session_with_refusals(proxy: ProxyProcess) -> None:
    for model in ("qwen/qwen3.8-27b:free", "stub/pool-429", "google/gemma-4-31b-it:free", "stub/pool-429"):
        proxy.post(model)
    proxy.stop()
    result = subprocess.run(
        [sys.executable, "-m", "harness_tally", "summarize", str(proxy.out)],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
        check=True,
    )
    summary = json.loads((proxy.out / "summary.json").read_text(encoding="utf-8"))
    assert json.loads(result.stdout) == summary
    assert summary["run_id"] == "run-1"
    assert summary["requests"] == {
        "total": 4,
        "completions": 4,
        "answered": 2,
        "steps": 2,
        "refused": 2,
        "by_status": {"200": 2, "429": 2},
        "refused_by_limit_source": {"upstream_provider_shared_pool": 2},
    }
    assert summary["tokens"] == {"input": 530, "cached": 0, "cache_write": 0, "output": 38, "reasoning": 35, "total": 568}
    assert summary["models_echoed"] == {"google/gemma-4-31b-it:free": 1, "qwen/qwen3.8-27b:free": 1}
    assert summary["flags"] == {"error_payload": 2, "non_2xx": 2}
