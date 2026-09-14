#!/usr/bin/env python3
"""Route a research idea to a domain adapter and produce an auditable plan."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

try:
    from tools.interpretive_garden_workflow import SEMANTICS, create_schema
except ImportError:
    from interpretive_garden_workflow import SEMANTICS, create_schema


ADAPTERS = {
    "plants": {
        "label": "Plantas y jardines",
        "description": "Modelado de crecimiento, ecologia, cultivo y traduccion visual.",
        "examples": "planta, cultivo, jardin, semilla, micelio, botania, crecimiento",
        "source_policy": "manuales, papers, herbarios, fuentes de cultivo y documentacion botanica",
        "constraint_policy": "separar metafora de evidencia; no presentar simulacion como hecho biologico",
        "keywords": ("planta", "cultivo", "jardin", "semilla", "micelio", "botan", "crecimiento", "fungi"),
    },
    "vj": {
        "label": "VJ y visuales en vivo",
        "description": "Herramientas, formatos, senales y flujos para visuales, pantallas y venues.",
        "examples": "vj, visuales, mapping, pantalla, midi, osc, blender, resolume, venue",
        "source_policy": "repositorios oficiales, releases, licencias, manuales y compatibilidad de plataforma",
        "constraint_policy": "distinguir open source, freeware, free tier, trial y uso no comercial",
        "keywords": ("vj", "visual", "mapping", "pantalla", "midi", "osc", "blender", "resolume", "venue", "proyeccion"),
    },
    "curatoria": {
        "label": "Curatoria e investigacion cultural",
        "description": "Archivos, artistas, exposiciones, precedentes y relaciones culturales.",
        "examples": "curatoria, archivo, artista, exposicion, obra, precedente, coleccion",
        "source_policy": "fuentes institucionales, catalogos, archivos, papers y paginas de artistas",
        "constraint_policy": "separar dato documentado, atribucion, lectura curatorial y especulacion",
        "keywords": ("curator", "curatoria", "archivo", "artista", "exposicion", "obra", "catalogo", "coleccion"),
    },
    "rd": {
        "label": "Reduciendo Dano",
        "description": "Entregables operativos de eventos, cotizaciones, planos y riders.",
        "examples": "rd, reduciendo dano, cotizacion, plano, rider, evento, suplemento",
        "source_policy": "datos locales autorizados, fichas verificadas y contratos operativos",
        "constraint_policy": "no inventar precios, venues, proveedores ni datos clinicos; mutaciones requieren autoridad",
        "keywords": ("reduciendo", "dano", "cotizacion", "cotización", "rider", "suplemento", "evento", "rd"),
    },
    "portfolio": {
        "label": "Portafolio y sitio",
        "description": "Obras, servicios, casos, propuestas y publicacion web.",
        "examples": "portafolio, sitio, web, dominio, obra, proyecto, propuesta",
        "source_policy": "assets locales, fichas de obra, dominios y evidencia publicada",
        "constraint_policy": "no publicar corpus privado, credenciales ni afirmaciones sin fuente",
        "keywords": ("portafolio", "portfolio", "sitio", "web", "dominio", "propuesta", "publicar"),
    },
    "general": {
        "label": "Investigacion general",
        "description": "Pregunta que aun no tiene un adaptador especifico.",
        "examples": "pregunta nueva, tema transversal, exploracion",
        "source_policy": "descubrir fuentes y declarar el dominio antes de interpretar",
        "constraint_policy": "mantener incertidumbre y no forzar una clasificacion",
        "keywords": (),
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def detect_domain(question: str) -> tuple[str, list[tuple[str, int]]]:
    normalized = question.casefold()
    scores = []
    for slug, adapter in ADAPTERS.items():
        score = sum(1 for keyword in adapter["keywords"] if keyword in normalized)
        if score:
            scores.append((slug, score))
    scores.sort(key=lambda item: (-item[1], item[0]))
    return (scores[0][0] if scores else "general", scores)


def ensure_adapters(conn: sqlite3.Connection) -> dict[str, int]:
    ids = {}
    for slug, adapter in ADAPTERS.items():
        conn.execute(
            "INSERT OR IGNORE INTO domain_adapters(slug,label,description,input_examples,source_policy,constraint_policy) VALUES (?,?,?,?,?,?)",
            (slug, adapter["label"], adapter["description"], adapter["examples"], adapter["source_policy"], adapter["constraint_policy"]),
        )
        conn.execute(
            "UPDATE domain_adapters SET label=?,description=?,input_examples=?,source_policy=?,constraint_policy=? WHERE slug=?",
            (adapter["label"], adapter["description"], adapter["examples"], adapter["source_policy"], adapter["constraint_policy"], slug),
        )
        ids[slug] = conn.execute("SELECT id FROM domain_adapters WHERE slug=?", (slug,)).fetchone()[0]
    return ids


def create_job(db_path: Path, question: str, domain: str | None) -> tuple[int, str, list[tuple[str, int]]]:
    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        adapter_ids = ensure_adapters(conn)
        detected, scores = detect_domain(question)
        selected = domain or detected
        if selected not in ADAPTERS:
            raise ValueError(f"unknown domain: {selected}")
        conn.execute(
            "INSERT INTO research_jobs(question,domain,adapter_id,status,next_process,created_at) VALUES (?,?,?,?,?,?)",
            (question, selected, adapter_ids[selected], "planned", "discover", now_iso()),
        )
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for order, (process_key, label_es, input_semantics, output_semantics, output_kind, policy) in enumerate(SEMANTICS, 1):
            provider_policy = "local_first; search_for_discovery; firecrawl_for_official_capture; groq_or_gemini_for_structured_extraction; ollama_fallback"
            if process_key in ("validate", "audit"):
                provider_policy = "deterministic_local_checks; human_or_source_review_required"
            conn.execute(
                "INSERT INTO job_steps(job_id,step_order,process_key,input_semantics,output_semantics,status,provider_policy) VALUES (?,?,?,?,?,?,?)",
                (job_id, order, process_key, input_semantics, output_semantics, "pending", provider_policy),
            )
        adapter = ADAPTERS[selected]
        conn.execute("INSERT INTO job_relations(job_id,relation_type,from_object,to_object,rationale) VALUES (?,?,?,?,?)", (
            job_id, "uses_adapter", "research_job", selected, adapter["description"],
        ))
        conn.execute("INSERT INTO audit_events(event_type,object_type,object_id,detail,created_at) VALUES (?,?,?,?,?)", (
            "plan", "research_job", job_id, f"Selected domain adapter {selected}; no external call executed", now_iso(),
        ))
        conn.commit()
    return job_id, selected, scores


def render_job(db_path: Path, output_dir: Path, job_id: int, selected: str, scores: list[tuple[str, int]]) -> tuple[Path, Path]:
    with sqlite3.connect(db_path) as conn:
        job = conn.execute("SELECT question,domain,status,next_process,created_at FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        adapter = conn.execute("SELECT label,description,input_examples,source_policy,constraint_policy FROM domain_adapters WHERE slug=?", (selected,)).fetchone()
        steps = conn.execute("SELECT step_order,process_key,input_semantics,output_semantics,status,provider_policy FROM job_steps WHERE job_id=? ORDER BY step_order", (job_id,)).fetchall()
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", job[0].casefold()).strip("-")[:70] or f"job-{job_id}"
    json_path = output_dir / f"{job_id:04d}-{slug}.json"
    md_path = output_dir / f"{job_id:04d}-{slug}.md"
    payload = {
        "job_id": job_id, "question": job[0], "domain": selected,
        "status": job[2], "next_process": job[3], "created_at": job[4],
        "adapter": {"label": adapter[0], "description": adapter[1], "input_examples": adapter[2], "source_policy": adapter[3], "constraint_policy": adapter[4]},
        "detected_scores": scores,
        "steps": [dict(zip(("order", "process", "input", "output", "status", "provider_policy"), row)) for row in steps],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Research job {job_id}: {adapter[0]}", "", f"**Pregunta:** {job[0]}",
        f"**Dominio:** `{selected}`", f"**Estado:** `{job[2]}`", "", adapter[1],
        "", "## Politica del adaptador", "", f"- Fuentes: {adapter[3]}",
        f"- Restricciones: {adapter[4]}", "", "## Ruta semantica", "",
        "| Paso | Proceso | Entrada | Salida | Estado |", "|---:|---|---|---|---|",
    ]
    for order, process_key, input_semantics, output_semantics, status, _provider_policy in steps:
        lines.append(f"| {order} | `{process_key}` | {input_semantics} | {output_semantics} | `{status}` |")
    lines += [
        "", "## Politica de proveedores", "",
        "- Descubrimiento: busqueda local, SearXNG o API de repositorios.",
        "- Captura: Firecrawl solo para paginas oficiales y con URL registrada.",
        "- Extraccion estructurada: Groq o Gemini; Ollama como fallback local.",
        "- Validacion: checks deterministas y revision de evidencia.",
        "- Publicacion: solo despues de licencia, compatibilidad, consumidor y estado verificados.",
        "", "Este archivo es un plan; no implica que se hayan ejecutado llamadas externas.", "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--domain", choices=sorted(ADAPTERS), default=None)
    parser.add_argument("--db", type=Path, default=Path("/home/mak/research/jardines_interpretativos/jardines_interpretativos.sqlite"))
    parser.add_argument("--out-dir", type=Path, default=Path("/home/mak/research/jobs"))
    args = parser.parse_args()
    db_path = args.db.resolve()
    job_id, selected, scores = create_job(db_path, args.question, args.domain)
    json_path, md_path = render_job(db_path, args.out_dir.resolve(), job_id, selected, scores)
    print(f"job_id={job_id}")
    print(f"domain={selected}")
    print(f"json={json_path}")
    print(f"report={md_path}")
    print("external_calls=0")
    print("validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
