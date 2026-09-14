#!/usr/bin/env python3
"""Materialize robust esfuerzo.py residuals from the MAK knowledge DB."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


METRICS = (
    "iteraciones",
    "llamadas_llm",
    "profundidad_cadena",
    "errores",
    "timeouts",
    "consultas",
    "deriva_consultas",
    "fuentes",
    "duracion_ms",
)
SIGN = {
    "iteraciones": 1,
    "llamadas_llm": 1,
    "profundidad_cadena": 1,
    "errores": 1,
    "timeouts": 1,
    "consultas": 1,
    "deriva_consultas": 1,
    "fuentes": -1,
    "duracion_ms": 1,
}
DATE_PREFIX = re.compile(r"^20\d{6}(?:[-_]\d{4,6})?-")


def robust_scale(values: list[float]) -> float:
    """Use the attachment contract: MAD, then scaled mean absolute deviation."""
    if len(values) < 2:
        return 0.0
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    mad = statistics.median(deviations)
    if mad > 0:
        return mad
    mean_absolute = sum(deviations) / len(deviations)
    return mean_absolute / 1.4826 if mean_absolute > 0 else 0.0


def source_topic(path: Path) -> str:
    """Read only a small JSON document to retain topic provenance."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        doc = {}
    if isinstance(doc, dict):
        meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
        for key in ("tema", "topic", "titulo", "title"):
            value = doc.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            value = meta.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    stem = path.stem
    stem = DATE_PREFIX.sub("", stem)
    return stem.replace("_", " ").replace("-", " ").strip() or "(sin tema)"


def artifact_dimensions(path: str, relative_path: str) -> tuple[str, str, str]:
    rel = Path(relative_path)
    mode = rel.parts[0] if rel.parts else "(sin modo)"
    route = "/".join(("research",) + rel.parts[:-1])
    return mode, source_topic(Path(path)), route


def load_records(conn: sqlite3.Connection) -> dict[int, dict]:
    records: dict[int, dict] = {}
    query = """
        SELECT a.artifact_id, a.path, a.relative_path,
               e.metric_name, e.metric_value, e.is_present
        FROM effort_metrics AS e
        JOIN artifacts AS a ON a.artifact_id = e.artifact_id
        WHERE e.metric_name IN (%s)
        ORDER BY a.artifact_id, e.metric_name
    """ % ",".join("?" for _ in METRICS)
    for artifact_id, path, relative_path, name, value, is_present in conn.execute(
        query, METRICS
    ):
        record = records.setdefault(
            artifact_id,
            {
                "artifact_id": artifact_id,
                "path": path,
                "relative_path": relative_path,
                "metrics": {},
            },
        )
        if is_present and value is not None:
            record["metrics"][name] = float(value)
    for record in records.values():
        mode, topic, route = artifact_dimensions(
            record["path"], record["relative_path"]
        )
        record.update(mode=mode, topic=topic, route=route)
    return records


def materialize(conn: sqlite3.Connection, records: dict[int, dict], computed_at: str):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS effort_residuals (
            artifact_id INTEGER NOT NULL,
            mode TEXT NOT NULL,
            topic TEXT NOT NULL,
            route TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            expected_median REAL,
            robust_scale REAL,
            residual REAL,
            is_scored INTEGER NOT NULL,
            group_count INTEGER NOT NULL,
            method_source TEXT NOT NULL,
            computed_at TEXT NOT NULL,
            PRIMARY KEY (artifact_id, metric_name),
            FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)
        );
        DELETE FROM effort_residuals;
        """
    )
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in records.values():
        groups[(record["mode"], record["route"])].append(record)

    group_stats: dict[tuple[str, str, str], tuple[float, float, int]] = {}
    for (mode, route), group in groups.items():
        for name in METRICS:
            values = [item["metrics"][name] for item in group if name in item["metrics"]]
            if len(values) < 3:
                group_stats[(mode, route, name)] = (None, 0.0, len(values))
                continue
            median = statistics.median(values)
            scale = robust_scale(values)
            group_stats[(mode, route, name)] = (median, scale, len(values))

    rows = []
    for record in records.values():
        for name, value in record["metrics"].items():
            median, scale, group_count = group_stats[
                (record["mode"], record["route"], name)
            ]
            residual = None
            scored = 0
            if median is not None and scale > 0:
                residual = round(
                    ((value - median) / (1.4826 * scale)) * SIGN[name], 3
                )
                scored = 1
            rows.append(
                (
                    record["artifact_id"],
                    record["mode"],
                    record["topic"],
                    record["route"],
                    name,
                    value,
                    median,
                    scale,
                    residual,
                    scored,
                    group_count,
                    "esfuerzo.py:attachment-contract",
                    computed_at,
                )
            )
    conn.executemany(
        """
        INSERT INTO effort_residuals(
            artifact_id, mode, topic, route, metric_name, metric_value,
            expected_median, robust_scale, residual, is_scored, group_count,
            method_source, computed_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    conn.commit()
    return rows, group_stats


def write_report(report_path: Path, csv_path: Path, rows, records, group_stats, computed_at):
    report_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "artifact_id", "mode", "topic", "route", "metric_name", "metric_value",
        "expected_median", "robust_scale", "residual", "is_scored", "group_count",
        "method_source", "computed_at",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    present = Counter(row[4] for row in rows)
    scored = Counter(row[4] for row in rows if row[9])
    unscored_small = Counter(row[4] for row in rows if not row[9] and row[10] < 3)
    unscored_constant = Counter(
        row[4] for row in rows if not row[9] and row[10] >= 3 and row[7] == 0
    )
    top = sorted((row for row in rows if row[9]), key=lambda row: row[8], reverse=True)[:15]
    lines = [
        "# Residuos robustos de esfuerzo MAK",
        "",
        "Calculado desde `data/mak_knowledge.db` con el contrato adjunto de `esfuerzo.py`.",
        "La agrupacion respeta el modo y la ruta de Research; tema y ruta se conservan",
        "en cada fila para triangulacion posterior.",
        "",
        f"- calculado: `{computed_at}`",
        f"- documentos con metricas: **{len(records)}**",
        f"- filas metricas materializadas: **{len(rows)}**",
        f"- filas puntuadas: **{sum(scored.values())}**",
        f"- CSV: `{csv_path}`",
        "",
        "## Metodo",
        "",
        "Se usa la mediana del grupo y la escala MAD. Si MAD es cero, se usa",
        "la desviacion absoluta media escalada; si el grupo es constante, la fila",
        "queda sin puntuar. Con menos de tres valores comparables no se fabrica",
        "una escala. `fuentes` invierte signo porque menos fuentes implica mayor",
        "resistencia; las demas metricas conservan signo positivo.",
        "",
        "## Cobertura",
        "",
        "| metrica | presente | puntuadas | grupo menor a 3 | grupo constante |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in METRICS:
        lines.append(
            f"| `{name}` | {present[name]} | {scored[name]} | "
            f"{unscored_small[name]} | {unscored_constant[name]} |"
        )
    lines += [
        "",
        "## Mayores residuos positivos",
        "",
        "| residuo | modo | ruta | tema | metrica | valor | esperado |",
        "|---:|---|---|---|---|---:|---:|",
    ]
    for row in top:
        lines.append(
            f"| {row[8]:.3f} | `{row[1]}` | `{row[3]}` | {row[2][:80]} | "
            f"`{row[4]}` | {row[5]:.3f} | {row[6]:.3f} |"
        )
    lines += [
        "",
        "## Limites",
        "",
        "- Un residuo es una senal de esfuerzo relativo, no una calidad ni una",
        "  recomendacion automatica de proyecto.",
        "- Los temas se leen desde el JSON cuando existe una clave declarada; si",
        "  no existe, se conserva el slug del archivo y se marca implicitamente",
        "  como inferencia de ruta.",
        "- `largo_informe`, presente en algunas filas de la base, queda fuera del",
        "  puntaje porque no pertenece al mapa `METRICAS` del contrato adjunto.",
        "- La base no contiene una decision de postulacion; esa decision sigue",
        "  requiriendo evidencia, consumidor y revision humana.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("/home/mak/flujo/data/mak_knowledge.db"))
    parser.add_argument("--report", type=Path, default=Path("/home/mak/flujo/context/MAK_EFFORT_RESIDUALS.md"))
    parser.add_argument("--csv", type=Path, default=Path("/home/mak/flujo/context/MAK_EFFORT_RESIDUALS.csv"))
    args = parser.parse_args()
    computed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys=ON")
    records = load_records(conn)
    rows, group_stats = materialize(conn, records, computed_at)
    write_report(args.report, args.csv, rows, records, group_stats, computed_at)
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    print(json.dumps({
        "db": str(args.db),
        "documents": len(records),
        "metric_rows": len(rows),
        "scored_rows": sum(1 for row in rows if row[9]),
        "groups": len(group_stats),
        "report": str(args.report),
        "csv": str(args.csv),
        "integrity": integrity,
    }, ensure_ascii=True, sort_keys=True))
    conn.close()
    return 0 if integrity == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
