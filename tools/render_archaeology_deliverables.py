#!/usr/bin/env python3
"""Render bounded archaeology deliverables from an archaeology SQLite snapshot.

The extractor is intentionally deterministic. It reports lexical candidates
and evidence links, never psychological diagnoses or causal claims.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from flujo.diagnostics import redact_text  # noqa: E402

SCHEMA = "mak-archaeology-deliverables-v1"
CLOSURE_PATTERN = re.compile(
    r"(?i)(no queda(?: nada)? pendiente|no required action|"
    r"objective (?:is )?(?:complete|completed)|phase .*complete|"
    r"todo (?:esta|está) listo|ya (?:esta|está) listo|\bdone\b|"
    r"\bcomplet(?:o|a|ed|ion)\b)"
)
CORRECTION_PATTERN = re.compile(
    r"(?i)(error|bug|falla|fall[oó]|no funciona|te dije|no era|pendiente|"
    r"confund|malentend|otra vez|no hiciste)"
)
DOMAIN_TERMS = {
    "rd": ("rd", "rider", "plano", "venue", "cotizacion", "reactivo", "evento"),
    "portfolio": ("portafolio", "portfolio", "iskvw", "dominio", "cloudflare", "web"),
    "cultura": ("cultura", "obra", "arte", "ascii", "tilde", "psicosis", "3d"),
    "research": ("research", "scraping", "fondart", "fuente", "catalogo", "investigacion"),
    "core": ("mak", "hub", "git", "rama", "handoff", "agente", "diagnostico"),
}


def rows(conn: sqlite3.Connection, sql: str, args=()):
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(sql, args)]


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def pct(value: int, total: int) -> str:
    return "n/a" if not total else f"{100.0 * value / total:.1f}%"


def excerpt(value: str, limit: int = 240) -> str:
    return redact_text(value or "", limit).replace("\n", " ").strip()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def md_table(headers, records) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for record in records:
        lines.append("| " + " | ".join(str(item).replace("|", "\\|") for item in record) + " |")
    return lines


def write_report(out: Path, name: str, title: str, method: str,
                 confidence: str, omissions: list[str], body: list[str]) -> None:
    text = "\n".join([
        f"# {title}", "", f"- schema: `{SCHEMA}`", f"- generated_at_utc: `{iso_now()}`",
        f"- confidence: `{confidence}`", f"- method: {method}", "",
        "## Omissions and limits", "", *[f"- {item}" for item in omissions], "",
        *body,
    ]) + "\n"
    (out / name).write_text(text, encoding="utf-8")


def source_inventory(paths: list[Path]) -> list[dict]:
    result = []
    for root in paths:
        files = 0
        total = 0
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    files += 1
                    try:
                        total += path.stat().st_size
                    except OSError:
                        pass
        result.append({"root": str(root), "exists": root.exists(), "files": files,
                       "bytes": total, "sha256": "not_computed"})
    return result


def render_session_inventory(conn: sqlite3.Connection, out: Path,
                             source_paths: list[Path]) -> dict:
    total = count_rows(conn, "turns")
    duplicates = int(conn.execute("select count(*) from turns where is_duplicate=1").fetchone()[0])
    analysis = int(conn.execute("select count(*) from turns where is_duplicate=0 and analysis_exclusion is null").fetchone()[0])
    by_source = rows(conn, """
        select source, count(*) as raw,
               sum(case when is_duplicate=0 then 1 else 0 end) as unique_rows,
               sum(case when is_duplicate=0 and analysis_exclusion is null then 1 else 0 end) as analysis_rows,
               count(distinct source_file) as source_files
        from turns group by source order by source
    """)
    session_rows = rows(conn, "select source, count(*) as sessions, sum(human_turns) as human_turns, sum(assistant_turns) as assistant_turns from session_profiles group by source order by source")
    body = [
        "## Resultado", "",
        f"- turnos brutos: **{total:,}**",
        f"- duplicados exactos por fingerprint: **{duplicates:,}** ({pct(duplicates, total)})",
        f"- turnos únicos usados para análisis: **{analysis:,}**",
        "", "## Capas de conversación", "",
    ]
    body += md_table(["source", "raw", "unique", "analysis", "source_files"],
                     [[r["source"], r["raw"], r["unique_rows"], r["analysis_rows"], r["source_files"]] for r in by_source])
    body += ["", "## Sesiones", ""]
    body += md_table(["source", "sessions", "human_turns", "assistant_turns"],
                     [[r["source"], r["sessions"], r["human_turns"], r["assistant_turns"]] for r in session_rows])
    body += ["", "## Fuentes físicas observadas", ""]
    inv = source_inventory(source_paths)
    body += md_table(["root", "exists", "files", "bytes", "sha256"],
                     [[r["root"], r["exists"], r["files"], r["bytes"], r["sha256"]] for r in inv])
    write_report(out, "session_inventory.md", "Session inventory", "SQLite turns + filesystem metadata; fingerprints are computed for turns, raw source SHA-256 was not recomputed.", "high", ["Claude Code JSONL was absent from the selected recovered root; Claude web and Codex rollouts were available.", "Raw source hashes were not recomputed over the 5.1 GB Codex tree."], body)
    return {"turns": total, "duplicates": duplicates, "analysis_turns": analysis, "by_source": by_source, "sources": inv}


def render_question_ledger(conn: sqlite3.Connection, out: Path) -> dict:
    counts = rows(conn, "select status, count(*) as n from question_links group by status order by n desc")
    samples = rows(conn, """
        select q.status, t.source, t.session_id, t.occurred_at, t.source_file,
               t.source_line, t.text
        from question_links q join turns t on t.id=q.turn_id
        where t.is_duplicate=0 and t.analysis_exclusion is null
        order by case q.status when 'mechanically_unresolved' then 0 else 1 end, t.occurred_at
        limit 20
    """)
    total = sum(r["n"] for r in counts)
    body = ["## Conteo", ""] + md_table(["status", "count", "share"], [[r["status"], r["n"], pct(r["n"], total)] for r in counts])
    body += ["", "## Muestras recuperables", "", "No son conclusiones: son puntos de revisión con `source_file` y `source_line`.", ""]
    body += md_table(["status", "source", "occurred_at", "source_line", "excerpt"], [[r["status"], r["source"], r["occurred_at"], r["source_line"], excerpt(r["text"])] for r in samples])
    write_report(out, "question_ledger.md", "Question ledger", "question_links generated by deterministic turn linking; unanswered means no immediate mechanically linked response, not evasion.", "medium", ["3,698 questions require semantic interpretation; the extractor does not decide whether a response truly answered them.", "No psychological or intentional inference is made."], body)
    return {"counts": counts, "samples": [{**r, "text": excerpt(r["text"])} for r in samples]}


def idea_domain(text: str) -> str:
    folded = text.casefold()
    scores = {domain: sum(term in folded for term in terms) for domain, terms in DOMAIN_TERMS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "unclassified"


def render_idea_catalog(conn: sqlite3.Connection, out: Path) -> dict:
    records = rows(conn, "select id, turn_id, 0.5 as score, evidence, status from idea_followups order by id")
    items = []
    for record in records:
        try:
            evidence = json.loads(record["evidence"] or "{}")
        except ValueError:
            evidence = {}
        text = str(evidence.get("idea_text") or evidence.get("text") or "")
        items.append({"id": record["id"], "turn_id": record["turn_id"], "score": record["score"], "status": record["status"], "domain": idea_domain(text), "text": excerpt(text)})
    domain_counts = Counter(item["domain"] for item in items)
    body = ["## Clasificación provisional", "", "La clasificación de dominio es lexical y sirve para ordenar revisión; no convierte una semilla en proyecto.", ""]
    body += md_table(["domain", "count"], [[domain, count] for domain, count in domain_counts.most_common()])
    body += ["", "## Muestras de mayor score", ""]
    body += md_table(["id", "domain", "score", "text"], [[i["id"], i["domain"], i["score"], i["text"]] for i in items[:25]])
    write_report(out, "idea_catalog.md", "Idea catalog", "seed_candidates filtered to idea_candidate; domain labels are keyword candidates and status remains needs_semantic_link.", "medium", ["All 508 candidates remain `needs_semantic_link`; no candidate was promoted to project or product.", "Domain terms are a triage aid, not a semantic model."], body)
    return {"count": len(items), "domain_counts": dict(domain_counts), "samples": items[:25]}


def render_decision_graph(conn: sqlite3.Connection, out: Path) -> dict:
    counts = rows(conn, "select status, count(*) as n from proposal_followups group by status order by n desc")
    evidence = rows(conn, """
        select status, count(*) as n,
               sum(case when direct_action_count > 0 then 1 else 0 end) as direct_actions,
               sum(case when matching_commit_count > 0 then 1 else 0 end) as matching_commits,
               sum(case when approval_present > 0 then 1 else 0 end) as approvals
        from proposal_followups group by status order by n desc
    """)
    samples = rows(conn, """
        select p.status, p.source, p.proposal_timestamp, p.direct_action_count,
               p.matching_commit_count, substr(json_extract(p.evidence, '$.proposal_text'), 1, 220) as proposal_text
        from proposal_followups p order by p.matching_commit_count desc, p.direct_action_count desc, p.id limit 30
    """)
    body = ["## Nodos por estado", ""] + md_table(["status", "count"], [[r["status"], r["n"]] for r in counts])
    body += ["", "## Enlaces de evidencia", ""] + md_table(["status", "count", "direct_actions", "matching_commits", "approvals"], [[r["status"], r["n"], r["direct_actions"], r["matching_commits"], r["approvals"]] for r in evidence])
    body += ["", "## Muestras de nodos", ""] + md_table(["status", "source", "timestamp", "direct", "commits", "proposal"], [[r["status"], r["source"], r["proposal_timestamp"], r["direct_action_count"], r["matching_commit_count"], excerpt(r["proposal_text"])] for r in samples])
    write_report(out, "decision_graph.md", "Decision graph", "proposal_followups joined to direct Codex/Claude actions and lexical Git matches; edges are evidence candidates, not proof of causality.", "medium", ["376 proposals have approval without direct action evidence.", "Lexical commit matching can be false positive and is explicitly not treated as implementation proof.", "The graph preserves alternatives only where the source tool extracted them."], body)
    return {"status_counts": counts, "evidence": evidence, "samples": samples}


def parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def render_effort_report(conn: sqlite3.Connection, out: Path) -> dict:
    profiles = rows(conn, "select * from session_profiles")
    durations = []
    for row in profiles:
        start, end = parse_time(row["start"]), parse_time(row["end"])
        if start and end and end >= start:
            durations.append((end - start).total_seconds())
    turns = rows(conn, "select source, session_id, occurred_at from turns where is_duplicate=0 and analysis_exclusion is null and occurred_at is not null order by source, session_id, occurred_at")
    gaps = []
    previous = {}
    for turn in turns:
        stamp = parse_time(turn["occurred_at"])
        key = (turn["source"], turn["session_id"])
        if stamp and key in previous:
            delta = (stamp - previous[key]).total_seconds()
            if delta >= 0:
                gaps.append(delta)
        if stamp:
            previous[key] = stamp
    long_gaps = [x for x in gaps if x >= 3600]
    day_gaps = [x for x in gaps if x >= 86400]
    mode_counts = Counter(row["mode_candidate"] for row in profiles)
    body = ["## Proxies temporales", "", f"- sesiones: **{len(profiles)}**", f"- duración total de ventanas de sesión: **{sum(durations)/3600:.2f} h**", f"- duración mediana de sesión: **{statistics.median(durations)/60:.1f} min**" if durations else "- duración mediana: n/a", f"- intervalos entre turnos analizados: **{len(gaps):,}**", f"- pausas >= 1 h: **{len(long_gaps):,}**", f"- pausas >= 24 h: **{len(day_gaps):,}**", "", "## Modos candidatos", ""]
    body += md_table(["mode_candidate", "count"], [[k, v] for k, v in mode_counts.most_common()])
    body += ["", "## Interpretación permitida", "", "Estos son proxies de actividad y pausa. No equivalen a cansancio, valor artístico, intención ni productividad.", "", "## Energía y costo", "", "No calculado: la fuente `mak_activity` produjo 0 filas válidas porque la bitácora entregada no contiene `activity_id`. No se reemplaza ese vacío por una estimación."]
    write_report(out, "effort_report.md", "Effort report", "session windows and temporal gaps from unique analyzed turns; no energy inference.", "medium", ["Energy, electricity cost and machine telemetry were not available in the accepted activity schema.", "A pause is reported as an interval, never as a psychological state."], body)
    return {"sessions": len(profiles), "total_window_seconds": sum(durations), "median_seconds": statistics.median(durations) if durations else None, "gaps": len(gaps), "long_gaps": len(long_gaps), "day_gaps": len(day_gaps), "modes": dict(mode_counts)}


def render_closure_audit(conn: sqlite3.Connection, out: Path) -> dict:
    claims = rows(conn, """
        select source, session_id, occurred_at, source_file, source_line, text
        from turns where role='assistant' and is_duplicate=0 and analysis_exclusion is null
        order by occurred_at
    """)
    matched = [r for r in claims if CLOSURE_PATTERN.search(r["text"] or "")]
    corrections = 0
    correction_samples = []
    all_turns = rows(conn, "select id, role, occurred_at, text, source_file, source_line from turns where is_duplicate=0 and analysis_exclusion is null order by id")
    for index, row in enumerate(all_turns):
        if row["role"] != "assistant" or not CLOSURE_PATTERN.search(row["text"] or ""):
            continue
        following = all_turns[index + 1:index + 9]
        hit = next((item for item in following if item["role"] == "user" and CORRECTION_PATTERN.search(item["text"] or "")), None)
        if hit:
            corrections += 1
            if len(correction_samples) < 20:
                correction_samples.append({"closure": excerpt(row["text"]), "correction": excerpt(hit["text"]), "closure_source": row["source_file"], "correction_source": hit["source_file"]})
    body = ["## Resultado lexical", "", f"- afirmaciones candidatas de cierre del agente: **{len(matched):,}**", f"- cierres seguidos por una corrección del usuario en los 8 turnos siguientes: **{corrections:,}** ({pct(corrections, len(matched))})", "", "La segunda cifra es un hotspot de falsa clausura, no una acusación: requiere revisión contextual.", "", "## Muestras", ""]
    body += md_table(["closure", "correction"], [[r["closure"], r["correction"]] for r in correction_samples])
    write_report(out, "closure_audit.md", "Closure audit", "assistant lexical closure candidates cross-checked with nearby user correction/error language.", "low", ["Closure phrases are ambiguous and may be quoted, hypothetical or duplicated context.", "A nearby correction does not prove that the closure was false; it marks a review point.", "No intent, manipulation or emotion is inferred."], body)
    return {"closure_claims": len(matched), "followed_by_correction": corrections, "samples": correction_samples}


def render_triangulation_report(conn: sqlite3.Connection, out: Path) -> dict:
    total_turns = count_rows(conn, "turns")
    duplicate_turns = int(conn.execute("select count(*) from turns where is_duplicate=1").fetchone()[0])
    action_ok = int(conn.execute("select count(*) from codex_actions where result_status='ok'").fetchone()[0])
    action_total = count_rows(conn, "codex_actions")
    proposal_direct = int(conn.execute("select count(*) from proposal_followups where direct_action_count > 0").fetchone()[0])
    proposal_commit = int(conn.execute("select count(*) from proposal_followups where matching_commit_count > 0").fetchone()[0])
    findings = [
        ("duplicate_turns", "strong", f"{duplicate_turns:,} of {total_turns:,} raw turns have exact normalized fingerprints; deduplication is reproducible."),
        ("codex_file_actions", "medium", f"{action_ok:,} of {action_total:,} extracted Codex actions report ok; this proves an action record, not current runtime success."),
        ("proposal_to_action", "weak", f"{proposal_direct:,} proposals have direct-action candidates and {proposal_commit:,} have lexical commit matches; neither alone proves user-accepted integration."),
        ("lexical_hotspots", "weak", f"{count_rows(conn, 'signals'):,} lexical signals exist; they are candidate hotspots, not diagnoses."),
        ("mak_activity", "unverified", "The selected activity source yielded zero valid rows because its schema differs; energy and runtime effort remain unverified."),
    ]
    body = ["## Hallazgos triangulados", "", "Confidence means evidentiary strength, not truth of an interpretation.", ""]
    body += md_table(["finding", "confidence", "evidence"], findings)
    body += ["", "## Regla de lectura", "", "Un hallazgo fuerte necesita dos capas independientes: por ejemplo, registro conversacional más acción material, o fingerprint más fuente recuperable. Las señales lingüísticas por sí solas permanecen débiles."]
    write_report(out, "triangulation_report.md", "Triangulation report", "cross-check of turns, direct action records, proposal links, lexical signals and activity schema.", "medium", ["Git lexical matches are not treated as causal links.", "Claude memory and energy telemetry were unavailable in the selected snapshot.", "Raw WIN remains evidence and was not modified."], body)
    return {"findings": [{"finding": a, "confidence": b, "evidence": c} for a, b, c in findings]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-root", action="append", type=Path, default=[])
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.sqlite.resolve())
    try:
        results = {
            "session_inventory": render_session_inventory(conn, out, args.source_root),
            "question_ledger": render_question_ledger(conn, out),
            "idea_catalog": render_idea_catalog(conn, out),
            "decision_graph": render_decision_graph(conn, out),
            "effort_report": render_effort_report(conn, out),
            "closure_audit": render_closure_audit(conn, out),
            "triangulation_report": render_triangulation_report(conn, out),
        }
    finally:
        conn.close()
    manifest = {"schema": SCHEMA, "generated_at_utc": iso_now(), "sqlite": str(args.sqlite.resolve()), "outputs": sorted(path.name for path in out.glob("*.md")), "summary": results}
    (out / "analysis_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "files": manifest["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
