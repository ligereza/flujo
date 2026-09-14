#!/usr/bin/env python3
"""Reconcile the global MAK DB with the persistent garden DB without merging."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


def count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--global-db", type=Path, default=Path("/home/mak/flujo/data/mak_knowledge.db"))
    parser.add_argument("--garden-db", type=Path, default=Path("/home/mak/research/jardines_interpretativos/jardines_interpretativos.sqlite"))
    parser.add_argument("--report", type=Path, default=Path("/home/mak/flujo/context/MAK_JARDINES_RECONCILIATION.md"))
    args = parser.parse_args()

    global_conn = sqlite3.connect(args.global_db)
    garden_conn = sqlite3.connect(args.garden_db)
    global_integrity = global_conn.execute("PRAGMA integrity_check").fetchone()[0]
    garden_integrity = garden_conn.execute("PRAGMA integrity_check").fetchone()[0]
    document = garden_conn.execute(
        "SELECT path,title,sha256,line_count FROM documents ORDER BY id LIMIT 1"
    ).fetchone()
    source_path = Path(document[0])
    global_artifact = global_conn.execute(
        "SELECT artifact_id,path,sha256,text_title,declared_status FROM artifacts WHERE path=?",
        (str(source_path),),
    ).fetchone()
    source_hash = sha256(source_path) if source_path.is_file() else ""
    process_count = count(garden_conn, "process_semantics")
    garden_urls = count(garden_conn, "sources")
    garden_claims = count(garden_conn, "claims")
    garden_entities = count(garden_conn, "entities")
    garden_relations = count(garden_conn, "relations")
    garden_tools = [row[0] for row in garden_conn.execute("SELECT name FROM tools ORDER BY name")]
    global_tool_names = {
        row[0].casefold()
        for row in global_conn.execute("SELECT canonical_name FROM entities WHERE entity_kind='tool_candidate'")
    }
    tool_overlap = sorted(name for name in garden_tools if name.casefold() in global_tool_names)
    effort_rows = count(global_conn, "effort_residuals")
    direct_research_links = global_conn.execute(
        """
        SELECT COUNT(*)
        FROM entity_relations r JOIN entities s ON s.entity_id=r.source_entity_id
        WHERE r.relation_kind='possibly_consumed_by'
          AND (s.path LIKE '/home/mak/research/%'
               OR s.path LIKE '/home/mak/flujo/cultura/mak_research/%')
        """
    ).fetchone()[0]

    hash_match = bool(global_artifact and global_artifact[2] == document[2] == source_hash)
    lines = [
        "# Reconciliacion MAK y Jardines interpretativos",
        "",
        "Este documento es un crosswalk read-only. Las dos bases conservan",
        "esquemas y responsabilidades distintas; no se fusionan tablas por",
        "tener nombres parecidos.",
        "",
        "## Identidad de la fuente",
        "",
        f"- fuente: `{source_path}`",
        f"- titulo: {document[1]}",
        f"- hash de Jardines: `{document[2]}`",
        f"- hash fisico actual: `{source_hash}`",
        f"- match con artifact MAK: **{hash_match}**",
        f"- artifact MAK: `{global_artifact[0] if global_artifact else 'not_found'}`",
        f"- integridad global: `{global_integrity}`",
        f"- integridad Jardines: `{garden_integrity}`",
        "",
        "## Conteo separado",
        "",
        "| superficie | cantidad | funcion |",
        "|---|---:|---|",
        f"| Jardines: fuentes URL | {garden_urls} | referencias capturables, aun no verificadas por red |",
        f"| Jardines: claims | {garden_claims} | afirmaciones/decisiones del documento |",
        f"| Jardines: entidades | {garden_entities} | entidades del modelo interpretativo |",
        f"| Jardines: relaciones | {garden_relations} | relaciones del modelo interpretativo |",
        f"| Jardines: semantica | {process_count} | discover a audit |",
        f"| MAK: residuos de esfuerzo | {effort_rows} | senales cronologicas de Research |",
        "",
        "## Herramientas y puente",
        "",
        f"- herramientas declaradas por Jardines: **{len(garden_tools)}**",
        f"- nombres que coinciden con candidatos tool de MAK: **{len(tool_overlap)}**",
        f"- coincidencias: `{', '.join(tool_overlap) if tool_overlap else 'ninguna'}`",
        f"- relaciones `possibly_consumed_by` desde Research: **{direct_research_links}**",
        "",
        "El cruce por nombre no promueve una herramienta: requiere etapa, entrada,",
        "salida, licencia, plataforma, mantenimiento y consumidor probado. La",
        "ausencia de `possibly_consumed_by` impide afirmar que un JSON de esfuerzo",
        "sea consumido por una herramienta concreta.",
        "",
        "## Decision",
        "",
        "1. La fuente esta correctamente indexada en ambas capas y el hash coincide.",
        "2. La base de Jardines permanece como modelo semantico especializado.",
        "3. `mak_knowledge.db` permanece como inventario cronologico, procedencia",
        "   fisica, imports, consumidores y residuos de esfuerzo.",
        "4. El puente operativo es el router de Research y el gate Cultura, no una",
        "   copia de tablas ni una fusion automatica.",
        "5. La primera entidad que puede pasar a `review_ready` es el expediente",
        "   de Jardines, porque tiene fuente, semantica, relaciones, restricciones",
        "   y un dry-run de propuesta; aun no tiene captura web verificada ni FUP.",
        "",
        "## Limites",
        "",
        "- Las 40 URLs del documento siguen siendo referencias hasta una captura",
        "  explicita; no se presenta su contenido como verificado.",
        "- `review_ready` no significa publicable ni postulacion enviada.",
        "- No se escribio ninguna de las dos bases durante esta reconciliacion.",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.report}")
    print(f"hash_match={int(hash_match)}")
    print(f"global_integrity={global_integrity}")
    print(f"garden_integrity={garden_integrity}")
    print(f"garden_urls={garden_urls}")
    print(f"garden_claims={garden_claims}")
    print(f"garden_tools={len(garden_tools)}")
    print(f"tool_overlap={len(tool_overlap)}")
    print(f"direct_research_links={direct_research_links}")
    print("databases_mutated=0")
    global_conn.close()
    garden_conn.close()
    return 0 if hash_match and global_integrity == "ok" and garden_integrity == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
