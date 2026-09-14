"""Canonical MAK department registry.

This module is deliberately data-first: the 8900 hub, diagnostics and an
external agent can discover the same three operational areas without reading
the whole repository. Paths are relative to the repository unless explicitly
marked as a runtime root.
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import os
import sqlite3
from typing import Any

SCHEMA = "mak-departments-v1"

DEPARTMENTS: dict[str, dict[str, Any]] = {
    "rd": {
        "label": "RD / Reduciendo Dano",
        "scope": "packs, quotes, plano, rider, venues, producers and events",
        "root_paths": ["src/flujo/rd", "src/flujo/plano", "data/rd.db"],
        "surface": "/departments/rd",
        "tool_links": [
            {"label": "Plano editor", "path": "/static/rd/plano"},
            {"label": "RD database", "path": "/api/rd/summary"},
            {"label": "RD topics", "path": "/api/rd/topics"},
            {"label": "Entity crosswalk", "path": "/api/rd/crosswalk"},
            {"label": "RD/Cultura relations", "path": "/api/rd/cultura-relations"},
        ],
        "contract_dir": "contracts/departments/rd",
        "handoff": "docs/handoffs/archive/rd.md",
        "runtime_mode": "offline_first",
        "api_dependencies": ["optional provider APIs for research only"],
    },
    "cultura": {
        "label": "Cultura / Research",
        "scope": "artistic ideas, curation, research, scraping and proposals",
        "root_paths": ["cultura", "cultura/mak_research", "context/diagnostics"],
        "surface": "/departments/cultura",
        "tool_links": [
            {"label": "Research service", "path": "/research/"},
            {"label": "Research jobs / Jardines", "path": "/research-garden/"},
            {"label": "Curation sources", "path": "/api/cultura/sources"},
            {"label": "Capabilities", "path": "/api/cultura/capabilities"},
            {"label": "Opportunity gate", "path": "/api/cultura/opportunity-gate"},
        ],
        "contract_dir": "contracts/departments/cultura",
        "handoff": "docs/handoffs/archive/cultura.md",
        "runtime_mode": "offline_first_with_optional_apis",
        "api_dependencies": ["Firecrawl", "Tavily", "Crawl4AI"],
    },
    "iskvw": {
        "label": "ISKVW / Portfolio",
        "scope": "artist portfolio, visual skins, web publication and venue identity",
        "root_paths": ["iskvw", "iskvw/editor.html", "tools/portfolio"],
        "surface": "/departments/iskvw",
        "tool_links": [
            {"label": "Portfolio editor", "path": "/portafolio/"},
            {"label": "ISKVW editor", "path": "/static/iskvw/editor"},
            {
                "label": "Archive portfolio view",
                "path": "/api/portfolio/archive-view",
                "mode": "read_only",
                "status": "draft",
                "publication": False,
                "authorship": False,
            },
        ],
        "contract_dir": "contracts/departments/iskvw",
        "handoff": "docs/handoffs/archive/iskvw.md",
        "runtime_mode": "offline_first",
        "api_dependencies": ["Cloudflare only at publication boundary"],
    },
}


def catalog(root: Path) -> dict[str, Any]:
    """Return bounded department metadata and physical existence checks."""
    root = Path(root).resolve()

    def exists(relative: str) -> bool:
        """Resolve motor-owned paths in the sibling FLUJO checkout too."""
        direct = root / relative
        if direct.exists():
            return True
        if relative.startswith("src/flujo/"):
            return (root / "flujo" / relative).exists()
        return False

    areas: dict[str, dict[str, Any]] = {}
    for key, raw in DEPARTMENTS.items():
        checks = {path: exists(path) for path in raw["root_paths"]}
        contract_dir = root / raw["contract_dir"]
        handoff = root / raw["handoff"]
        areas[key] = {
            **raw,
            "root_checks": checks,
            # No `agents` entry: the per-department `agents.md` files were
            # deleted 2026-09-03 with every other contract file. Reporting a
            # permanent False invites the next agent to "fix" it by recreating
            # a document nobody asked for.
            "contract_files": {
                "requirements": (contract_dir / "requirements.txt").is_file(),
                "env_example": (contract_dir / ".env.example").is_file(),
            },
            "handoff_exists": handoff.is_file(),
            "ready": all(checks.values()) and contract_dir.is_dir() and handoff.is_file(),
        }
    return {
        "schema": SCHEMA,
        "version": 1,
        "primary_interface": "http://127.0.0.1:8900",
        "historical_archive": "/home/mak/WIN",
        "areas": areas,
    }


def rd_summary(root: Path) -> dict[str, Any]:
    """Read-only summary of both RD SQLite boundaries."""
    root = Path(root).resolve()
    result: dict[str, Any] = {
        "schema": "mak-rd-summary-v1",
        "canonical_projection": "data/rd.db",
        # Una sola base desde el 2026-09-05. `rd_datos.db` se conserva como
        # origen de la migracion y ya no recibe escrituras.
        "runtime_tables_in_projection": ["registros_testeo", "atenciones", "encuestas"],
        "legacy_runtime_boundary": "data/rd_datos.db",
        "databases": {},
    }
    for relative in ("data/rd.db", "data/rd_datos.db"):
        path = root / relative
        entry: dict[str, Any] = {"path": relative, "exists": path.is_file()}
        if path.is_file():
            try:
                uri = "file:%s?mode=ro" % path.as_posix()
                with sqlite3.connect(uri, uri=True) as connection:
                    tables = [row[0] for row in connection.execute(
                        "select name from sqlite_master where type='table' order by name")]
                    counts = {}
                    for table in tables:
                        safe = table.replace('"', '""')
                        counts[table] = connection.execute(
                            'select count(*) from "%s"' % safe).fetchone()[0]
                    entry["tables"] = tables
                    entry["row_counts"] = counts
                    entry["rows"] = sum(counts.values())
            except (OSError, sqlite3.Error) as exc:
                entry["error"] = type(exc).__name__
        result["databases"][relative] = entry
    crosswalk_path = root / "data" / "rd_fuentes" / "candidates" / "rd_portfolio_entity_crosswalk.json"
    try:
        crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
        result["crosswalk"] = {
            "path": crosswalk_path.relative_to(root).as_posix(),
            "status": crosswalk.get("status", "unknown"),
            "source_databases": crosswalk.get("source_databases", []),
            "entities": [
                {
                    "canonical_id": item.get("canonical_id"),
                    "role": item.get("role"),
                    "confidence": item.get("confidence"),
                    "publication": item.get("publication"),
                    "evidence": item.get("evidence", []),
                }
                for item in crosswalk.get("entities", [])
                if isinstance(item, dict)
            ],
            "mutation": "disabled",
        }
    except (OSError, ValueError, TypeError):
        result["crosswalk"] = {
            "path": "data/rd_fuentes/candidates/rd_portfolio_entity_crosswalk.json",
            "status": "unavailable",
            "entities": [],
            "mutation": "disabled",
        }
    return result


def rd_crosswalk(root: Path) -> dict[str, Any]:
    """Return the validated RD/portfolio crosswalk without side effects."""
    root = Path(root).resolve()
    path = root / "data" / "rd_fuentes" / "candidates" / "rd_portfolio_entity_crosswalk.json"
    try:
        from .rd.entity_crosswalk import load_crosswalk

        crosswalk = load_crosswalk(path)
        return {
            "schema": "mak-rd-crosswalk-v1",
            "contract": crosswalk.contract,
            "version": crosswalk.version,
            "status": crosswalk.status,
            "path": path.relative_to(root).as_posix(),
            "source_databases": list(crosswalk.source_databases),
            "mutation": "disabled",
            "identity_join": "explicit_provenance_only",
            "entities": [dict(link.raw) for link in crosswalk.entities],
        }
    except Exception as exc:  # noqa: BLE001 - endpoint reports contract failure
        return {
            "schema": "mak-rd-crosswalk-v1",
            "contract": "rd_portfolio_entity_crosswalk",
            "version": 1,
            "status": "invalid",
            "path": "data/rd_fuentes/candidates/rd_portfolio_entity_crosswalk.json",
            "source_databases": [],
            "mutation": "disabled",
            "entities": [],
            "error": type(exc).__name__,
        }


def rd_cultura_relations(root: Path) -> dict[str, Any]:
    """Build a bounded, provenance-first relation view across RD/Cultura.

    This is a read-only projection of existing JSON records. Unresolved venue
    names remain candidates and are never promoted to canonical IDs.
    """
    root = Path(root).resolve()
    relations: list[dict[str, Any]] = []
    producers: list[dict[str, Any]] = []
    venues: list[dict[str, Any]] = []
    productora_root = root / "data" / "productoras"
    for path in sorted(productora_root.glob("*.json")) if productora_root.is_dir() else ():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        slug = path.stem
        role = "artist_dj" if raw.get("tipo") == "artist_dj" else "producer_or_brand"
        producers.append({"id": slug, "name": raw.get("name", slug), "role": role,
                          "source": path.relative_to(root).as_posix()})
        for relation in raw.get("relaciones", []):
            if not isinstance(relation, dict) or not relation.get("objetivo"):
                continue
            relations.append({
                "source_id": slug,
                "target_id": str(relation["objetivo"]).strip().lower().replace(" ", "_"),
                "relation_type": relation.get("tipo", "related_to"),
                "status": "explicit_user_or_source_relation",
                "evidence": [relation.get("fuente", path.relative_to(root).as_posix())],
            })
        for index, event in enumerate(raw.get("eventos", [])):
            if not isinstance(event, dict):
                continue
            event_id = "event_candidate:%s:%d" % (slug, index)
            relations.append({
                "source_id": slug,
                "target_id": event_id,
                "relation_type": "producer_event" if role != "artist_dj" else "artist_event",
                "status": event.get("estado", "review"),
                "evidence": [event.get("fuente", path.relative_to(root).as_posix())],
                "label": event.get("nombre", ""),
            })
            venue_name = str(event.get("venue") or "").strip()
            if venue_name and venue_name.lower() not in {"needs_confirmation", "santiago"}:
                relations.append({
                    "source_id": event_id,
                    "target_id": str(event.get("venue_id") or venue_name),
                    "relation_type": "event_venue",
                    "status": "canonical" if event.get("venue_id") else "review_candidate",
                    "evidence": [event.get("fuente", path.relative_to(root).as_posix())],
                })
        for venue in raw.get("venues", []):
            if isinstance(venue, dict) and venue.get("nombre"):
                relations.append({
                    "source_id": slug,
                    "target_id": str(venue.get("venue_id") or venue["nombre"]),
                    "relation_type": "producer_venue" if role != "artist_dj" else "artist_venue",
                    "status": "canonical" if venue.get("venue_id") else "review_candidate",
                    "evidence": [venue.get("notas", path.relative_to(root).as_posix())],
                })
    venue_root = root / "data" / "venues"
    for path in sorted(venue_root.glob("*.json")) if venue_root.is_dir() else ():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict) and raw.get("id"):
            venues.append({"id": raw["id"], "name": raw.get("nombre", raw["id"]),
                           "type": raw.get("tipo", "unknown"),
                           "source": path.relative_to(root).as_posix(),
                           "technical": True})
    return {
        "schema": "mak-rd-cultura-relations-v1",
        "status": "read_only_candidate_graph",
        "mutation": "disabled",
        "join_rule": "explicit_venue_id_or_provenance_only",
        "producers": producers,
        "venues": venues,
        "relations": relations[:500],
        "truncated": len(relations) > 500,
        "consumers": [
            {"name": "rd_panel", "path": "src/flujo/rd/panel.py"},
            {"name": "research_router", "path": "cultura/mak_plataforma/research_router.py"},
            {"name": "portfolio_venue_surface", "path": "iskvw/piel/venue"},
        ],
    }


def rd_topics(root: Path) -> dict[str, Any]:
    """Return the RD data separated by operational theme.

    This is a bounded read-only index, not a second database. The canonical
    projection remains ``data/rd.db``, which since 2026-09-05 also carries the
    accumulative field tables; ``data/rd_datos.db`` is kept as the migration
    source and remains an
    empty runtime boundary. Counts come from the existing summary and the
    cross-domain bridge reports only expose status and bounded totals.
    """
    root = Path(root).resolve()
    summary = rd_summary(root)
    canonical = summary.get("databases", {}).get("data/rd.db", {})
    counts = canonical.get("row_counts", {})
    crosswalk = summary.get("crosswalk", {})
    relations = rd_cultura_relations(root)

    def row_total(*tables: str) -> int:
        return sum(int(counts.get(table, 0) or 0) for table in tables)

    topics = [
        {
            "id": "service_delivery",
            "label": "Operacion en terreno",
            "purpose": "Packs, eventos y la salida operativa de plano, rider y cotizacion.",
            "tables": ["packs", "eventos"],
            "rows": row_total("packs", "eventos"),
            "sources": ["src/flujo/rd", "src/flujo/plano", "data/rd.db"],
        },
        {
            "id": "event_calendar",
            "label": "Calendario y red de eventos",
            "purpose": "Productoras, venues y enlaces de eventos que alimentan la triangulacion.",
            "tables": ["productoras", "venues", "productora_eventos", "productora_venues"],
            "rows": row_total("productoras", "venues", "productora_eventos", "productora_venues"),
            "sources": ["data/rd.db", "data/productoras", "data/venues"],
        },
        {
            "id": "testing_evidence",
            "label": "Testeo y evidencia",
            "purpose": "Reactivos, sustancias, observaciones y fuentes del trabajo de testeo.",
            "tables": [
                "reactivos", "inclusiones", "testeo_fuentes", "testeo_eventos_fuente",
                "testeo_filas_fuente", "testeo_observaciones_fuente", "testeo_enlaces_revision",
                "testeo_mapa_reactivos", "testeo_mapa_sustancias",
            ],
            "rows": row_total(
                "reactivos", "inclusiones", "testeo_fuentes", "testeo_eventos_fuente",
                "testeo_filas_fuente", "testeo_observaciones_fuente", "testeo_enlaces_revision",
                "testeo_mapa_reactivos", "testeo_mapa_sustancias",
            ),
            "sources": ["src/flujo/rd/database.py", "data/rd.db"],
        },
        {
            "id": "delivery_assets",
            "label": "Productos y activos de entrega",
            "purpose": "Suplementos, inclusiones, logos y tipos que se consumen al preparar una pieza.",
            "tables": ["suplementos", "productora_logos", "productora_tipos"],
            "rows": row_total("suplementos", "productora_logos", "productora_tipos"),
            "sources": ["src/flujo/rd", "knowledge/logos", "data/rd.db"],
        },
        {
            "id": "research_bridges",
            "label": "Puentes con Cultura y Portfolio",
            "purpose": "Relaciones explicitamente trazables; lo dudoso queda como candidato de revision.",
            "tables": [],
            "rows": len(crosswalk.get("entities", [])) + len(relations.get("relations", [])),
            "sources": [
                "data/rd_fuentes/candidates/rd_portfolio_entity_crosswalk.json",
                "data/productoras",
                "data/venues",
            ],
        },
    ]
    return {
        "schema": "mak-rd-topics-v1",
        "read_only": True,
        "mutation": "disabled",
        "canonical_projection": "data/rd.db",
        "runtime_tables_in_projection": ["registros_testeo", "atenciones", "encuestas"],
        "legacy_runtime_boundary": "data/rd_datos.db",
        "topics": topics,
        "bridges": {
            "portfolio_crosswalk": {
                "status": crosswalk.get("status", "unavailable"),
                "entities": len(crosswalk.get("entities", [])),
                "mutation": "disabled",
            },
            "rd_cultura_relations": {
                "status": relations.get("status", "unavailable"),
                "producers": len(relations.get("producers", [])),
                "venues": len(relations.get("venues", [])),
                "relations": len(relations.get("relations", [])),
                "truncated": bool(relations.get("truncated")),
                "mutation": "disabled",
            },
        },
        "database": {
            "canonical_exists": bool(canonical.get("exists")),
            "canonical_rows": int(canonical.get("rows", 0) or 0),
            "runtime_exists": bool(summary.get("databases", {}).get("data/rd_datos.db", {}).get("exists")),
            "runtime_rows": int(summary.get("databases", {}).get("data/rd_datos.db", {}).get("rows", 0) or 0),
        },
    }


def cultura_sources(root: Path) -> dict[str, Any]:
    """Expose source-entry metadata without reading private corpus contents."""
    root = Path(root).resolve()
    roots = [root / "cultura" / "mak_research", root / "data" / "rd_fuentes"]
    files: list[dict[str, Any]] = []
    for source_root in roots:
        if not source_root.is_dir():
            continue
        for path in sorted(source_root.iterdir()):
            if path.name.startswith("__") or path.suffix in {".pyc", ".db"}:
                continue
            files.append({
                "path": path.relative_to(root).as_posix(),
                "kind": "directory" if path.is_dir() else "file",
            })
    return {
        "schema": "mak-cultura-sources-v1",
        "roots": [path.relative_to(root).as_posix() for path in roots if path.exists()],
        "entries": files[:240],
        "truncated": len(files) > 240,
    }


def cultura_capabilities(root: Path) -> dict[str, Any]:
    """Describe the offline research and proposal route without calling APIs."""
    root = Path(root).resolve()
    try:
        from cultura.mak_plataforma.research_router import (
            OUTPUT_CONTRACTS,
            route_research_task,
        )
        opportunity = route_research_task("atender", "Fondart convocatoria")
        formats = sorted(OUTPUT_CONTRACTS)
        opportunity_contract = list(opportunity.required_fields)
    except Exception:
        formats = []
        opportunity_contract = []
    return {
        "schema": "mak-cultura-capabilities-v1",
        "offline": {
            "source_pipeline": (root / "cultura/mak_research/source_pipeline.py").is_file(),
            "fondart_corpus": (root / "cultura/mak_research/fondart_corpus.py").is_file(),
            "research_router": (root / "cultura/mak_plataforma/research_router.py").is_file(),
            "proposal_generator": (root / "tools/gen_propuesta_directiva.py").is_file(),
        },
        "output_formats": formats,
        "opportunity_contract": opportunity_contract,
        "providers": {
            "firecrawl_configured": bool(os.environ.get("FIRECRAWL_API_KEY")),
            "tavily_configured": bool(os.environ.get("TAVILY_API_KEY")),
            "crawl4ai_installed": importlib.util.find_spec("crawl4ai") is not None,
            "urllib_fallback": True,
        },
        "policy": {
            "offline_first": True,
            "live_scrape_requires_explicit_gate": True,
            "proposal_is_draft_until_review": True,
            "secrets_in_payload": False,
        },
    }


def cultura_opportunity_gate(root: Path) -> dict[str, Any]:
    """Verify the offline opportunity-to-proposal contract without execution."""
    root = Path(root).resolve()
    try:
        from cultura.mak_plataforma.research_router import route_research_task

        route = route_research_task("atender", "Fondart convocatoria")
        fields = list(route.required_fields)
        route_name = route.formato
    except Exception:
        fields = []
        route_name = "unavailable"
    paths = {
        "source_pipeline": "cultura/mak_research/source_pipeline.py",
        "fondart_corpus": "cultura/mak_research/fondart_corpus.py",
        "research_router": "cultura/mak_plataforma/research_router.py",
        "proposal_generator": "tools/gen_propuesta_directiva.py",
        "proposal_rd_generator": "tools/gen_propuestas_rd.py",
    }
    return {
        "schema": "mak-cultura-opportunity-gate-v1",
        "mode": "contract_check_only",
        "route": route_name,
        "required_fields": fields,
        "components": {name: (root / path).is_file() for name, path in paths.items()},
        "provider_policy": {
            "scrape": "optional_and_explicit",
            "proposal": "draft_until_human_review",
            "network": "not_called",
            "ledger_mutation": "not_called",
        },
        "output": "opportunity_card_then_reviewed_proposal",
    }
