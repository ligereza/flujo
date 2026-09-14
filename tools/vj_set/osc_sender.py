#!/usr/bin/env python3
"""
Dispara osc_score.json (salida de git_performance.py) como UDP OSC real hacia
Resolume Arena. Pieza MANIFIESTO #1: "el repo se performa a si mismo" -- este
modulo es la parte que faltaba, la que efectivamente TOCA Resolume.

osc_score.json (ver tools/vj_set/git_performance.py, write_outputs()) tiene la
forma:

    {"port": 7000, "fps": 30, "duration_s": 360.0,
     "messages": [{"t": 0.0, "address": "/composition/layers/1/clips/1/connect",
                    "args": [1], "type": "feat"}, ...]}

Los mensajes NO vienen ordenados por tiempo garantizado (compose() los emite
en orden cronologico de commit, que coincide con "t" creciente, pero no lo
asumimos: se ordenan aqui de nuevo antes de disparar). Direcciones OSC y
puerto se toman TAL CUAL del score -- nunca se inventan aca.

Uso:
    py tools/vj_set/osc_sender.py score.json --dry-run
    py tools/vj_set/osc_sender.py score.json --host 127.0.0.1 --port 7000
    py tools/vj_set/osc_sender.py score.json --speed 4 --desde 30
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from pathlib import Path
from typing import Any


def _pad4(data: bytes) -> bytes:
    """OSC strings/blobs are null-padded to the next 4-byte boundary, and the
    padding is ALWAYS at least one null byte (even if len(data) is already a
    multiple of 4)."""
    pad_len = 4 - (len(data) % 4)
    return data + b"\x00" * pad_len


def _osc_string(s: str) -> bytes:
    return _pad4(s.encode("utf-8"))


def encode_osc(address: str, *args: Any) -> bytes:
    """Encode one OSC 1.0 message: address, then typetag string, then args.

    Supported arg types: int -> 'i' (big-endian int32), float -> 'f'
    (big-endian float32), str -> 's' (null-padded OSC string). No external
    libs (stdlib struct only).
    """
    if not address.startswith("/"):
        raise ValueError(f"direccion OSC invalida (debe empezar con '/'): {address!r}")

    typetags = ","
    arg_bytes = b""
    for a in args:
        if isinstance(a, bool):
            # bool es subclase de int en Python; OSC 1.0 no tiene tipo bool
            # dedicado en este encoder minimo -- lo mandamos como int 0/1.
            typetags += "i"
            arg_bytes += struct.pack(">i", int(a))
        elif isinstance(a, int):
            typetags += "i"
            arg_bytes += struct.pack(">i", a)
        elif isinstance(a, float):
            typetags += "f"
            arg_bytes += struct.pack(">f", a)
        elif isinstance(a, str):
            typetags += "s"
            arg_bytes += _osc_string(a)
        else:
            raise TypeError(f"tipo de argumento OSC no soportado: {type(a)!r}")

    return _osc_string(address) + _osc_string(typetags) + arg_bytes


def load_score(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "messages" not in data:
        raise ValueError(f"{path}: no tiene 'messages' (no es un osc_score.json valido)")
    return data


def _fmt_args(args: list) -> str:
    return " ".join(repr(a) for a in args)


def run(
    score: dict,
    host: str,
    port_override: int | None,
    dry_run: bool,
    speed: float,
    desde: float,
) -> tuple[int, int]:
    """Dispara (o imprime, en --dry-run) las cues del score. Devuelve
    (enviados, restantes) -- restantes > 0 solo si hubo Ctrl-C."""
    messages = sorted(score.get("messages", []), key=lambda m: m["t"])
    messages = [m for m in messages if m["t"] >= desde]
    port = port_override if port_override is not None else int(score.get("port", 7000))

    sock: socket.socket | None = None
    if not dry_run:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sent = 0
    total = len(messages)
    try:
        t_prev = desde
        for msg in messages:
            t = msg["t"]
            address = msg["address"]
            args = msg["args"]
            delta = (t - t_prev) / max(speed, 1e-9)
            if delta > 0:
                time.sleep(delta)
            t_prev = t

            if dry_run:
                print(f"t={t:.3f} {address} {_fmt_args(args)}")
            else:
                packet = encode_osc(address, *args)
                assert sock is not None
                sock.sendto(packet, (host, port))
                print(f"t={t:.3f} -> {host}:{port} {address} {_fmt_args(args)}")
            sent += 1
    except KeyboardInterrupt:
        remaining = total - sent
        print(
            f"\ninterrumpido: {sent} cues enviadas, {remaining} restantes",
            file=sys.stderr,
        )
        return sent, remaining
    finally:
        if sock is not None:
            sock.close()

    return sent, 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Envia un osc_score.json (git_performance.py) como OSC UDP a Resolume."
    )
    ap.add_argument("score", type=Path, help="Ruta a osc_score.json")
    ap.add_argument("--host", default="127.0.0.1", help="Host OSC destino (default 127.0.0.1)")
    ap.add_argument(
        "--port", type=int, default=None,
        help="Puerto OSC destino (default: el 'port' del score, normalmente 7000)",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Solo imprime 't=<s> <address> <args>' por cue, sin abrir socket ni enviar nada",
    )
    ap.add_argument(
        "--speed", type=float, default=1.0,
        help="Multiplicador de velocidad de reproduccion (2.0 = el doble de rapido; para ensayo)",
    )
    ap.add_argument(
        "--desde", type=float, default=0.0,
        help="Saltar cues con t < DESDE segundos",
    )
    args = ap.parse_args()

    if args.speed <= 0:
        print("--speed debe ser > 0", file=sys.stderr)
        sys.exit(2)

    score = load_score(args.score)
    total = len([m for m in score.get("messages", []) if m["t"] >= args.desde])
    if total == 0:
        print("sin cues para disparar (score vacio o --desde despues de la ultima cue)",
              file=sys.stderr)
        sys.exit(1)

    mode = "DRY-RUN" if args.dry_run else f"UDP -> {args.host}:{args.port or score.get('port', 7000)}"
    print(f"[{mode}] {total} cues, speed={args.speed}x, desde={args.desde}s", file=sys.stderr)

    sent, remaining = run(score, args.host, args.port, args.dry_run, args.speed, args.desde)
    print(f"listo: {sent} enviadas, {remaining} restantes", file=sys.stderr)
    if remaining:
        sys.exit(130)  # convencion shell: 128 + SIGINT(2)


if __name__ == "__main__":
    main()
