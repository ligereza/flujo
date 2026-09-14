"""Informe trimestral + resumen JSON sobre la DB de datos de campo RD (F3b).

Consume las agregaciones puras de `flujo.rd.datos` (tendencias,
tasa_adulteracion, atenciones_por_tipo) y las renderiza a markdown, siguiendo
el patron de separacion datos/render de `flujo.dashboard` (`scoring.py` ->
datos, `report.py` -> render). ASCII puro en toda salida generada.

Todo dato en `data/rd_datos_demo/` es DEMO/FICTICIO (ver F3a, PR #157): no
existe todavia ningun dato real de terreno RD. El DISCLAIMER de este modulo
lo deja explicito en cada informe y en el resumen JSON del hub.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from ..privacy import scan_text
from .datos import (
    DEFAULT_DB_PATH,
    atenciones_por_tipo,
    conectar,
    tasa_adulteracion,
    tendencias,
)

DISCLAIMER = (
    "DISCLAIMER OBLIGATORIO: los resultados de reactivos colorimetricos son "
    "PRESUNTIVOS, no confirmatorios -- indican familia posible de sustancia, "
    "NO identifican ni miden pureza. Un color no vuelve segura una "
    "sustancia. Los datos de este informe son DEMO/FICTICIOS: no existe "
    "todavia ningun dato real de terreno RD (pendiente acta de entrega)."
)


def _tabla_markdown(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    headers = list(headers)
    lineas = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    tiene_filas = False
    for fila in rows:
        tiene_filas = True
        lineas.append("| " + " | ".join(str(c) for c in fila) + " |")
    if not tiene_filas:
        lineas.append("| " + " | ".join("(sin datos)" for _ in headers) + " |")
    return "\n".join(lineas)


def informe_trimestral(
    db_path: str | Path | None = None, trimestre: str | None = None
) -> str:
    """Genera el informe trimestral en markdown: disclaimer obligatorio +
    3 tablas (tendencias por sustancia/mes, tasa de no-coincidencia por
    sustancia, atenciones por tipo). `trimestre` opcional ('YYYY-Q1'..
    'YYYY-Q4') filtra el rango; None = todo el historico de la DB."""
    conn = conectar(db_path)
    try:
        tend = tendencias(conn, trimestre=trimestre)
        tasa = tasa_adulteracion(conn, trimestre=trimestre)
        atp = atenciones_por_tipo(conn, trimestre=trimestre)
    finally:
        conn.close()

    titulo = "Informe trimestral RD -- datos de campo"
    if trimestre:
        titulo += f" ({trimestre})"

    lineas: list[str] = [f"# {titulo}", "", DISCLAIMER, ""]

    lineas.append("## Tendencias por sustancia declarada y mes")
    lineas.append("")
    lineas.append(
        _tabla_markdown(
            ["mes", "sustancia declarada", "conteo"],
            [(r["mes"], r["sustancia_declarada"], r["conteo"]) for r in tend],
        )
    )
    lineas.append("")

    lineas.append("## Tasa de no-coincidencia por sustancia declarada")
    lineas.append("")
    lineas.append(
        "Nota: 'no coincide' = el reactivo NO confirmo la sustancia "
        "declarada por la persona (presuntivo, no es medicion de pureza)."
    )
    lineas.append("")
    lineas.append(
        _tabla_markdown(
            ["sustancia declarada", "no coincide", "total", "tasa"],
            [
                (r["sustancia_declarada"], r["no_coincide"], r["total"], f"{r['tasa']:.2f}")
                for r in tasa
            ],
        )
    )
    lineas.append("")

    lineas.append("## Atenciones por tipo")
    lineas.append("")
    lineas.append(
        _tabla_markdown(
            ["tipo", "conteo"],
            [(r["tipo"], r["conteo"]) for r in atp],
        )
    )
    lineas.append("")

    return "\n".join(lineas)


def resumen_json(db_path: str | Path | None = None) -> dict[str, Any]:
    """Resumen JSON compacto para el endpoint del hub
    (GET /api/rd-datos-summary): totales por tabla, tasa de no-coincidencia
    global y fecha del ultimo ingest. Si la DB de datos de campo todavia no
    existe (nada ingerido) retorna `{"disponible": False}` -- NUNCA lanza,
    y NUNCA crea el archivo como efecto secundario de una lectura. Un
    archivo presente pero corrupto/no-sqlite tambien degrada a
    `{"disponible": False, "error": ...}` en vez de propagar (el hub NUNCA
    debe devolver 500 por este endpoint)."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    # A GET summary must never create the field-data database as a side effect.
    # `conectar()` is intentionally schema-creating for ingestion, so this
    # reader opens an existing, non-empty SQLite file in URI read-only mode.
    if not path.exists() or path.stat().st_size == 0:
        return {"disponible": False}

    try:
        conn = sqlite3.connect(
            "file:" + str(path.resolve()) + "?mode=ro", uri=True
        )
        try:
            total_testeos = conn.execute(
                "SELECT COUNT(*) FROM registros_testeo"
            ).fetchone()[0]
            total_atenciones = conn.execute(
                "SELECT COUNT(*) FROM atenciones"
            ).fetchone()[0]
            total_encuestas = conn.execute(
                "SELECT COUNT(*) FROM encuestas"
            ).fetchone()[0]
            no_coincide, con_resultado = conn.execute(
                "SELECT SUM(CASE WHEN coincide = 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN coincide IS NOT NULL THEN 1 ELSE 0 END) "
                "FROM registros_testeo"
            ).fetchone()
            no_coincide = no_coincide or 0
            con_resultado = con_resultado or 0
            tasa_global = (no_coincide / con_resultado) if con_resultado else 0.0

            ultimo_ingest = None
            for tabla in ("registros_testeo", "atenciones", "encuestas"):
                valor = conn.execute(f"SELECT MAX(fecha) FROM {tabla}").fetchone()[0]
                if valor and (ultimo_ingest is None or valor > ultimo_ingest):
                    ultimo_ingest = valor
        finally:
            conn.close()
    except Exception as e:
        return {"disponible": False, "error": str(e)}

    return {
        "disponible": True,
        "total_testeos": total_testeos,
        "total_atenciones": total_atenciones,
        "total_encuestas": total_encuestas,
        "tasa_no_coincidencia_global": round(tasa_global, 4),
        "ultimo_ingest": ultimo_ingest,
        "disclaimer": DISCLAIMER,
    }


def exportar_csv_agregados(
    filas: Iterable[dict[str, Any]], path: str | Path
) -> int:
    """Exporta una lista de dicts (fila de agregado, ej. `tendencias()` o
    `tasa_adulteracion()`) a CSV. Defensa en profundidad: aunque las
    agregaciones vienen de GROUP BY sobre columnas cerradas sin identidad,
    cada fila se re-escanea con `flujo.privacy.scan_text` ANTES de
    escribirse -- protege contra un futuro cambio de schema o un campo de
    texto libre colado en un agregado. Filas con PII detectado se OMITEN
    (nunca se escriben, nunca se loguea su contenido). Retorna la cantidad
    de filas efectivamente escritas."""
    filas = list(filas)
    campos = list(filas[0].keys()) if filas else []
    escritas = 0
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        if campos:
            writer = csv.DictWriter(fh, fieldnames=campos)
            writer.writeheader()
            for fila in filas:
                texto = "\n".join(
                    str(v) for v in fila.values() if v is not None and str(v) != ""
                )
                if scan_text(texto).total_pii > 0:
                    continue
                writer.writerow(fila)
                escritas += 1
    return escritas
