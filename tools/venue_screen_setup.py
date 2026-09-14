#!/usr/bin/env python3
"""Read Resolume ScreenSetup files and emit venue projection records.

Read-only over the source files. Writes only into the directory it is given.

    python3 tools/venue_screen_setup.py --file "/media/mak/PortableSSD/CHILLAN.xml" \
        --out-dir /tmp/venue_projection
    python3 tools/venue_screen_setup.py --glob "/media/mak/PortableSSD/*.xml" \
        --out-dir /tmp/venue_projection --index
"""
from __future__ import annotations

import argparse
import glob as globmod
import html
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from flujo.venues.resolume_screen_setup import (  # noqa: E402
    parse_screen_setup, rig_index, to_payload,
)


def _stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True)


def _slug(name: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in Path(name).stem]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "venue"


def _html_view(payloads: Sequence[dict], index: dict | None) -> str:
    """A page a person can read next to the original files."""
    rows = []
    for payload in payloads:
        summary = payload["resumen"]
        surfaces = "".join(
            f"<tr><td>{html.escape(str(s['nombre']) or '(sin nombre)')}</td>"
            f"<td>{'si' if s['habilitada'] else 'no'}</td>"
            f"<td>{s['salida_px']['ancho']:.0f}&times;{s['salida_px']['alto']:.0f}</td>"
            f"<td>{s['warp']}</td></tr>"
            for s in payload["superficies"])
        residues = "".join(f"<li>{html.escape(r['descripcion'])}</li>"
                           for r in payload["residuos"])
        rows.append(
            f"<section><h2>{html.escape(summary['source_name'])}</h2>"
            f"<p class=meta>{html.escape(summary['tool'])} &middot; lienzo "
            f"{summary['lienzo_px']} &middot; {summary['pantallas']} pantalla(s) "
            f"&middot; {summary['superficies']} superficie(s), "
            f"{summary['superficies_habilitadas']} habilitada(s) &middot; "
            f"{summary['superficies_planas']} plana(s) / "
            f"{summary['superficies_deformadas']} deformada(s) &middot; "
            f"{summary['dmx_slices']} DMX</p>"
            f"<p class=ident>identidad de sala: candidato "
            f"<b>{html.escape(payload['identidad_sala']['candidato'])}</b>, estado "
            f"{payload['identidad_sala']['estado']} &mdash; "
            f"{html.escape(payload['identidad_sala']['regla'])}</p>"
            f"<table><tr><th>superficie</th><th>habilitada</th>"
            f"<th>salida px</th><th>warp</th></tr>{surfaces}</table>"
            f"<h3>Residuos: lo que este archivo NO prueba</h3><ul>{residues}</ul>"
            f"</section>")
    index_block = ""
    if index:
        relations = "".join(
            f"<li><b>{html.escape(r['left'])}</b> &harr; "
            f"<b>{html.escape(r['right'])}</b>: {r['relation']} "
            f"[{r['epistemic_status']}], {r['identifying_surfaces']} superficie(s) "
            f"nombradas por el operador coinciden"
            + ("<ul>" + "".join(f"<li>en contra: {html.escape(e)}</li>"
                                for e in r.get('evidence_against', [])) + "</ul>"
               if r.get("evidence_against") else "")
            + "</li>"
            for r in index["relations"])
        index_block = (
            f"<section><h2>Rigs compartidos entre shows</h2>"
            f"<p class=meta>{index['files']} archivo(s), "
            f"{index['distinct_topologies']} topologia(s) distinta(s)</p>"
            f"<ul>{relations or '<li>ninguna relacion sostenida por evidencia</li>'}"
            f"</ul></section>")
    return (
        "<meta charset=utf-8><title>Proyeccion de salas</title>"
        "<style>body{font:14px/1.5 system-ui,sans-serif;margin:2rem;max-width:60rem}"
        "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}"
        "h3{font-size:.95rem;color:#555}table{border-collapse:collapse;margin:.5rem 0}"
        "td,th{border:1px solid #ccc;padding:.2rem .5rem;text-align:left}"
        ".meta,.ident{color:#555}li{margin:.2rem 0}</style>"
        "<h1>Topologia de proyeccion medida</h1>"
        "<p>Pixeles, no metros. Ninguna dimension fisica, carga ni altura de "
        "cuelgue se deriva de estos archivos.</p>"
        + index_block + "".join(rows))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", default=[],
                        help="one ScreenSetup file; repeatable")
    parser.add_argument("--glob", default=None,
                        help="shell glob of ScreenSetup files")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--index", action="store_true",
                        help="also relate the files by measured rig topology")
    args = parser.parse_args(list(argv) if argv is not None else None)

    paths = [Path(p) for p in args.file]
    if args.glob:
        paths.extend(Path(p) for p in sorted(globmod.glob(args.glob))
                     if not Path(p).name.startswith("._"))
    if not paths:
        parser.error("no input: pass --file or --glob")

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    records, payloads, failed = [], [], []
    for path in paths:
        try:
            record = parse_screen_setup(path)
        except Exception as exc:  # a bad file is reported, never guessed at
            failed.append({"file": str(path), "error": f"{type(exc).__name__}: {exc}"})
            continue
        records.append(record)
        payload = to_payload(record)
        payloads.append(payload)
        (out_dir / f"{_slug(record.source_name)}.projection.json").write_text(
            _stable(payload) + "\n", encoding="utf-8")

    index = rig_index(records) if args.index and len(records) > 1 else None
    if index:
        (out_dir / "rig_index.json").write_text(_stable(index) + "\n",
                                                encoding="utf-8")
    (out_dir / "projection.html").write_text(_html_view(payloads, index),
                                             encoding="utf-8")

    result = {
        "schema": "mak-venue-projection-run-v1",
        "out_dir": str(out_dir),
        "parsed": len(payloads),
        "failed": failed,
        "venues": [
            {"file": p["resumen"]["source_name"],
             "identity_candidate": p["identidad_sala"]["candidato"],
             "identity_status": p["identidad_sala"]["estado"],
             "surfaces": p["resumen"]["superficies"],
             "operator_named": sum(
                 1 for s in p["superficies"]
                 if s["nombre"] and not s["nombre"].lower().startswith("slice")),
             "warped": p["resumen"]["superficies_deformadas"],
             "canvas": p["resumen"]["lienzo_px"]}
            for p in payloads],
        **({"rig_relations": index["relations"],
            "distinct_topologies": index["distinct_topologies"]} if index else {}),
    }
    print(_stable(result))
    return 0 if payloads else 1


if __name__ == "__main__":
    raise SystemExit(main())
