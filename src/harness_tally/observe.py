"""Read a copy of the response bytes and extract what the record needs.

The proxy forwards every byte first and only then feeds a copy here, so nothing
in this module can change what the client receives. It never repairs: a missing
field stays missing and becomes a flag on the record.
"""

from __future__ import annotations

import json
from typing import Any

USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "cached_tokens", "cache_write_tokens", "reasoning_tokens", "cost")


class ResponseObserver:
    """Accumulates facts about one response, SSE or plain JSON.

        >>> obs = ResponseObserver(is_sse=True)
        >>> obs.feed(b'data: {"model":"m","choices":[{"finish_reason":"stop"}],'
        ...          b'"usage":{"prompt_tokens":3,"completion_tokens":1}}\\n\\ndata: [DONE]\\n\\n')
        >>> obs.finish()
        >>> obs.usage["prompt_tokens"], obs.finish_reason, obs.saw_done
        (3, 'stop', True)
    """

    def __init__(self, is_sse: bool) -> None:
        self.is_sse = is_sse
        self._pending = b""
        self.model_echoed: str | None = None
        self.provider: str | None = None
        self.finish_reason: str | None = None
        self.usage: dict[str, int | float | None] = {}
        self.error: dict[str, Any] | None = None
        self.saw_done = False
        self.usage_after_done = False
        self.unparsed_frames = 0
        self._tool_call_ids: set[tuple[int, int]] = set()
        self._message_tool_calls = 0

    @property
    def tool_calls(self) -> int:
        return len(self._tool_call_ids) + self._message_tool_calls

    def feed(self, chunk: bytes) -> None:
        self._pending += chunk
        if not self.is_sse:
            return
        *lines, self._pending = self._pending.split(b"\n")
        for line in lines:
            self._sse_line(line.rstrip(b"\r"))

    def finish(self) -> None:
        """Parse whatever is left once the upstream body has ended."""
        rest, self._pending = self._pending, b""
        if self.is_sse:
            if rest.strip():
                self._sse_line(rest.rstrip(b"\r"))
            return
        if not rest.strip():
            return
        try:
            self._frame(json.loads(rest), after_done=False)
        except ValueError:
            self.unparsed_frames += 1

    def _sse_line(self, line: bytes) -> None:
        # SSE comment lines (": OPENROUTER PROCESSING") and blank separators carry no data.
        if not line.startswith(b"data:"):
            return
        payload = line[5:].strip()
        if payload == b"[DONE]":
            self.saw_done = True
            return
        try:
            frame = json.loads(payload)
        except ValueError:
            self.unparsed_frames += 1
            return
        self._frame(frame, after_done=self.saw_done)

    def _frame(self, frame: Any, after_done: bool) -> None:
        if not isinstance(frame, dict):
            return
        if "error" in frame and self.error is None:
            self.error = summarize_error(frame["error"])
        if self.model_echoed is None and isinstance(frame.get("model"), str):
            self.model_echoed = frame["model"]
        if self.provider is None and isinstance(frame.get("provider"), str):
            self.provider = frame["provider"]
        for choice in frame.get("choices") or []:
            self._choice(choice)
        if isinstance(frame.get("usage"), dict):
            self.usage = read_usage(frame["usage"])
            self.usage_after_done = self.usage_after_done or after_done

    def _choice(self, choice: Any) -> None:
        if not isinstance(choice, dict):
            return
        if choice.get("finish_reason"):
            self.finish_reason = choice["finish_reason"]
        index = choice.get("index", 0)
        delta = choice.get("delta") or {}
        for call in delta.get("tool_calls") or []:
            if isinstance(call, dict):
                self._tool_call_ids.add((index, call.get("index", 0)))
        message = choice.get("message") or {}
        self._message_tool_calls += len(message.get("tool_calls") or [])


def read_usage(usage: dict[str, Any]) -> dict[str, int | float | None]:
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "cache_write_tokens": prompt_details.get("cache_write_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "cost": usage.get("cost"),
    }


def summarize_error(error: Any) -> dict[str, Any]:
    """Keep what classifies a refusal; drop the account's `user_id` and prose."""
    if not isinstance(error, dict):
        return {"code": None, "message": str(error)[:200], "limit_source": None, "provider": None}
    metadata = error.get("metadata") or {}
    return {
        "code": error.get("code"),
        "message": str(error.get("message", ""))[:200],
        "limit_source": metadata.get("limit_source"),
        "provider": metadata.get("provider_name"),
    }
