#!/usr/bin/env python3
"""Smoke test del hub local (`flujo app` / `flujo serve`).

Cubre los riesgos que más han roto el workflow:
- /api/ping responde con backend real.
- El servidor sigue respondiendo mientras /api/events (SSE) está abierto.
- No expone traversal ni archivos internos del repo (pyproject/src/.env/etc.).

Uso:
    py scripts/hub_smoke.py
    python3 scripts/hub_smoke.py --port 9876
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "_logs"


def _find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _http_get(host: str, port: int, path: str, timeout: float = 3.0) -> tuple[int, str]:
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        raw = resp.read(200_000)
        return int(resp.status), raw.decode("utf-8", errors="replace")
    finally:
        conn.close()


def _wait_for_ping(host: str, port: int, timeout: float) -> dict:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            status, body = _http_get(host, port, "/api/ping", timeout=1.5)
            if status == 200:
                data = json.loads(body)
                if data.get("status") == "ok":
                    return data
                last_error = f"bad ping payload: {body[:200]}"
            else:
                last_error = f"HTTP {status}: {body[:200]}"
        except Exception as exc:  # noqa: BLE001 - smoke diagnostic
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"Hub no respondió /api/ping en {timeout}s: {last_error}")


def _hold_sse(host: str, port: int, ready: threading.Event, errors: list[str], hold_seconds: float = 4.0) -> None:
    conn = http.client.HTTPConnection(host, port, timeout=10)
    try:
        conn.request("GET", "/api/events", headers={"Accept": "text/event-stream"})
        resp = conn.getresponse()
        if resp.status != 200:
            errors.append(f"SSE HTTP {resp.status}")
            ready.set()
            return
        ready.set()
        time.sleep(hold_seconds)
    except Exception as exc:  # noqa: BLE001 - smoke diagnostic
        errors.append(str(exc))
        ready.set()
    finally:
        conn.close()


def _assert_status(host: str, port: int, path: str, expected: set[int]) -> str:
    status, body = _http_get(host, port, path, timeout=3.0)
    if status not in expected:
        raise AssertionError(f"{path}: esperado {sorted(expected)}, recibido {status}. Body: {body[:200]}")
    return body


def run_smoke(port: int = 0, timeout: float = 30.0, sse: bool = True) -> None:
    host = "127.0.0.1"
    port = port or _find_free_port(host)
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"hub_smoke_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    cmd = [sys.executable, "-m", "flujo", "serve", "--host", host, "--port", str(port)]
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        try:
            ping = _wait_for_ping(host, port, timeout=timeout)
            version = ping.get("version", "?")

            # Path traversal + internal file disclosure guards.
            _assert_status(host, port, "/../../../../etc/passwd", {400, 403, 404})
            _assert_status(host, port, "/%2e%2e/pyproject.toml", {400, 403, 404})
            _assert_status(host, port, "/pyproject.toml", {400, 403, 404})
            _assert_status(host, port, "/src/flujo/cli.py", {400, 403, 404})

            if (ROOT / "projects" / "flujo" / "flujo.json").exists():
                _assert_status(host, port, "/projects/flujo/flujo.json", {200})

            if sse:
                ready = threading.Event()
                errors: list[str] = []
                thread = threading.Thread(target=_hold_sse, args=(host, port, ready, errors), daemon=True)
                thread.start()
                if not ready.wait(timeout=8):
                    raise RuntimeError("SSE no abrió a tiempo")
                if errors:
                    raise RuntimeError(f"SSE falló: {errors[0]}")
                # This catches accidental regressions to single-threaded HTTPServer.
                _assert_status(host, port, "/api/ping", {200})

            print(f"OK hub smoke: version={version} port={port} log={log_path}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test del hub local")
    parser.add_argument("--port", type=int, default=0, help="Puerto a usar (0 = libre automático)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Segundos máximos esperando /api/ping")
    parser.add_argument("--no-sse", action="store_true", help="No probar concurrencia con /api/events")
    args = parser.parse_args(argv)
    try:
        run_smoke(port=args.port, timeout=args.timeout, sse=not args.no_sse)
        return 0
    except Exception as exc:  # noqa: BLE001 - script diagnostic
        print(f"ERROR hub smoke: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
