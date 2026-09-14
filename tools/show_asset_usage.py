#!/usr/bin/env python3
"""Report which SSD assets a real Resolume show used, and what it could not decide.

Read-only over the composition files and the SSD index. Writes only into the
directory it is given, and every path it writes is anonymised.

    python3 tools/show_asset_usage.py \
        --composition "/media/mak/PortableSSD/DREFGIRA/IMPORT CLAUDIO/SHOWCAUPOLICAN FINAL ANTES DE CAUPO.avc" \
        --index /home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite \
        --out-dir /tmp/show_usage --orphans DREFGIRA
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

from flujo.venues.resolume_composition import (  # noqa: E402
    AMBIGUOUS, NOT_FOUND, RESOLVED_MULTI_LOCATION, RESOLVED_UNIQUE,
    index_asset_metadata, index_basenames, orphan_candidates,
    parse_composition, resolve_references, usage_report,
)


def _stable(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True)


def _slug(name: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in Path(name).stem)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "show"


def _html(reports: Sequence[dict], orphans: Sequence[dict]) -> str:
    blocks = []
    for report in reports:
        info = report["composicion"]
        counts = report["conteos"]
        rows = "".join(
            f"<tr class={r['estado']}><td>{html.escape(r['basename'])}</td>"
            f"<td>{r['estado']}</td>"
            f"<td>{html.escape(', '.join(r['assets_en_el_ssd'][:3]) or '-')}</td></tr>"
            for r in report["referencias"])
        limits = "".join(f"<li>{html.escape(x)}</li>" for x in report["limites"])
        used = "".join(f"<li>{html.escape(a)}</li>" for a in report["assets_usados"])
        blocks.append(
            f"<section><h2>{html.escape(info['composition_name'] or info['source_name'])}</h2>"
            f"<p class=meta>{html.escape(info['tool'])} &middot; lienzo "
            f"{info['lienzo_px']} &middot; {info['decks']} deck(s), "
            f"{info['layers']} capa(s), {info['columns']} columna(s) &middot; "
            f"{counts['referencias']} referencia(s)</p>"
            f"<p><b>{counts[RESOLVED_UNIQUE]}</b> resueltas sin ambiguedad "
            f"({report['tasa_resolucion_inequivoca']:.0%}), "
            f"<b>{counts[RESOLVED_MULTI_LOCATION]}</b> en copias duplicadas, "
            f"<b>{counts[AMBIGUOUS]}</b> ambiguas, "
            f"<b>{counts[NOT_FOUND]}</b> no encontradas. Contenedores tocados: "
            f"{html.escape(', '.join(report['contenedores_tocados']) or '-')}</p>"
            f"<h3>Assets usados</h3><ul>{used or '<li>ninguno resuelto</li>'}</ul>"
            f"<h3>Referencia por referencia</h3><table>"
            f"<tr><th>archivo citado</th><th>estado</th><th>asset(s) en el SSD</th></tr>"
            f"{rows}</table>"
            f"<h3>Limites</h3><ul>{limits}</ul></section>")
    for orphan in orphans:
        top = "".join(
            f"<li>{html.escape(o['asset'])} &mdash; {o['bytes']/1e9:.2f} GB</li>"
            for o in orphan["mayores_sin_referencia"])
        blocks.append(
            f"<section><h2>Candidatos sin referencia en "
            f"{html.escape(orphan['contenedor'])}</h2>"
            f"<p class=meta>{orphan['assets_en_el_contenedor']} asset(s); "
            f"{orphan['referenciados_por_una_composicion_leida']} referenciado(s) "
            f"por una composicion leida; {orphan['sin_referencia_conocida']} sin "
            f"referencia conocida ({orphan['bytes_sin_referencia']/1e9:.1f} GB)</p>"
            f"<p class=warn>{html.escape(orphan['advertencia'])}</p>"
            f"<ul>{top}</ul></section>")
    return (
        "<meta charset=utf-8><title>Uso de assets por show</title>"
        "<style>body{font:14px/1.5 system-ui,sans-serif;margin:2rem;max-width:64rem}"
        "h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:2rem}"
        "h3{font-size:.95rem;color:#555}table{border-collapse:collapse;margin:.5rem 0}"
        "td,th{border:1px solid #ccc;padding:.2rem .5rem;text-align:left;"
        "font-size:12px}.meta{color:#555}.warn{background:#fff6d5;padding:.5rem}"
        f"tr.{AMBIGUOUS}{{background:#fff2f2}}tr.{NOT_FOUND}{{color:#888}}</style>"
        "<h1>Que assets uso un show de verdad</h1>"
        "<p>Union por basename con abstencion explicita. Una coincidencia de "
        "nombre es candidata, no identidad de bytes.</p>" + "".join(blocks))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composition", action="append", default=[])
    parser.add_argument("--glob", default=None)
    parser.add_argument("--index", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--orphans", action="append", default=[],
                        help="container to list unreferenced candidates for")
    args = parser.parse_args(list(argv) if argv is not None else None)

    paths = [Path(p) for p in args.composition]
    if args.glob:
        paths.extend(Path(p) for p in sorted(globmod.glob(args.glob))
                     if not Path(p).name.startswith("._"))
    if not paths:
        parser.error("no input: pass --composition or --glob")

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    basenames = index_basenames(args.index)
    metadata = index_asset_metadata(args.index)

    reports, failed, used_all = [], [], set()
    for path in paths:
        try:
            record = parse_composition(path)
        except Exception as exc:
            failed.append({"file": str(path),
                           "error": f"{type(exc).__name__}: {exc}"})
            continue
        report = usage_report(
            record, resolve_references(record, basenames, metadata))
        reports.append(report)
        used_all.update(report["assets_usados"])
        (out_dir / f"{_slug(record.source_name)}.usage.json").write_text(
            _stable(report) + "\n", encoding="utf-8")

    orphans = [orphan_candidates(container, used_all, args.index)
               for container in args.orphans]
    for orphan in orphans:
        (out_dir / f"{_slug(orphan['contenedor'])}.orphans.json").write_text(
            _stable(orphan) + "\n", encoding="utf-8")
    (out_dir / "usage.html").write_text(_html(reports, orphans), encoding="utf-8")

    print(_stable({
        "schema": "mak-show-asset-usage-run-v1",
        "out_dir": str(out_dir),
        "index_basenames": len(basenames),
        "compositions": [
            {"file": r["composicion"]["source_name"],
             "name": r["composicion"]["composition_name"],
             "references": r["conteos"]["referencias"],
             RESOLVED_UNIQUE: r["conteos"][RESOLVED_UNIQUE],
             RESOLVED_MULTI_LOCATION: r["conteos"][RESOLVED_MULTI_LOCATION],
             AMBIGUOUS: r["conteos"][AMBIGUOUS],
             NOT_FOUND: r["conteos"][NOT_FOUND],
             "rate_unambiguous": r["tasa_resolucion_inequivoca"],
             "rate_clip_decided": r["tasa_clip_decidido"],
             "duplicated_copies": len(r["copias_duplicadas"]),
             "containers": r["contenedores_tocados"]}
            for r in reports],
        "assets_used_total": len(used_all),
        "orphan_containers": [
            {"container": o["contenedor"],
             "assets": o["assets_en_el_contenedor"],
             "referenced": o["referenciados_por_una_composicion_leida"],
             "unreferenced": o["sin_referencia_conocida"]}
            for o in orphans],
        "failed": failed,
    }))
    return 0 if reports else 1


if __name__ == "__main__":
    raise SystemExit(main())
