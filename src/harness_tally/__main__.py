"""Command line: `python -m harness_tally serve|summarize`.

    python -m harness_tally serve --upstream https://openrouter.ai/api/v1 \\
        --run-id pi-build-01 --out runs/pi-build-01 --upstream-key-env OPENROUTER_API_KEY
    python -m harness_tally summarize runs/pi-build-01

`serve` prints one JSON ready line on stdout once the socket accepts, and stops
when stdin reaches EOF or on Ctrl-C. Exit codes: 0 clean, 1 start-up failure,
2 bad arguments, 3 drain timeout (records written, some flagged
`shutdown_in_flight`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path

from . import __version__
from .proxy import RecordLog, TallyServer, Upstream
from .summarize import write_summary


def _fail(message: str) -> int:
    print(json.dumps({"event": "error", "message": message}), file=sys.stderr, flush=True)
    return 1


def serve(args: argparse.Namespace) -> int:
    try:
        upstream = Upstream.parse(args.upstream)
    except ValueError as exc:
        return _fail(str(exc))
    api_key = None
    if args.upstream_key_env:
        api_key = os.environ.get(args.upstream_key_env, "")
        if not api_key:
            return _fail(f"environment variable {args.upstream_key_env} is unset or empty")
    try:
        log = RecordLog(Path(args.out), args.run_id)
        server = TallyServer((args.host, args.port), upstream, log, api_key)
    except (OSError, ValueError) as exc:
        return _fail(str(exc))
    port = server.server_address[1]
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    ready = {
        "event": "ready",
        "port": port,
        "base_url": f"http://{args.host}:{port}",
        "pid": os.getpid(),
        "run_id": args.run_id,
        "upstream_auth": "injected" if api_key is not None else "forwarded",
        "harness_tally_version": __version__,
    }
    print(json.dumps(ready), flush=True)
    stdin_closed = threading.Event()
    threading.Thread(target=lambda: (sys.stdin.buffer.read(), stdin_closed.set()), daemon=True).start()
    try:
        while not stdin_closed.wait(0.2):
            pass
    except KeyboardInterrupt:
        pass
    server.shutdown()
    clean = server.drain(args.drain_timeout)
    server.server_close()
    return 0 if clean else 3


def summarize(args: argparse.Namespace) -> int:
    summary = write_summary(Path(args.out))
    print(json.dumps(summary, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness_tally")
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("serve", help="run the measuring proxy")
    s.add_argument("--upstream", required=True, help="gateway base URL; request paths are appended verbatim")
    s.add_argument("--run-id", required=True, help="opaque id written on every record")
    s.add_argument("--out", required=True, help="run directory; an existing one of the same run is continued")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=0, help="0 picks a free port, reported in the ready line")
    s.add_argument("--upstream-key-env", help="inject Authorization from this environment variable")
    s.add_argument("--drain-timeout", type=float, default=30.0)
    s.set_defaults(func=serve)
    m = commands.add_parser("summarize", help="write summary.json for a run directory")
    m.add_argument("out")
    m.set_defaults(func=summarize)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
