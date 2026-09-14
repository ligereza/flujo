#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Empty MAK's work queue while the paid window lasts, and count what came out.

The queue is the biggest thing this repo has and nobody was cashing it. Measured
on 2026-08-01: 2.730 pending tasks, most of them the RD triangulation -- "which
producer ran the event with these headliners on this date, with a verifiable
source". That is RD's actual product, sitting as text.

`trabajo.py` pops ONE task per invocation and runs on a cron, so the queue
drains at one task per cycle: months. This drains it in parallel for as long as
you tell it to, and STOPS on its own when the answers stop being worth the
tokens.

Three things it refuses to do, and each is a defect this repo already paid for:

1. **It does not write into the RD database.** Output goes to its own directory
   for a human to review. A producer identified by a model is a candidate, not
   a client.
2. **It stops when the searcher goes blind.** `research.py` already pauses per
   task; this counts those pauses and aborts the whole run when they pile up.
   Without that, a blocked searcher turns into hundreds of reports written from
   memory -- the exact thing the blindness detection exists to prevent.
3. **It reports the distribution, not a total.** "412 done" says nothing;
   "412 done, 180 with a producer and a source, 190 NO SE ENCONTRO, 42 paused
   blind" is the only shape that lets someone decide whether to keep going.

    python3 tools/drenar_material.py --lote 20            # sonda
    python3 tools/drenar_material.py --lote 500 --hilos 6
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

COLA = Path(os.path.expanduser("~/plataforma/material.jsonl"))
RESEARCH = Path(os.path.expanduser("~/research"))
SALIDA = Path(os.path.expanduser("~/curatoria/drenaje"))


def cargar(cola: Path) -> list[dict]:
    filas = []
    for linea in cola.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            filas.append(json.loads(linea))
        except ValueError:
            continue
    return filas


def guardar(cola: Path, filas: list[dict]) -> None:
    tmp = cola.with_suffix(".jsonl.drenaje.tmp")
    tmp.write_text("\n".join(json.dumps(f, ensure_ascii=False)
                             for f in filas) + "\n", encoding="utf-8")
    tmp.replace(cola)


def correr_tarea(tarea: dict, raiz: Path, salida: Path, timeout: int) -> dict:
    """One task. NEVER raises: one bad task cannot bring the drain down."""
    t0 = time.time()
    guion = "research.py" if tarea.get("depto") != "codex" else "generar.py"
    base = raiz / ("research" if guion == "research.py" else "codex")
    cmd = [sys.executable, str(base / guion), tarea["texto"]]
    if guion == "research.py":
        cmd += ["--iteraciones", "1", "--densidad", "corto",
                "--out", str(salida), "--providers", "groq,gemini,ollama"]
    else:
        cmd += ["--densidad", "corto"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout,
                           cwd=str(base))
    except subprocess.TimeoutExpired:
        return {"id": tarea["id"], "estado": "timeout", "seg": timeout}
    except OSError as e:
        return {"id": tarea["id"], "estado": "no_corrio", "detalle": str(e)[:120]}

    salida_txt = (r.stdout or "") + (r.stderr or "")
    # `research.py` exits 3 and prints PAUSADO when the search goes blind.
    # That is NOT a task failure: it is the system refusing to write a report
    # with no sources, and it has to be counted apart or the summary lies.
    if r.returncode == 3 or "PAUSADO:" in salida_txt:
        motivo = ""
        m = re.search(r"PAUSADO:.*?\|\s*(.+)", salida_txt)
        if m:
            motivo = m.group(1).strip()[:120]
        return {"id": tarea["id"], "estado": "pausada", "detalle": motivo,
                "seg": round(time.time() - t0, 1)}
    if r.returncode != 0:
        ultima = [l for l in salida_txt.strip().splitlines() if l.strip()]
        return {"id": tarea["id"], "estado": "fallo", "rc": r.returncode,
                "detalle": (ultima[-1][:140] if ultima else "sin salida"),
                "seg": round(time.time() - t0, 1)}

    informe = ""
    m = re.search(r"INFORME:\s*(\S+)", salida_txt)
    if m:
        informe = m.group(1)
    # Found or not. The triangulation prompt asks for exactly "NO SE
    # ENCONTRO" when there is no source, so that is what is read -- no prose
    # is interpreted.
    encontro = None
    if informe and Path(informe).exists():
        texto = Path(informe).read_text(encoding="utf-8", errors="replace")
        encontro = "NO SE ENCONTRO" not in texto.upper()
    return {"id": tarea["id"], "estado": "ok", "informe": informe,
            "encontro": encontro, "seg": round(time.time() - t0, 1)}


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lote", type=int, default=20,
                   help="cuantas tareas sacar de la cola")
    p.add_argument("--hilos", type=int, default=4)
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--depto", default="research", choices=("research", "codex"))
    p.add_argument("--cola", type=Path, default=COLA)
    p.add_argument("--raiz", type=Path, default=Path(os.path.expanduser("~")))
    p.add_argument("--salida", type=Path, default=SALIDA)
    p.add_argument("--tope-pausas", type=int, default=5,
                   dest="tope_pausas",
                   help="abortar si tantas tareas seguidas pausan por ceguera")
    a = p.parse_args()

    if not a.cola.exists():
        print("no existe la cola: %s" % a.cola, file=sys.stderr)
        return 2
    filas = cargar(a.cola)
    pendientes = [f for f in filas
                  if f.get("estado") == "pendiente" and f.get("depto") == a.depto]
    if not pendientes:
        print("no hay tareas pendientes de %s" % a.depto)
        return 0
    lote = pendientes[:a.lote]
    print("cola: %d filas | pendientes de %s: %d | este lote: %d"
          % (len(filas), a.depto, len(pendientes), len(lote)), flush=True)

    a.salida.mkdir(parents=True, exist_ok=True)
    por_id = {f["id"]: f for f in filas}
    for t in lote:
        por_id[t["id"]]["estado"] = "despachada"
    guardar(a.cola, filas)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max(1, a.hilos)) as ex:
        resultados = list(ex.map(
            lambda t: correr_tarea(t, a.raiz, a.salida, a.timeout), lote))

    conteo: dict[str, int] = {}
    for r in resultados:
        conteo[r["estado"]] = conteo.get(r["estado"], 0) + 1
    ok = [r for r in resultados if r["estado"] == "ok"]
    encontraron = sum(1 for r in ok if r.get("encontro"))
    pausadas = [r for r in resultados if r["estado"] == "pausada"]

    # Whatever paused or failed goes BACK to pending: marking it dispatched
    # would lose it, and a queue that empties without having worked is the
    # worst possible way of saying it finished.
    filas = cargar(a.cola)
    por_id = {f["id"]: f for f in filas}
    devueltas = 0
    for r in resultados:
        if r["estado"] in ("pausada", "fallo", "timeout", "no_corrio"):
            if r["id"] in por_id:
                por_id[r["id"]]["estado"] = "pendiente"
                devueltas += 1
    guardar(a.cola, filas)

    print()
    print("%d tareas en %.0f s (%.1f s por tarea con %d hilos)"
          % (len(lote), time.time() - t0,
             (time.time() - t0) / max(1, len(lote)), a.hilos))
    for estado, n in sorted(conteo.items(), key=lambda x: -x[1]):
        print("   %-10s %d" % (estado, n))
    if ok:
        print("   de las ok: %d con productora/fuente, %d dicen NO SE ENCONTRO"
              % (encontraron, len(ok) - encontraron))
    if devueltas:
        print("   %d volvieron a pendiente (pausadas o fallidas)" % devueltas)
    if pausadas:
        motivos: dict[str, int] = {}
        for r in pausadas:
            motivos[r.get("detalle") or "sin motivo"] = motivos.get(
                r.get("detalle") or "sin motivo", 0) + 1
        print("   motivos de pausa:")
        for motivo, n in sorted(motivos.items(), key=lambda x: -x[1])[:4]:
            print("      %3d  %s" % (n, motivo[:110]))
    (a.salida / "drenaje.jsonl").open("a", encoding="utf-8").write(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in resultados) + "\n")

    if len(pausadas) >= a.tope_pausas:
        print()
        print("!! %d tareas pausaron por ceguera: el buscador no esta sirviendo "
              "y seguir seria gastar tokens en aire" % len(pausadas),
              file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
