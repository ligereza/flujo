#!/usr/bin/env python3
"""Build a traceable research model for JARDINES_INTERPRETATIVOS.md.

The tool is intentionally offline-first. It parses the source document, keeps
all referenced URLs, creates a small SQLite knowledge model, and renders a
Spanish research report. Network capture is a separate future step: a URL is
not treated as verified merely because it appears in the document.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0"
URL_RE = re.compile(r"https?://[^\s)>'\"]+")

TOPICS = [
    ("core_thesis", "Tesis y posicionamiento", "Laboratorio de traduccion entre conocimiento y experiencia."),
    ("knowledge_model", "Modelo de conocimiento", "Fuentes, claims, entidades, relaciones y procedencia."),
    ("analogy_interpretation", "Analogia e interpretacion", "Correspondencia, lectura, quiebre y limites."),
    ("garden_simulation", "Simulacion de jardin", "Reglas, semillas, ambiente, estados y trayectorias."),
    ("domain_adapters", "Adaptadores de dominio", "Plantas, alimentos y sustancias como dominios diferenciados."),
    ("research_pipeline", "Pipeline de investigacion", "Idea, precedentes, herramientas, prototipo, resultado y obra."),
    ("visual_generation", "Generacion visual", "SVG, imagen, animacion, 3D, simulacion y web."),
    ("reference_tools", "Mapa de herramientas", "Herramientas externas clasificadas por funcion, no por moda."),
    ("risks_ethics", "Riesgos y etica", "Incertidumbre, danos, licencias, opacidad y limites de uso."),
    ("product_economics", "Producto y economia", "Servicios, subvenciones, residencias, mantenimiento y obra."),
    ("portfolio_publication", "Portafolio y publicacion", "Evidencia publica, pieza, dossier y trazabilidad."),
    ("existing_funding_lab", "Funding lab separado", "Consumidor adyacente de reglas y ledgers; no es parte del jardin."),
]

SEMANTICS = [
    ("discover", "descubrir", "idea o pregunta", "candidates", "candidate", "No afirmar existencia; registrar consulta y cobertura."),
    ("capture", "capturar", "URL o archivo", "source_snapshot", "source", "Conservar URL, hash, fecha y tipo de fuente."),
    ("extract", "extraer", "fuente capturada", "claims, entities, citations", "extracted_fact", "Marcar automatico y guardar evidencia exacta."),
    ("normalize", "normalizar", "entidad o termino", "canonical entity", "canonical_entity", "No inferir significado por similitud nominal."),
    ("relate", "relacionar", "entidades + evidencia", "typed relation", "inferred_relation", "Toda relacion necesita base, confianza y fuente."),
    ("contextualize", "contextualizar", "relacion + tiempo/lugar/dominio", "context", "contextualized_claim", "Separar el contexto de la interpretacion."),
    ("interpret", "interpretar", "contexto + correspondencia", "interpretation hypothesis", "hypothesis_or_metaphor", "Declarar correspondencia, quiebre y no-equivalencia."),
    ("simulate", "simular", "reglas + semilla + ambiente", "states and trajectories", "observed_model_result", "El comportamiento del modelo no prueba el mundo real."),
    ("validate", "validar", "claim, relation o experimento", "decision", "validated_or_uncertain", "Usar pass, fail o uncertain; nunca completar vacios con prosa."),
    ("curate", "curar", "material validado o incierto", "selection and decision", "curatorial_decision", "La seleccion humana queda separada de la extraccion automatica."),
    ("publish", "publicar", "seleccion + assets", "public work or dossier", "published_artifact", "Publicar evidencia suficiente sin exponer secretos ni datos privados."),
    ("audit", "auditar", "todos los eventos", "provenance ledger", "audit_event", "Cada salida debe poder volver a fuente, proceso y version."),
]

CORRELATIONS = [
    ("knowledge_model", "research_pipeline", "feeds", "claims and provenance become the memory of research", 0.98),
    ("analogy_interpretation", "garden_simulation", "maps_to", "an analogy can become a rule or field, never a fact", 0.95),
    ("garden_simulation", "visual_generation", "drives", "states and trajectories become visual behavior", 0.92),
    ("research_pipeline", "reference_tools", "selects", "tools are selected by pipeline stage and constraints", 0.93),
    ("risks_ethics", "domain_adapters", "constrains", "the substance domain requires hard safety and non-operationalization rules", 0.99),
    ("product_economics", "portfolio_publication", "proves", "public work and dossier provide evidence of a service", 0.84),
    ("portfolio_publication", "visual_generation", "exposes", "the portfolio presents the result, not the entire private corpus", 0.89),
    ("existing_funding_lab", "research_pipeline", "consumes", "funding-lab demonstrates deterministic rules and ledgers but stays separate", 0.81),
    ("domain_adapters", "knowledge_model", "instantiates", "plant, food and substance domains share a schema but retain local constraints", 0.91),
    ("analogy_interpretation", "risks_ethics", "limits", "metaphor needs a declared break point to avoid false equivalence", 0.96),
]

CONSTRAINTS = [
    ("evidence_levels", "global", "high", "Documented fact, automatic extraction, inferred relation, hypothesis, metaphor, curatorial decision and observed result are different types."),
    ("analogy_break_point", "interpretation", "high", "Every analogy declares correspondence, interpretation, break point, sources and uncertainty."),
    ("substance_harm", "domain_adapters", "critical", "Research about drugs or substances must not operationalize, normalize or optimize harmful use."),
    ("provenance_required", "global", "high", "Claims and relations without source or explicit status remain uncertain."),
    ("model_is_not_reality", "garden_simulation", "high", "A generative garden is a model of relations, not evidence of biological or social reality."),
    ("license_boundary", "reference_tools", "high", "A tool is a candidate until license, maintenance, platform and data restrictions are checked."),
    ("public_private_boundary", "portfolio_publication", "high", "Public outputs are derived artifacts; private raw sources and credentials stay outside publication."),
    ("funding_lab_boundary", "existing_funding_lab", "medium", "The paper trading/funding experiment is an adjacent consumer, not a semantic merge with cultural interpretation."),
]

EXTERNAL_RESEARCH = [
    ("Algorithmic Botany", "Su grupo declara como foco el modelado, la simulacion y la visualizacion de plantas, junto con herramientas para experimentos simulados.", "https://algorithmicbotany.org/", "official_page_reviewed"),
    ("OpenAlea", "La documentacion lo presenta como proyecto open source para investigacion de plantas, con bibliotecas para analizar, visualizar y modelar arquitectura y crecimiento.", "https://openalea.readthedocs.io/en/latest/", "official_docs_reviewed"),
    ("Wikidata", "Es una base secundaria, libre, colaborativa, multilingue y estructurada; registra afirmaciones, fuentes y conexiones con otras bases.", "https://www.wikidata.org/wiki/Wikidata:Introduction", "official_page_reviewed"),
    ("Semantic MediaWiki", "Agrega anotaciones semanticas a una wiki para buscar, organizar, consultar y reutilizar contenido como una base de datos colaborativa.", "https://www.semantic-mediawiki.org/wiki/Help:Introduction_to_Semantic_MediaWiki", "official_docs_reviewed"),
    ("nodegoat", "Se presenta como entorno web de investigacion para humanidades, con modelado propio, visualizaciones espacio-temporales y analisis de redes.", "https://nodegoat.net/", "official_page_reviewed"),
    ("Omeka S", "Su API ofrece operaciones de busqueda, lectura, creacion, actualizacion y eliminacion sobre recursos; por eso requiere una frontera explicita entre lecturas y mutaciones.", "https://omeka.org/s/docs/developer/api/", "official_docs_reviewed"),
    ("Gephi", "Es software libre y open source para explorar y manipular redes; sirve como referencia de visualizacion, no como base primaria de claims.", "https://gephi.org/", "official_page_reviewed"),
]

CLAIMS = [
    ("core_thesis", "documented_fact", "Jardines no propone otra wiki, dashboard o biblioteca de modelos; propone traducir fuentes tecnicas y culturales a interpretaciones visuales y generativas.", "document:thesis"),
    ("core_thesis", "documented_fact", "La infraestructura privada busca, lee, clasifica, relaciona, diagnostica y genera; la web publica funciona como vitrina.", "document:pipeline"),
    ("knowledge_model", "documented_fact", "El esquema comun declara source, claim, entity, relation, method, tool, constraint, license, confidence, interpretation, analogy, state y result.", "document:common-schema"),
    ("knowledge_model", "design_decision", "SQLite sera el registro local de procedencia y correlaciones; no se introduce un grafo externo como dependencia inicial.", "workflow:database"),
    ("analogy_interpretation", "documented_fact", "La analogia debe declarar correspondencia, interpretacion, punto de quiebre, fuentes e incertidumbre.", "document:analogy-contract"),
    ("analogy_interpretation", "hypothesis", "La analogia funciona como interfaz pedagogica cuando lleva desde una estructura conocida hacia un concepto desconocido y luego devuelve al concepto real.", "document:analogy-interface"),
    ("garden_simulation", "documented_fact", "El jardin modela environmental_field, lineage_seed, growth_rules, light_competition, mutation y decay hacia plant_form.", "document:garden-model"),
    ("garden_simulation", "design_decision", "Conviene almacenar reglas, semillas, campos, linajes, restricciones y trayectorias, no millones de plantas renderizadas.", "document:storage-rule"),
    ("garden_simulation", "hypothesis", "El motor de jardin puede servir como capa visual comun para relaciones biologicas, sociales y culturales si mantiene los limites de cada dominio.", "workflow:cross-domain-hypothesis"),
    ("domain_adapters", "documented_fact", "Plantas, alimentos y sustancias comparten la abstraccion entidad, estado, relacion, ambiente, transformacion y consecuencia.", "document:domains"),
    ("domain_adapters", "design_decision", "Los tres dominios deben ser adaptadores separados sobre un esquema comun, no una ontologia universal que borre diferencias.", "workflow:domain-adapters"),
    ("research_pipeline", "documented_fact", "El flujo propuesto es idea, verificar existencia, precedentes, herramientas, faltantes, licencias, decisiones, prototipo y registro del logro.", "document:research-flow"),
    ("research_pipeline", "design_decision", "Cada etapa debe emitir un tipo semantico propio y no convertir automaticamente una hipotesis en un hecho.", "workflow:stage-semantics"),
    ("visual_generation", "documented_fact", "La caja visual contempla curaduria de imagen, vision, ilustracion, animacion, SVG, simulacion, visualizaciones relacionales y web.", "document:visual-box"),
    ("visual_generation", "design_decision", "La generacion visual debe consumir estados y relaciones auditables, no solo un resumen textual.", "workflow:visual-consumer"),
    ("reference_tools", "documented_fact", "El documento separa modelado botanico, bases estructuradas, anotacion, grafos, simulacion y creative coding como familias de herramientas.", "document:references"),
    ("reference_tools", "design_decision", "La herramienta se clasifica por etapa, entrada, salida, licencia, mantenimiento y plataforma; el nombre no es criterio suficiente.", "workflow:tool-selection"),
    ("risks_ethics", "documented_fact", "Los riesgos declarados incluyen evidencia sin interpretacion, visualizacion sin pedagogia, analogias sin limite, IA opaca, sistemas estaticos y herramientas aisladas.", "document:risks"),
    ("risks_ethics", "design_decision", "Un resultado sin evidencia, incertidumbre o limite declarado no entra como afirmacion publica.", "workflow:publication-gate"),
    ("product_economics", "documented_fact", "Las salidas posibles incluyen investigacion visual a medida, exposiciones digitales, inteligencia preproyecto, comunicacion cientifica y cultural, motores, licencias, servicios, fondos y residencias.", "document:economics"),
    ("portfolio_publication", "documented_fact", "La propuesta de valor es convertir archivos y conocimiento especializado en experiencias visuales, contextuales y trazables.", "document:value"),
    ("existing_funding_lab", "documented_fact", "Funding-lab opera como torneo de hipotesis en papel con reglas deterministas y ledger; no debe confundirse con el motor interpretativo.", "local:funding-lab-readme"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def family_for_url(url: str) -> tuple[str, str, str]:
    host = url.split("/", 3)[2].lower()
    if "algorithmicbotany" in host:
        return "botanical_modeling", "Algorithmic Botany", "plant modeling and visualization"
    if "openalea" in host:
        return "botanical_modeling", "OpenAlea", "plant architecture modeling"
    if "groimp" in host:
        return "botanical_modeling", "GroIMP", "rule-based plant modeling"
    if "wikidata" in host:
        return "structured_knowledge", "Wikidata", "structured multilingual knowledge"
    if "semantic-mediawiki" in host:
        return "structured_knowledge", "Semantic MediaWiki", "semantic annotations in wiki pages"
    if "nodegoat" in host:
        return "research_database", "nodegoat", "research data modeling"
    if "recogito" in host:
        return "annotation", "Recogito", "text and map annotation"
    if "omeka" in host:
        return "digital_collections", "Omeka S", "digital collection API"
    if "scalar" in host:
        return "digital_publication", "Scalar", "media-rich publication"
    if "gephi" in host:
        return "graph_visualization", "Gephi", "network analysis and visualization"
    if "gama-platform" in host:
        return "simulation", "GAMA", "agent-based simulation"
    if "p5js" in host:
        return "creative_coding", "p5.js", "creative coding and web visualisation"
    return "reference", host, "reference source"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
            sha256 TEXT NOT NULL, captured_at TEXT NOT NULL, line_count INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, label TEXT NOT NULL,
            description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, kind TEXT NOT NULL,
            text TEXT NOT NULL, evidence_ref TEXT NOT NULL, confidence REAL NOT NULL,
            status TEXT NOT NULL, FOREIGN KEY(topic_id) REFERENCES topics(id)
        );
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY, canonical_name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL, domain TEXT NOT NULL,
            source_ref TEXT NOT NULL, confidence REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS claim_entities (
            claim_id INTEGER NOT NULL, entity_id INTEGER NOT NULL,
            role TEXT NOT NULL, PRIMARY KEY(claim_id, entity_id, role),
            FOREIGN KEY(claim_id) REFERENCES claims(id),
            FOREIGN KEY(entity_id) REFERENCES entities(id)
        );
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL,
            domain TEXT NOT NULL, time_scope TEXT NOT NULL,
            place_scope TEXT NOT NULL, notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY, subject_entity_id INTEGER NOT NULL,
            predicate TEXT NOT NULL, object_entity_id INTEGER NOT NULL,
            claim_id INTEGER, relation_type TEXT NOT NULL,
            confidence REAL NOT NULL, evidence_ref TEXT NOT NULL,
            FOREIGN KEY(subject_entity_id) REFERENCES entities(id),
            FOREIGN KEY(object_entity_id) REFERENCES entities(id),
            FOREIGN KEY(claim_id) REFERENCES claims(id)
        );
        CREATE TABLE IF NOT EXISTS interpretations (
            id INTEGER PRIMARY KEY, title TEXT UNIQUE NOT NULL,
            mechanism TEXT NOT NULL, correspondence TEXT NOT NULL,
            break_point TEXT NOT NULL, source_refs TEXT NOT NULL,
            uncertainty TEXT NOT NULL, status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY, entity_id INTEGER NOT NULL,
            state_name TEXT NOT NULL, environment TEXT NOT NULL,
            trajectory_ref TEXT NOT NULL, observed_or_simulated TEXT NOT NULL,
            FOREIGN KEY(entity_id) REFERENCES entities(id)
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY, interpretation_id INTEGER,
            result_text TEXT NOT NULL, evidence_kind TEXT NOT NULL,
            status TEXT NOT NULL, FOREIGN KEY(interpretation_id) REFERENCES interpretations(id)
        );
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, family TEXT NOT NULL,
            name TEXT NOT NULL, role TEXT NOT NULL, authority TEXT NOT NULL,
            verification_state TEXT NOT NULL, notes TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tools (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, family TEXT NOT NULL,
            role TEXT NOT NULL, input_type TEXT NOT NULL, output_type TEXT NOT NULL,
            license_state TEXT NOT NULL, platform_state TEXT NOT NULL,
            selection_state TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS process_semantics (
            id INTEGER PRIMARY KEY, process_key TEXT UNIQUE NOT NULL,
            label_es TEXT NOT NULL, input_semantics TEXT NOT NULL,
            output_semantics TEXT NOT NULL, output_kind TEXT NOT NULL,
            policy TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS correlations (
            id INTEGER PRIMARY KEY, left_topic_id INTEGER NOT NULL,
            right_topic_id INTEGER NOT NULL, relation TEXT NOT NULL,
            basis TEXT NOT NULL, confidence REAL NOT NULL,
            FOREIGN KEY(left_topic_id) REFERENCES topics(id),
            FOREIGN KEY(right_topic_id) REFERENCES topics(id)
        );
        CREATE TABLE IF NOT EXISTS constraints (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, scope TEXT NOT NULL,
            severity TEXT NOT NULL, rule_text TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY, hypothesis TEXT NOT NULL, method TEXT NOT NULL,
            inputs TEXT NOT NULL, expected TEXT NOT NULL, observed TEXT NOT NULL,
            status TEXT NOT NULL, rollback TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, object_type TEXT NOT NULL,
            object_id INTEGER, detail TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS domain_adapters (
            id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, label TEXT NOT NULL,
            description TEXT NOT NULL, input_examples TEXT NOT NULL,
            source_policy TEXT NOT NULL, constraint_policy TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS research_jobs (
            id INTEGER PRIMARY KEY, question TEXT NOT NULL, domain TEXT NOT NULL,
            adapter_id INTEGER NOT NULL, status TEXT NOT NULL,
            next_process TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(adapter_id) REFERENCES domain_adapters(id)
        );
        CREATE TABLE IF NOT EXISTS job_steps (
            id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL, step_order INTEGER NOT NULL,
            process_key TEXT NOT NULL, input_semantics TEXT NOT NULL,
            output_semantics TEXT NOT NULL, status TEXT NOT NULL,
            provider_policy TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES research_jobs(id)
        );
        CREATE TABLE IF NOT EXISTS job_relations (
            id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL, from_object TEXT NOT NULL,
            to_object TEXT NOT NULL, rationale TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES research_jobs(id)
        );
        CREATE TABLE IF NOT EXISTS job_sources (
            id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL,
            stage TEXT NOT NULL, query TEXT NOT NULL,
            discovery_provider TEXT NOT NULL, rank INTEGER NOT NULL,
            url TEXT NOT NULL, title TEXT NOT NULL, snippet TEXT NOT NULL,
            capture_provider TEXT NOT NULL, capture_status TEXT NOT NULL,
            http_status INTEGER, content_type TEXT NOT NULL,
            raw_sha256 TEXT NOT NULL, text_sha256 TEXT NOT NULL,
            text_path TEXT NOT NULL, captured_at TEXT NOT NULL,
            license_state TEXT NOT NULL, license_evidence TEXT NOT NULL,
            credits_estimate REAL NOT NULL, notes TEXT NOT NULL,
            UNIQUE(job_id, url), FOREIGN KEY(job_id) REFERENCES research_jobs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_job_sources_job ON job_sources(job_id);
        """
    )


def seed(conn: sqlite3.Connection, source_path: Path) -> int:
    text = source_path.read_text(encoding="utf-8", errors="replace")
    digest = sha256(source_path)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source_path.stem
    # This database is a derived projection, so regeneration is deterministic.
    # The source document and all external evidence remain untouched.
    for table in ("audit_events", "experiments", "results", "states", "interpretations",
                  "relations", "contexts", "claim_entities", "entities", "constraints",
                  "correlations", "process_semantics", "tools", "sources", "claims",
                  "topics", "documents"):
        conn.execute(f"DELETE FROM {table}")
    conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)", ("schema_version", SCHEMA_VERSION))
    conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)", ("source_path", str(source_path)))
    conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)", ("source_sha256", digest))
    conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)", ("generated_at", now_iso()))
    conn.execute("INSERT OR REPLACE INTO documents(path,title,sha256,captured_at,line_count) VALUES (?,?,?,?,?)",
                 (str(source_path), title, digest, now_iso(), len(text.splitlines())))

    topic_ids: dict[str, int] = {}
    for slug, label, description in TOPICS:
        conn.execute("INSERT OR IGNORE INTO topics(slug,label,description) VALUES (?,?,?)", (slug, label, description))
        topic_ids[slug] = conn.execute("SELECT id FROM topics WHERE slug=?", (slug,)).fetchone()[0]

    kind_confidence = {
        "documented_fact": (0.96, "documented"),
        "design_decision": (0.88, "proposed"),
        "hypothesis": (0.55, "hypothesis"),
    }
    for topic, kind, claim_text, evidence_ref in CLAIMS:
        confidence, status = kind_confidence[kind]
        conn.execute("INSERT INTO claims(topic_id,kind,text,evidence_ref,confidence,status) VALUES (?,?,?,?,?,?)",
                     (topic_ids[topic], kind, claim_text, evidence_ref, confidence, status))

    entity_specs = [
        ("source", "artifact", "global", "document:common-schema", 0.99),
        ("claim", "knowledge_unit", "global", "document:common-schema", 0.99),
        ("relation", "knowledge_unit", "global", "document:common-schema", 0.99),
        ("analogy", "interpretive_device", "cultural", "document:analogy-contract", 0.96),
        ("mycelium_network", "analogy_source", "plant", "document:analogy-interface", 0.78),
        ("light_competition", "model_variable", "plant", "document:garden-model", 0.94),
        ("growth_rules", "model_rule", "plant", "document:garden-model", 0.94),
        ("plant_form", "model_output", "plant", "document:garden-model", 0.94),
        ("interpretation", "curatorial_output", "cultural", "document:analogy-contract", 0.84),
    ]
    for row in entity_specs:
        conn.execute("INSERT INTO entities(canonical_name,entity_type,domain,source_ref,confidence) VALUES (?,?,?,?,?)", row)
    entity_ids = {row[0]: row[1] for row in conn.execute("SELECT canonical_name,id FROM entities")}
    claim_ids = {row[0]: row[1] for row in conn.execute("SELECT evidence_ref,id FROM claims")}
    for evidence_ref, name, role in (
        ("document:common-schema", "source", "field"),
        ("document:common-schema", "claim", "field"),
        ("document:common-schema", "relation", "field"),
        ("document:analogy-contract", "analogy", "subject"),
        ("document:analogy-interface", "mycelium_network", "object"),
        ("document:garden-model", "light_competition", "subject"),
        ("document:garden-model", "growth_rules", "subject"),
        ("document:garden-model", "plant_form", "object"),
    ):
        if evidence_ref in claim_ids:
            conn.execute("INSERT INTO claim_entities(claim_id,entity_id,role) VALUES (?,?,?)", (claim_ids[evidence_ref], entity_ids[name], role))
    conn.execute("INSERT INTO contexts(name,domain,time_scope,place_scope,notes) VALUES (?,?,?,?,?)", (
        "interpretive_garden_context", "cross_domain", "unspecified", "local_or_project_specific",
        "Context is a boundary around a relation; it is not the interpretation itself.",
    ))
    relation_specs = [
        ("mycelium_network", "illustrates", "relation", None, "inferred_relation", 0.72, "document:analogy-interface"),
        ("light_competition", "influences", "plant_form", claim_ids.get("document:garden-model"), "documented_model_rule", 0.94, "document:garden-model"),
        ("growth_rules", "produces", "plant_form", claim_ids.get("document:garden-model"), "documented_model_rule", 0.94, "document:garden-model"),
        ("analogy", "maps_to", "growth_rules", claim_ids.get("document:analogy-contract"), "interpretive_mapping", 0.60, "document:analogy-contract"),
    ]
    for subject, predicate, object_name, claim_id, relation_type, confidence, evidence_ref in relation_specs:
        conn.execute("INSERT INTO relations(subject_entity_id,predicate,object_entity_id,claim_id,relation_type,confidence,evidence_ref) VALUES (?,?,?,?,?,?,?)", (entity_ids[subject], predicate, entity_ids[object_name], claim_id, relation_type, confidence, evidence_ref))
    conn.execute("INSERT INTO interpretations(title,mechanism,correspondence,break_point,source_refs,uncertainty,status) VALUES (?,?,?,?,?,?,?)", (
        "mycelium_as_interface", "translate a network structure into a visual rule",
        "mycelium network -> connected growth behavior",
        "the visual analogy is not evidence that the modeled behavior is biological reality",
        "document:analogy-contract;document:analogy-interface", "medium", "hypothesis",
    ))
    interpretation_id = conn.execute("SELECT id FROM interpretations WHERE title='mycelium_as_interface'").fetchone()[0]
    conn.execute("INSERT INTO states(entity_id,state_name,environment,trajectory_ref,observed_or_simulated) VALUES (?,?,?,?,?)", (
        entity_ids["plant_form"], "uninstantiated", "interpretive_garden_context", "none", "not_observed",
    ))
    conn.execute("INSERT INTO results(interpretation_id,result_text,evidence_kind,status) VALUES (?,?,?,?)", (
        interpretation_id, "The model is registered; no visual prototype was executed in this phase.", "absence_of_execution", "pending_prototype",
    ))

    urls = sorted({u.rstrip(".,;:") for u in URL_RE.findall(text)})
    canonical_names: dict[str, str] = {}
    for url in urls:
        family, name, role = family_for_url(url)
        canonical_names[name] = family
        verification = "official_url_referenced"
        if any(token in url for token in (
            "algorithmicbotany.org/", "openalea.readthedocs.io/", "wikidata.org/",
            "semantic-mediawiki.org/", "nodegoat.net/", "recogito.pelagios.org/",
            "omeka.org/", "gephi.org/", "gama-platform.org/", "p5js.org/",
        )):
            verification = "official_page_reviewed_or_referenced"
        conn.execute(
            "INSERT OR REPLACE INTO sources(url,family,name,role,authority,verification_state,notes) VALUES (?,?,?,?,?,?,?)",
            (url, family, name, role, "official project or publication URL", verification,
             "Presence in the source document is evidence of a candidate reference, not proof of current suitability."),
        )

    tool_specs = [
        ("Algorithmic Botany", "botanical_modeling", "plant modeling and visualization", "plant rules and structures", "models and visual output"),
        ("OpenAlea", "botanical_modeling", "plant architecture analysis", "Python modules and plant data", "analysis and visualization"),
        ("GroIMP", "botanical_modeling", "rule-based 3D plant modeling", "rules and parameters", "3D plant structures"),
        ("Wikidata", "structured_knowledge", "structured multilingual reference", "items, properties and sources", "linked claims"),
        ("Semantic MediaWiki", "structured_knowledge", "semantic page annotations", "wiki pages and properties", "queryable annotations"),
        ("nodegoat", "research_database", "research data modeling", "entities, events and relations", "research database views"),
        ("Recogito", "annotation", "annotation and entity linking", "texts or maps", "annotated corpus"),
        ("Omeka S", "digital_collections", "collection and API layer", "items and metadata", "public collection API"),
        ("Scalar", "digital_publication", "nonlinear publication", "media and references", "contextual publication"),
        ("Gephi", "graph_visualization", "network exploration", "graph data", "network maps"),
        ("GAMA", "simulation", "agent-based simulation", "agents, environments and rules", "simulation trajectories"),
        ("p5.js", "creative_coding", "browser visual prototyping", "JavaScript and data", "interactive visual output"),
    ]
    for name, family, role, input_type, output_type in tool_specs:
        conn.execute(
            "INSERT OR REPLACE INTO tools(name,family,role,input_type,output_type,license_state,platform_state,selection_state) VALUES (?,?,?,?,?,?,?,?)",
            (name, family, role, input_type, output_type, "needs_project_specific_check", "candidate_not_runtime_dependency", "reference_candidate"),
        )

    for row in SEMANTICS:
        conn.execute("INSERT OR REPLACE INTO process_semantics(process_key,label_es,input_semantics,output_semantics,output_kind,policy) VALUES (?,?,?,?,?,?)", row)
    for left, right, relation, basis, confidence in CORRELATIONS:
        conn.execute("INSERT INTO correlations(left_topic_id,right_topic_id,relation,basis,confidence) VALUES (?,?,?,?,?)", (topic_ids[left], topic_ids[right], relation, basis, confidence))
    for row in CONSTRAINTS:
        conn.execute("INSERT OR REPLACE INTO constraints(name,scope,severity,rule_text) VALUES (?,?,?,?)", row)
    conn.execute("INSERT INTO experiments(hypothesis,method,inputs,expected,observed,status,rollback) VALUES (?,?,?,?,?,?,?)", (
        "Una misma pregunta puede recorrer fuente, claim, relacion, interpretacion y prototipo sin perder procedencia.",
        "Ejecutar este builder sobre el documento y consultar correlaciones por topic.",
        "JARDINES_INTERPRETATIVOS.md + URLs declaradas",
        "SQLite con fuentes, claims, semantica, correlaciones y restricciones.",
        "El resultado se valida con conteos y claves unicas; no es aun una prueba de calidad de cada fuente externa.",
        "observed_local_model",
        "Eliminar solo la base generada si se desea regenerar; el documento fuente permanece intacto.",
    ))
    conn.execute("INSERT INTO audit_events(event_type,object_type,object_id,detail,created_at) VALUES (?,?,?,?,?)", ("build", "document", 1, f"Seeded from {source_path} with {len(urls)} URLs", now_iso()))
    conn.commit()
    return len(urls)


def render_report(conn: sqlite3.Connection, output: Path, source_path: Path, url_count: int) -> None:
    meta = dict(conn.execute("SELECT key,value FROM metadata"))
    counts = {
        "topics": conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0],
        "claims": conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
        "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "tools": conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0],
        "entities": conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        "relations": conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
        "interpretations": conn.execute("SELECT COUNT(*) FROM interpretations").fetchone()[0],
        "states": conn.execute("SELECT COUNT(*) FROM states").fetchone()[0],
        "semantics": conn.execute("SELECT COUNT(*) FROM process_semantics").fetchone()[0],
        "correlations": conn.execute("SELECT COUNT(*) FROM correlations").fetchone()[0],
        "constraints": conn.execute("SELECT COUNT(*) FROM constraints").fetchone()[0],
    }
    lines = [
        "# Research y workflow: Jardines interpretativos",
        "",
        f"> Fuente analizada: `{source_path}`",
        f"> Generado: `{meta['generated_at']}` | schema `{SCHEMA_VERSION}` | SHA-256 `{meta['source_sha256']}`",
        "",
        "## Resultado ejecutivo",
        "",
        "Jardines interpretativos no debe implementarse como otra wiki, otro dashboard ni un chatbot de resumen. Su unidad de valor es una cadena trazable que convierte una fuente especializada en una interpretacion visual o generativa, declarando que es evidencia, que es inferencia, que es metafora y que fue decidido por curaduria.",
        "",
        "La arquitectura recomendada es un laboratorio local offline-first con SQLite como registro de procedencia, un pipeline por etapas y salidas separadas. La web y las piezas visuales consumen derivados validados; no son la base de verdad.",
        "",
        "## Separacion de temas",
        "",
        "| Tema | Funcion | No confundir con | Salida principal |",
        "|---|---|---|---|",
    ]
    for slug, label, description in TOPICS:
        lines.append(f"| `{slug}` | {label} | {description} | registros y decisiones del tema |")
    lines += [
        "",
        "### Limite importante: funding-lab",
        "",
        "`funding-lab` queda como consumidor adyacente. Su torneo de hipotesis, reglas deterministas y ledger pueden reutilizar el contrato de `source`, `claim`, `method`, `constraint` y `result`, pero no se fusiona semánticamente con plantas, analogias o generacion visual. Esta separacion evita que una logica financiera de papel sea interpretada como conocimiento cultural.",
        "",
        "## Semantica por proceso",
        "",
        "| Proceso | Entrada | Salida | Tipo | Regla |",
        "|---|---|---|---|---|",
    ]
    for row in conn.execute("SELECT process_key,label_es,input_semantics,output_semantics,output_kind,policy FROM process_semantics ORDER BY id"):
        lines.append("| `%s` (%s) | %s | %s | `%s` | %s |" % row)
    lines += [
        "",
        "## Correlaciones operativas",
        "",
        "Las correlaciones no significan que dos temas sean iguales. Son rutas de trabajo que deben conservar fundamento y confianza.",
        "",
        "| Desde | Hacia | Relacion | Base | Confianza |",
        "|---|---|---|---|---:|",
    ]
    query = """SELECT a.slug,b.slug,c.relation,c.basis,c.confidence
               FROM correlations c JOIN topics a ON a.id=c.left_topic_id
               JOIN topics b ON b.id=c.right_topic_id ORDER BY c.id"""
    for row in conn.execute(query):
        lines.append("| `%s` | `%s` | `%s` | %s | %.2f |" % row)
    lines += [
        "",
        "## Modelo de datos",
        "",
        "La base SQLite contiene `documents`, `sources`, `topics`, `claims`, `entities`, `relations`, `contexts`, `interpretations`, `states`, `results`, `tools`, `process_semantics`, `correlations`, `constraints`, `experiments` y `audit_events`. La forma minima de una afirmacion es:",
        "",
        "```text",
        "source -> claim -> entity/relation -> context -> interpretation -> state/result",
        "```",
        "",
        "El campo `kind` de `claims` es obligatorio: `documented_fact`, `design_decision` o `hypothesis`. El workflow puede ampliar luego a `automatic_extraction`, `inferred_relation`, `metaphor`, `curatorial_decision` y `observed_result` sin perder compatibilidad.",
        "",
        "## Herramientas: como entran al sistema",
        "",
        "Las referencias del documento quedan registradas como candidatos, no como dependencias instaladas. La seleccion real se hace por etapa, entrada, salida, licencia, plataforma, mantenimiento y restriccion. En esta primera corrida se conservaron todas las URLs declaradas para no perder genealogia.",
        "",
        "| Familia | Herramienta | Uso posible | Estado |",
        "|---|---|---|---|",
    ]
    for row in conn.execute("SELECT family,name,role,selection_state FROM tools ORDER BY family,name"):
        lines.append("| `%s` | %s | %s | `%s` |" % row)
    lines += [
        "",
        "## Contratos de seguridad y calidad",
        "",
    ]
    for name, scope, severity, rule_text in conn.execute("SELECT name,scope,severity,rule_text FROM constraints ORDER BY id"):
        lines.append(f"- **{name}** (`{scope}`, `{severity}`): {rule_text}")
    lines += [
        "",
        "## Verificacion externa inicial",
        "",
        "La revision web se limita a paginas oficiales o documentacion de cada proyecto. Esto confirma el rol declarado de la referencia, pero no autoriza instalarla ni la convierte en dependencia de MAK.",
        "",
        "| Referencia | Hallazgo | Estado | Fuente |",
        "|---|---|---|---|",
    ]
    for name, finding, url, state in EXTERNAL_RESEARCH:
        lines.append(f"| {name} | {finding} | `{state}` | {url} |")
    lines += [
        "",
        "## Workflow recomendado",
        "",
        "1. `discover`: recibir una idea y registrar consultas sin afirmar resultados.",
        "2. `capture`: guardar URL/archivo, fecha, hash y tipo de fuente.",
        "3. `extract`: separar claims, entidades y citas; cada extraccion conserva su evidencia.",
        "4. `normalize`: unificar nombres e identificadores sin inferir significado.",
        "5. `relate`: proponer relaciones tipadas con fundamento y confianza.",
        "6. `contextualize`: agregar tiempo, lugar, dominio y escala.",
        "7. `interpret`: formular analogia o hipotesis con correspondencia y punto de quiebre.",
        "8. `simulate`: convertir reglas y estados en trayectoria visual; registrar que es modelo.",
        "9. `validate`: aceptar, rechazar o dejar incierto; no rellenar vacios.",
        "10. `curate`: seleccionar lo que entra en una obra, dossier o propuesta.",
        "11. `publish`: exportar una pieza o portafolio derivado, sin exponer el corpus privado.",
        "12. `audit`: registrar versiones, fuentes, decisiones, resultados y rollback.",
        "",
        "## Orden de implementacion",
        "",
        "- **Primero:** SQLite + contratos de semantica + importacion de fuentes y claims.",
        "- **Despues:** correlaciones y busquedas por tema/dominio/estado/certeza.",
        "- **Luego:** adaptadores separados para plantas, alimentos y sustancias.",
        "- **Despues:** simulacion visual y exportacion a SVG/HTML/3D.",
        "- **Al final:** integraciones externas, scraping amplio y publicacion automatica.",
        "",
        "La primera prueba concreta no necesita APIs ni navegador: consultar la base, producir un mapa de precedentes y generar una interpretacion marcada como hipotesis. Solo cuando esa cadena sea auditable se conecta una herramienta visual o una fuente remota.",
        "",
        "## Conteo de esta corrida",
        "",
        "| Registro | Cantidad |",
        "|---|---:|",
    ]
    for key, value in counts.items():
        lines.append(f"| {key} | {value} |")
    lines += [
        f"| URLs extraidas del documento | {url_count} |",
        "",
        "## Archivos generados",
        "",
        "- `jardines_interpretativos.sqlite`: registro local consultable.",
        "- `jardines_interpretativos_correlations.csv`: correlaciones para inspeccion rapida.",
        "- `jardines_interpretativos_process_semantics.csv`: contrato de entradas/salidas.",
        "- `JARDINES_INTERPRETATIVOS_RESEARCH.md`: lectura humana y mapa de decisiones.",
        "",
        "## Limite de esta investigacion",
        "",
        "Esta corrida modela y ordena el documento completo y conserva sus referencias. No declara que cada herramienta externa este instalada, vigente, licenciada o adecuada para produccion. Ese es el siguiente gate: verificar fuente por fuente y luego probar solo los candidatos que tengan consumidor real en MAK.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


def export_csv(conn: sqlite3.Connection, output_dir: Path) -> None:
    specs = {
        "jardines_interpretativos_correlations.csv": (
            "SELECT a.slug AS left_topic,b.slug AS right_topic,c.relation,c.basis,c.confidence "
            "FROM correlations c JOIN topics a ON a.id=c.left_topic_id JOIN topics b ON b.id=c.right_topic_id ORDER BY c.id",
            ["left_topic", "right_topic", "relation", "basis", "confidence"],
        ),
        "jardines_interpretativos_process_semantics.csv": (
            "SELECT process_key,label_es,input_semantics,output_semantics,output_kind,policy FROM process_semantics ORDER BY id",
            ["process_key", "label_es", "input_semantics", "output_semantics", "output_kind", "policy"],
        ),
    }
    for filename, (query, headers) in specs.items():
        with (output_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(conn.execute(query))


def validate(conn: sqlite3.Connection) -> list[str]:
    required = ["metadata", "documents", "topics", "claims", "entities", "claim_entities", "contexts", "relations", "interpretations", "states", "results", "sources", "tools", "process_semantics", "correlations", "constraints", "experiments", "audit_events"]
    existing = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    errors = [f"missing table: {name}" for name in required if name not in existing]
    for table in ("topics", "claims", "entities", "relations", "interpretations", "states", "results", "sources", "process_semantics", "correlations", "constraints"):
        if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0:
            errors.append(f"empty table: {table}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("/home/mak/research/jardines_interpretativos"))
    args = parser.parse_args()
    source = args.source.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "jardines_interpretativos.sqlite"
    report_path = out_dir / "JARDINES_INTERPRETATIVOS_RESEARCH.md"
    with sqlite3.connect(db_path) as conn:
        create_schema(conn)
        url_count = seed(conn, source)
        errors = validate(conn)
        if errors:
            raise SystemExit("validation failed: " + "; ".join(errors))
        render_report(conn, report_path, source, url_count)
        export_csv(conn, out_dir)
        print(f"database={db_path}")
        print(f"report={report_path}")
        print(f"urls={url_count}")
        print("validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
