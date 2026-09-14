#!/usr/bin/env python3
"""
El repo se toca a si mismo.

Lee el `git log` del repositorio y lo compone como un SET de VJ para Resolume:
cada commit es un golpe (un clip que se dispara), cada tipo de Conventional
Commit es una capa (layer), cada merge es un DROP. El ano entero de trabajo se
comprime a seis minutos -- el mismo gesto que FASE_2 del corpus Omega ("un ano
en seis minutos"). Nadie en la pista sabe que esta bailando la historia del
repo; vos si.

Salidas (todas en --out):
  - cue_sheet.json : las cues normalizadas (smpte, layer, clip, tipo, drop)
  - osc_cues.csv   : timecodes + mensajes OSC (formato real del repo)
  - osc_score.json : lista {t_segundos, address, args} lista para enviar a Resolume
  - timeline.html  : la partitura vista -- capas como pistas, drops como barras

Usa las convenciones OSC REALES del repo (flujo.resolume.automator.ShowCue:
/composition/layers/{layer}/clips/{clip}/connect, puerto 7000, 30 fps). No se
inventa el esquema.

    py tools/vj_set/git_performance.py --out tools/vj_set/out --duration 360
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Convenciones OSC reales del repo (no adivinar el esquema).
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))
from flujo.resolume.automator import ShowCue, write_osc_csv  # noqa: E402

# Conventional Commit type -> capa (deck) + color de la paleta flujo.
# El merge no es un tipo: es el DROP, capa 1, siempre.
TYPE_LAYER = {
    "merge": 1,
    "feat": 2,
    "fix": 3,
    "refactor": 4,
    "perf": 5,
    "chore": 6,
    "docs": 7,
    "test": 8,
    "style": 9,
    "build": 10,
    "ci": 10,
    "other": 11,
}
TYPE_COLOR = {
    "merge": "#f8f1e3",    # paper: el drop, lo mas brillante
    "feat": "#2d5a4a",     # accent (verde flujo): construir
    "fix": "#c2410f",      # alert (naranja): arreglar
    "refactor": "#675f55", # support
    "perf": "#8a9b6e",
    "chore": "#4a554e",
    "docs": "#a99f8e",
    "test": "#5f7a8a",
    "style": "#7a6e8a",
    "build": "#52525b",
    "ci": "#52525b",
    "other": "#3a4038",
}
_TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?!?:", re.IGNORECASE)
_UNIT = "\x1f"


def _commit_type(subject: str, n_parents: int) -> str:
    if n_parents >= 2:
        return "merge"
    m = _TYPE_RE.match(subject.strip())
    if m:
        t = m.group("type").lower()
        return t if t in TYPE_LAYER else "other"
    return "other"


def read_commits(limit: int | None, all_refs: bool) -> list[dict]:
    """git log -> lista de commits {hash, parents, t, subject, type} cronologica."""
    fmt = _UNIT.join(["%H", "%P", "%ct", "%s"])
    cmd = ["git", "log", f"--pretty=format:{fmt}"]
    if all_refs:
        cmd.append("--all")
    if limit is not None:
        cmd.append(f"-n{limit}")
    out = subprocess.run(
        cmd, cwd=str(_REPO_ROOT), capture_output=True, text=True, encoding="utf-8"
    )
    if out.returncode != 0:
        # An empty repository has no HEAD and no refs.  Check that state
        # directly instead of matching Git's localized diagnostic text.
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=str(_REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
        )
        refs = subprocess.run(
            ["git", "show-ref"], cwd=str(_REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8",
        )
        if head.returncode != 0 and not refs.stdout.strip():
            return []
        raise RuntimeError(f"git log fallo: {out.stderr.strip()}")
    commits = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        h, parents, ct, subject = line.split(_UNIT, 3)
        n_parents = len(parents.split()) if parents.strip() else 0
        commits.append({
            "hash": h,
            "short": h[:7],
            "parents": n_parents,
            "t": int(ct),
            "subject": subject,
            "type": _commit_type(subject, n_parents),
        })
    commits.sort(key=lambda c: c["t"])  # cronologico: el set corre hacia adelante
    return commits


def _smpte(seconds: float, fps: int = 30) -> str:
    total_f = round(seconds * fps)
    f = total_f % fps
    s = (total_f // fps) % 60
    m = (total_f // (fps * 60)) % 60
    h = total_f // (fps * 3600)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def compose(commits: list[dict], duration: float, fps: int = 30) -> list[dict]:
    """Comprime la linea real de commits al largo del set y arma las cues."""
    if not commits:
        return []
    t0, t1 = commits[0]["t"], commits[-1]["t"]
    span = max(1, t1 - t0)
    clip_counter: dict[int, int] = {}
    cues = []
    for c in commits:
        layer = TYPE_LAYER.get(c["type"], TYPE_LAYER["other"])
        # clip: cada golpe avanza la columna de su capa (max 8 columnas, cicla)
        clip_counter[layer] = clip_counter.get(layer, 0) + 1
        clip = ((clip_counter[layer] - 1) % 8) + 1
        pos = (c["t"] - t0) / span * duration
        cues.append({
            "t": round(pos, 3),
            "smpte": _smpte(pos, fps),
            "layer": layer,
            "clip": clip,
            "type": c["type"],
            "subject": c["subject"],
            "short": c["short"],
            "drop": c["type"] == "merge",
            "color": TYPE_COLOR.get(c["type"], TYPE_COLOR["other"]),
        })
    return cues


def write_outputs(cues: list[dict], out_dir: Path, duration: float, fps: int = 30) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) cue sheet
    (out_dir / "cue_sheet.json").write_text(
        json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2) osc_cues.csv con el writer real del repo (ShowCue = fuente de verdad OSC)
    show_cues = [
        ShowCue(title=f"{c['short']} {c['subject'][:48]}", smpte=c["smpte"],
                layer=c["layer"], clip=c["clip"])
        for c in cues
    ]
    write_osc_csv(show_cues, out_dir / "osc_cues.csv", fps=fps)

    # 3) osc_score.json: mensajes listos para enviar (connect = arg 1)
    score = [
        {"t": c["t"], "address": sc.osc_address(), "args": [1], "type": c["type"]}
        for c, sc in zip(cues, show_cues)
    ]
    (out_dir / "osc_score.json").write_text(
        json.dumps({"port": 7000, "fps": fps, "duration_s": duration, "messages": score},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 4) timeline.html
    (out_dir / "timeline.html").write_text(
        _timeline_html(cues, duration), encoding="utf-8"
    )


def _timeline_html(cues: list[dict], duration: float) -> str:
    W, pad = 1360, 24
    layers = sorted({c["layer"] for c in cues})
    lane_h = 34
    H = pad * 2 + len(layers) * lane_h + 40
    lane_y = {ly: pad + 30 + i * lane_h for i, ly in enumerate(layers)}
    inv_layer = {v: k for k, v in TYPE_LAYER.items()}

    def px(t):
        return pad + (t / max(1e-6, duration)) * (W - 2 * pad)

    marks = []
    # lineas de capa + etiqueta del tipo
    for ly in layers:
        y = lane_y[ly]
        name = inv_layer.get(ly, "?")
        marks.append(f'<line x1="{pad}" y1="{y}" x2="{W-pad}" y2="{y}" stroke="#2a2018"/>')
        marks.append(f'<text x="{pad}" y="{y-6}" fill="#6f665a" font-size="11" '
                     f'font-family="monospace">L{ly} {html.escape(name)}</text>')
    # golpes
    for c in cues:
        x = px(c["t"])
        y = lane_y[c["layer"]]
        if c["drop"]:
            top = pad + 24
            bot = pad + 24 + len(layers) * lane_h
            marks.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bot}" '
                         f'stroke="{c["color"]}" stroke-width="1.5" opacity="0.55"/>')
            marks.append(f'<circle cx="{x:.1f}" cy="{y}" r="5" fill="{c["color"]}"/>')
        else:
            marks.append(f'<rect x="{x-1.5:.1f}" y="{y-9}" width="3.4" height="18" '
                         f'rx="1" fill="{c["color"]}"/>')

    n_drops = sum(1 for c in cues if c["drop"])
    legend = " ".join(
        f'<span style="color:{TYPE_COLOR[t]}">&#9632; {t}</span>'
        for t in TYPE_LAYER if any(c["type"] == t for c in cues)
    )
    svg = (f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">'
           f'<rect width="{W}" height="{H}" fill="#14100c"/>{"".join(marks)}</svg>')
    mins = int(duration // 60)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>El repo se toca a si mismo</title>
<style>
  body{{margin:0;background:#0f0c09;color:#e8e0d2;font-family:system-ui,sans-serif;padding:28px}}
  .wrap{{max-width:1400px;margin:0 auto}}
  h1{{font-weight:600;letter-spacing:.02em;margin:0 0 4px}}
  p{{color:#a99f8e;line-height:1.5;max-width:900px}}
  .legend{{margin:14px 0;font:13px/1.8 monospace}}
  .board{{background:#14100c;border:1px solid #2a2018;border-radius:10px;overflow:hidden}}
</style></head><body><div class="wrap">
<h1>El repo se toca a si mismo</h1>
<p>La historia entera del repositorio comprimida a {mins} minutos y tocada como
un set de VJ para Resolume. {len(cues)} commits = {len(cues)} golpes; cada tipo
de commit es una capa; {n_drops} merges = {n_drops} drops (las barras claras).
El OSC real esta en <code>osc_score.json</code> / <code>osc_cues.csv</code>
(/composition/layers/N/clips/M/connect, puerto 7000). Nadie en la pista sabe que
esta bailando tu ano de trabajo.</p>
<div class="legend">{legend}</div>
<div class="board">{svg}</div>
</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Compone el git log como set de VJ para Resolume.")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"),
                    help="Directorio de salida")
    ap.add_argument("--duration", type=float, default=360.0,
                    help="Largo del set en segundos (default 360 = 6 min)")
    ap.add_argument("--fps", type=int, default=30, help="FPS para SMPTE")
    ap.add_argument("--limit", type=int, default=None, help="Maximo de commits")
    ap.add_argument("--all", action="store_true", help="Incluir todas las ramas (--all)")
    args = ap.parse_args()

    commits = read_commits(args.limit, args.all)
    if not commits:
        print("sin commits", file=sys.stderr)
        sys.exit(1)
    cues = compose(commits, args.duration, args.fps)
    out_dir = Path(args.out)
    write_outputs(cues, out_dir, args.duration, args.fps)
    n_drops = sum(1 for c in cues if c["drop"])
    print(f"set compuesto: {len(cues)} golpes, {n_drops} drops, {args.duration:.0f}s "
          f"-> {out_dir}/timeline.html (+ cue_sheet.json, osc_cues.csv, osc_score.json)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
