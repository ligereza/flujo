"""Portal visual gratuito para jefatura/solicitantes.

Genera un HTML estático, sin red ni dependencias, con estado de jobs y enlaces
opcionales a GitHub Issues. La idea es reemplazar herramientas tipo monday.com
con piezas gratuitas: GitHub Issues/Projects + dashboard exportable de flujo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable

from .jobs.brief import load_brief
from .jobs.job import list_jobs
from .jobs.lifecycle import suggest_next_action
from .paths import context_dir


BOARD_COLUMNS = [
    ("pendiente_datos", "Pendiente datos"),
    ("brief_extraido_pendiente_revision", "Por revisar"),
    ("listo_para_disenar", "Listo para diseñar"),
    ("en_diseno", "En diseño"),
    ("generado", "Generado / revisión"),
    ("entregado", "Entregado"),
]


@dataclass
class PortalJob:
    name: str
    path: str
    estado: str
    titulo: str
    cliente: str
    tipo_pieza: str
    medida: str
    pendientes: list[str]
    next_action: str


def _issue_url(repo_url: str, template: str = "") -> str:
    if not repo_url:
        return ""
    base = repo_url.rstrip("/")
    if template:
        return f"{base}/issues/new?template={template}"
    return f"{base}/issues/new/choose"


def collect_portal_jobs() -> list[PortalJob]:
    """Lee jobs locales y devuelve solo información segura/operativa."""
    rows: list[PortalJob] = []
    for info in list_jobs():
        brief_path = info.path / "brief.yaml"
        try:
            brief = load_brief(brief_path)
            medida = ""
            if brief.medidas.ancho_cm and brief.medidas.alto_cm:
                medida = f"{brief.medidas.ancho_cm:g} × {brief.medidas.alto_cm:g} cm"
            rows.append(
                PortalJob(
                    name=info.name,
                    path=str(info.path),
                    estado=brief.estado.value,
                    titulo=brief.proyecto or info.name,
                    cliente=brief.cliente,
                    tipo_pieza=brief.tipo_pieza,
                    medida=medida,
                    pendientes=list(brief.pendientes),
                    next_action=suggest_next_action(brief),
                )
            )
        except Exception:
            rows.append(
                PortalJob(
                    name=info.name,
                    path=str(info.path),
                    estado=info.estado or "error",
                    titulo=info.name,
                    cliente="",
                    tipo_pieza=info.tipo_pieza,
                    medida="",
                    pendientes=["Revisar brief.yaml"],
                    next_action="Revisar job manualmente",
                )
            )
    return rows


def _status_class(estado: str) -> str:
    if estado in ("pendiente_datos", "brief_extraido_pendiente_revision"):
        return "warn"
    if estado in ("en_diseno", "listo_para_disenar"):
        return "active"
    if estado in ("generado",):
        return "review"
    if estado in ("entregado",):
        return "done"
    return "neutral"


def render_portal_html(jobs: Iterable[PortalJob], repo_url: str = "", titulo: str = "Portal de pedidos") -> str:
    jobs = list(jobs)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(jobs)
    abiertos = sum(1 for j in jobs if j.estado not in ("entregado", "cancelado"))
    pendientes = sum(1 for j in jobs if j.pendientes)
    issue_new = _issue_url(repo_url, "pedido_diseno.yml")
    issue_change = _issue_url(repo_url, "cambio_diseno.yml")
    board = repo_url.rstrip("/") + "/projects" if repo_url else ""

    def job_card(job: PortalJob) -> str:
        pending = "".join(f"<li>{escape(p)}</li>" for p in job.pendientes[:4])
        pending_html = f"<ul>{pending}</ul>" if pending else "<p class='ok'>Sin pendientes visibles.</p>"
        meta = " · ".join(x for x in [job.tipo_pieza, job.medida, job.cliente] if x)
        return f"""
        <article class="job {_status_class(job.estado)}">
          <div class="job-top">
            <span class="pill">{escape(job.estado)}</span>
            <span class="job-id">{escape(job.name)}</span>
          </div>
          <h3>{escape(job.titulo)}</h3>
          <p class="meta">{escape(meta or 'Sin metadata')}</p>
          <details>
            <summary>Ver pendientes / próxima acción</summary>
            {pending_html}
            <p><b>Próxima acción:</b> {escape(job.next_action)}</p>
          </details>
        </article>
        """

    sections = []
    for status, label in BOARD_COLUMNS:
        group = [j for j in jobs if j.estado == status]
        cards = "".join(job_card(j) for j in group) or "<p class='empty'>Sin pedidos en esta etapa.</p>"
        sections.append(f"<section class='col'><h2>{escape(label)} <small>{len(group)}</small></h2>{cards}</section>")
    other = [j for j in jobs if j.estado not in {s for s, _ in BOARD_COLUMNS}]
    if other:
        sections.append(f"<section class='col'><h2>Otros <small>{len(other)}</small></h2>{''.join(job_card(j) for j in other)}</section>")

    actions = ""
    if issue_new or issue_change or board:
        actions = "<nav class='actions'>"
        if issue_new:
            actions += f"<a href='{escape(issue_new)}'>Nuevo pedido</a>"
        if issue_change:
            actions += f"<a href='{escape(issue_change)}'>Pedir cambio</a>"
        if board:
            actions += f"<a href='{escape(board)}'>Ver tablero GitHub</a>"
        actions += "</nav>"

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)} · flujo</title>
<style>
:root {{
  --bg:#12001f; --panel:#2b0a3d; --card:#f5e8ff; --ink:#17051f; --muted:#6b5b78;
  --accent:#6d28d9; --warn:#f59e0b; --active:#a855f7; --review:#7c3aed; --done:#22c55e;
}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:#fff}}
header{{padding:28px 28px 18px;background:linear-gradient(135deg,#101412,#1b2822)}}
h1{{margin:0;font-size:clamp(1.8rem,4vw,3.2rem);letter-spacing:-.04em}}
header p{{margin:.4rem 0 0;color:#cfc7ba}}
.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}}
.actions a{{background:var(--card);color:var(--ink);text-decoration:none;border-radius:999px;padding:10px 14px;font-weight:800}}
.actions a:first-child{{background:#d8f3df}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;padding:18px 28px;background:#0b0d0c}}
.stat{{background:var(--panel);padding:16px;border-radius:18px;border:1px solid rgba(255,255,255,.07)}}
.stat b{{display:block;font-size:2rem;color:#f6efe3}}
.board{{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(290px,1fr);gap:14px;overflow-x:auto;padding:22px 28px 34px}}
.col{{background:var(--panel);border:1px solid rgba(255,255,255,.08);border-radius:22px;padding:14px;min-height:420px}}
.col h2{{margin:0 0 12px;font-size:1rem;text-transform:uppercase;letter-spacing:.08em;color:#e8dfd0}}
.col h2 small{{color:#a9a195}}
.job{{background:var(--card);color:var(--ink);border-radius:18px;padding:14px;margin:0 0 12px;border-left:7px solid #999;box-shadow:0 10px 30px rgba(0,0,0,.22)}}
.job.warn{{border-left-color:var(--warn)}} .job.active{{border-left-color:var(--active)}} .job.review{{border-left-color:var(--review)}} .job.done{{border-left-color:var(--done)}}
.job-top{{display:flex;align-items:center;justify-content:space-between;gap:10px}}
.pill{{font-size:.72rem;font-weight:900;background:#111;color:#fff;border-radius:999px;padding:4px 8px}}
.job-id{{font-size:.72rem;color:var(--muted);word-break:break-all;text-align:right}}
.job h3{{margin:10px 0 5px;font-size:1.05rem;letter-spacing:-.02em}}
.meta{{margin:0 0 10px;color:var(--muted)}}
details{{border-top:1px solid rgba(0,0,0,.1);padding-top:8px}}
summary{{cursor:pointer;font-weight:800}}
ul{{padding-left:1.1rem}} .ok{{color:#276b46;font-weight:800}} .empty{{color:#aaa}}
footer{{padding:20px 28px;color:#aaa;border-top:1px solid rgba(255,255,255,.08)}}
</style>
</head>
<body>
<header>
  <h1>{escape(titulo)}</h1>
  <p>Vista simple para jefatura/solicitantes · actualizado {escape(now)} · sin monday.com · fuente: jobs locales de flujo.</p>
  {actions}
</header>
<div class="stats">
  <div class="stat"><b>{total}</b>Total pedidos</div>
  <div class="stat"><b>{abiertos}</b>Abiertos</div>
  <div class="stat"><b>{pendientes}</b>Con pendientes</div>
  <div class="stat"><b>{sum(1 for j in jobs if j.estado == 'entregado')}</b>Entregados</div>
</div>
<main class="board">
  {''.join(sections)}
</main>
<footer>
  Para cambios: usar “Pedir cambio” o comentar el issue del pedido. Este portal no muestra el texto original completo para reducir exposición de datos.
</footer>
</body>
</html>
"""


def export_portal(output: Path | None = None, repo_url: str = "", titulo: str = "Portal de pedidos") -> Path:
    """Escribe el portal HTML y retorna su ruta."""
    out = output or (context_dir() / "portal_jefe.html")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_portal_html(collect_portal_jobs(), repo_url=repo_url, titulo=titulo), encoding="utf-8")
    return out
