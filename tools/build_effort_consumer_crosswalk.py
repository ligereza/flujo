#!/usr/bin/env python3
"""Build a read-only crosswalk from effort outliers to Research consumers."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def fetch_rows(conn: sqlite3.Connection, limit: int):
    return conn.execute(
        """
        SELECT r.residual, a.path, r.mode, r.route, r.topic,
               r.metric_name, r.metric_value, r.expected_median
        FROM effort_residuals AS r
        JOIN artifacts AS a ON a.artifact_id=r.artifact_id
        WHERE r.is_scored=1
        ORDER BY r.residual DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def direct_links(conn: sqlite3.Connection, artifact_path: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT e.entity_kind, e.canonical_name, e.status
        FROM artifacts a
        JOIN entity_artifacts ea ON ea.artifact_id=a.artifact_id
        JOIN entities e ON e.entity_id=ea.entity_id
        WHERE a.path=?
        ORDER BY e.entity_kind, e.canonical_name
        """,
        (artifact_path,),
    ).fetchall()
    return [f"{kind}:{name} [{status}]" for kind, name, status in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("/home/mak/flujo/data/mak_knowledge.db"))
    parser.add_argument("--report", type=Path, default=Path("/home/mak/flujo/context/MAK_EFFORT_CONSUMER_CROSSWALK.md"))
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    rows = fetch_rows(conn, args.limit)
    effort_files = conn.execute("SELECT COUNT(DISTINCT artifact_id) FROM effort_metrics").fetchone()[0]
    linked_files = conn.execute(
        """
        SELECT COUNT(DISTINCT e.artifact_id)
        FROM effort_metrics e JOIN entity_artifacts ea ON ea.artifact_id=e.artifact_id
        """
    ).fetchone()[0]
    static_links = conn.execute(
        """
        SELECT COUNT(*)
        FROM entity_relations r JOIN entities s ON s.entity_id=r.source_entity_id
        WHERE r.relation_kind='possibly_consumed_by'
          AND (s.path LIKE '/home/mak/research/%'
               OR s.path LIKE '/home/mak/flujo/cultura/mak_research/%'
               OR s.path='/home/mak/flujo/tools/research_job_router.py')
        """
    ).fetchone()[0]
    active_research_consumers = conn.execute(
        """
        SELECT e.entity_kind, e.canonical_name, e.path, e.status
        FROM entities e
        WHERE e.path IN (
          '/home/mak/research/interfaz.py',
          '/home/mak/flujo/cultura/mak_research/interfaz.py',
          '/home/mak/flujo/cultura/mak_research/source_pipeline.py',
          '/home/mak/flujo/cultura/mak_research/fondart_corpus.py',
          '/home/mak/flujo/tools/research_job_router.py'
        )
        ORDER BY e.path, e.entity_kind
        """
    ).fetchall()

    lines = [
        "# Crosswalk de esfuerzo hacia consumidores Research/Cultura",
        "",
        "Este reporte no convierte un residuo estadistico en una decision de",
        "limpieza o postulacion. Solo conecta la senal con evidencia de ruta y",
        "declara donde el inventario aun no prueba consumo runtime.",
        "",
        f"- base: `{args.db}`",
        f"- documentos con esfuerzo: **{effort_files}**",
        f"- documentos con entidad directa: **{linked_files}**",
        f"- relaciones `possibly_consumed_by` directas desde Research: **{static_links}**",
        "",
        "## Lectura de la evidencia",
        "",
        "Los JSON de esfuerzo estan vinculados a la entidad de departamento",
        "`research`, pero el inventario no contiene relaciones estaticas",
        "`possibly_consumed_by` desde esos JSON hacia un consumidor. Por eso",
        "el ranking sirve para priorizar revision, mientras que el consumo real",
        "se prueba con la interfaz 8890, el proxy 8900 y el gate de Cultura.",
        "",
        "## Consumidores candidatos conocidos",
        "",
        "| componente | estado de evidencia | consumidor/ruta |",
        "|---|---|---|",
        "| `tools/research_job_router.py` | contract_checked; runtime gate probado | `GET /api/cultura/opportunity-gate` en 8900 |",
        "| `cultura/mak_research/source_pipeline.py` | componente presente; captura separada | gate offline; no proveedor llamado |",
        "| `cultura/mak_research/fondart_corpus.py` | componente presente; corpus separado | gate offline; propuesta queda en draft |",
        "| `cultura/mak_research/interfaz.py` | canonico/proyeccion hash-validado | servicio interno 8890, proxied by 8900 |",
        "| `cultura/mak_plataforma/hub.py` | entrypoint activo | hub 8900; APIs Cultura/Research |",
        "",
        "## Candidatos priorizados por residuo",
        "",
        "| residuo | modo | ruta | tema | metrica | valor | esperado | entidad directa |",
        "|---:|---|---|---|---|---:|---:|---|",
    ]
    for residual, path, mode, route, topic, metric, value, expected in rows:
        links = "; ".join(direct_links(conn, path)) or "sin entidad directa"
        topic = topic.replace("|", "/").replace("\n", " ")[:100]
        lines.append(
            f"| {residual:.3f} | `{mode}` | `{route}` | {topic} | `{metric}` | "
            f"{value:.3f} | {expected:.3f} | {links} |"
        )
    lines += [
        "",
        "## Consumidores estaticos encontrados por el inventario",
        "",
        "| tipo | nombre | ruta | estado |",
        "|---|---|---|---|",
    ]
    for kind, name, path, status in active_research_consumers:
        lines.append(f"| `{kind}` | `{name}` | `{path}` | `{status}` |")
    lines += [
        "",
        "## Decision de fase",
        "",
        "El siguiente slice no debe ser un informe con residuo alto aislado:",
        "debe ser el gate `opportunity -> research job -> draft proposal`,",
        "porque es el unico tramo que ya tiene componente, ruta 8900, contrato",
        "offline y rollback claro. Los outliers de `errores`, `duracion_ms` y",
        "`profundidad_cadena` quedan como evidencia para mejorar ese proceso, no",
        "como motivo para descartar documentos o herramientas.",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.report}")
    print(f"outliers={len(rows)}")
    print(f"effort_files={effort_files}")
    print(f"directly_linked={linked_files}")
    print(f"research_static_consumers={static_links}")
    print("database_mutated=0")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
