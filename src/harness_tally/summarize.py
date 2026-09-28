"""Turn one run directory's `records.jsonl` into `summary.json`.

The session is the unit (harness-tally #43): refusals and interruptions are
expected, so nothing here discards. Every figure is a plain sum over records,
and every flag is counted so a reader can decide what to trust.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .proxy import COMPLETIONS_SUFFIX

SCHEMA = "harness-tally/summary/1"
TOKEN_FIELDS = {
    "input": "prompt_tokens",
    "cached": "cached_tokens",
    "cache_write": "cache_write_tokens",
    "output": "completion_tokens",
    "reasoning": "reasoning_tokens",
}


def load_records(out_dir: Path) -> list[dict[str, Any]]:
    path = out_dir / "records.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum a run's records.

        >>> summarize([])["requests"]["total"]
        0
    """
    completions = [r for r in records if r["method"] == "POST" and r["path"].split("?")[0].endswith(COMPLETIONS_SUFFIX)]
    answered = [r for r in completions if r["status"] is not None and 200 <= r["status"] < 300 and not r["error"]]
    steps = [r for r in answered if r["finish_reason"] and "upstream_disconnect" not in r["flags"]]
    tokens = {name: sum(r[field] or 0 for r in records) for name, field in TOKEN_FIELDS.items()}
    tokens["total"] = tokens["input"] + tokens["output"]
    run_ids = sorted({r["run_id"] for r in records})
    return {
        "schema": SCHEMA,
        "run_id": run_ids[0] if len(run_ids) == 1 else run_ids,
        "first_utc": min((r["utc"] for r in records), default=None),
        "last_utc": max((r["utc"] for r in records), default=None),
        "requests": {
            "total": len(records),
            "completions": len(completions),
            "answered": len(answered),
            "steps": len(steps),
            "refused": len(completions) - len(answered),
            "by_status": dict(sorted(Counter(str(r["status"]) for r in records).items())),
            "refused_by_limit_source": dict(
                sorted(Counter(str((r["error"] or {}).get("limit_source")) for r in completions if r not in answered).items())
            ),
        },
        "tokens": tokens,
        "cost": sum(r["cost"] or 0 for r in records),
        "tool_calls": sum(r["tool_calls"] for r in records),
        "models_echoed": dict(sorted(Counter(str(r["model_echoed"]) for r in answered).items())),
        "flags": dict(sorted(Counter(flag for r in records for flag in r["flags"]).items())),
    }


def write_summary(out_dir: Path) -> dict[str, Any]:
    summary = summarize(load_records(out_dir))
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary
