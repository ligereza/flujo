"""
TAPIZ LIVE LOOP: daemon-style poller for the --live pipeline
Ecosystem: Tapiz <-> Psicosis <-> Fungi
Version: 1.0.0

Runs compete_engine.execute_pipeline(mode="live") in-process on a fixed
interval so the repo self-portrait (tools/dist/system_status.json) stays
fresh without any external scheduler (cron, Task Scheduler, etc). This is
the "poll del modo live como daemon" item from tools/TAPIZ.md.

Usage:
    py tools/tapiz_live_loop.py                       # loop every 300s
    py tools/tapiz_live_loop.py --interval 60          # loop every 60s
    py tools/tapiz_live_loop.py --once                 # single tick, exit
    py tools/tapiz_live_loop.py --out tools/dist_live   # custom output dir

Ctrl+C exits cleanly and prints a run summary. A single failing tick is
logged and the loop keeps going (a daemon should not die on one bad
tick); MAX_CONSECUTIVE_FAILURES failures in a row is treated as a stuck
pipeline and the process exits with code 1.

Stdlib only, no external deps.
"""
import argparse
import contextlib
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import compete_engine  # noqa: E402 -- path setup above must run first

DEFAULT_INTERVAL = 300.0
DEFAULT_OUT_DIR = TOOLS_DIR / "dist"
MAX_CONSECUTIVE_FAILURES = 3


def _harden_console():
    """Same pattern as compete_engine._harden_console: keep cp1252 Windows
    consoles alive when the pipeline (or our own status lines) touch
    non-ASCII asset names/content."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # non-reconfigurable stream (pipes, test capture) -- fine


def _run_tick(out_dir):
    """Runs one live-pipeline tick in-process and returns a summary dict.
    The pipeline's own chatty stdout (per-asset diagnostics) is captured
    and discarded so the daemon log stays one compact line per tick;
    exceptions propagate to the caller, which decides how to log/recover."""
    start = time.perf_counter()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        path = compete_engine.execute_pipeline(output_dir=str(out_dir), mode="live")
    duration = time.perf_counter() - start

    with open(path, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    pressure = matrix.get("luminous_mesh_densities", {}).get("global_pressure", 0.0)
    payload_count = matrix.get("encoded_asset_payloads", {}).get("total_payloads", 0)
    sigil = matrix.get("meta", {}).get("integrity_sigil", "")

    return {
        "path": path,
        "pressure": pressure,
        "payload_count": payload_count,
        "sigil_prefix": sigil[:12],
        "duration": duration,
    }


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_ok(tick_num, summary):
    return (
        f"[{_timestamp()}] tick={tick_num} pressure={summary['pressure']:.4f} "
        f"payloads={summary['payload_count']} sigil={summary['sigil_prefix']} "
        f"dur={summary['duration']:.2f}s"
    )


def _format_error(tick_num, exc):
    return f"[{_timestamp()}] tick={tick_num} ERROR: {exc}"


def run_loop(interval, once, out_dir):
    """Core loop: ticks until --once is satisfied, Ctrl+C is caught, or
    MAX_CONSECUTIVE_FAILURES is hit. Returns a process exit code."""
    out_dir = Path(out_dir)
    tick_num = 0
    ok_count = 0
    fail_count = 0
    consecutive_failures = 0
    exit_code = 0

    try:
        while True:
            tick_num += 1
            try:
                summary = _run_tick(out_dir)
                ok_count += 1
                consecutive_failures = 0
                print(_format_ok(tick_num, summary), flush=True)
            except Exception as exc:
                fail_count += 1
                consecutive_failures += 1
                print(_format_error(tick_num, exc), flush=True)
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(
                        f"ABORT: {consecutive_failures} consecutive tick "
                        "failures, giving up.",
                        file=sys.stderr, flush=True,
                    )
                    exit_code = 1
                    break

            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("", flush=True)
        print("Interrupted by user (Ctrl+C).", flush=True)

    print(
        f"Summary: ticks={tick_num} ok={ok_count} failed={fail_count} "
        f"out_dir={out_dir.resolve()}",
        flush=True,
    )
    return exit_code


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tapiz_live_loop",
        description="Poll the TAPIZ --live pipeline as a lightweight "
                     "in-process daemon (no external scheduler needed).",
    )
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL,
        help=f"seconds to sleep between ticks (default: {DEFAULT_INTERVAL:.0f})",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="run a single tick and exit (no sleep loop)",
    )
    parser.add_argument(
        "--out", metavar="DIR", default=str(DEFAULT_OUT_DIR),
        help=f"output directory for system_status.json (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(argv)

    if args.interval <= 0:
        parser.error("--interval must be > 0")

    _harden_console()
    return run_loop(args.interval, args.once, args.out)


if __name__ == "__main__":
    sys.exit(main())
