"""CLI unificada de flujo — Typer.

Completa: jobs, privacy, render, dashboard, intake, flyer, airdrop, etc.
La versión se centraliza en `flujo.version` (ver `flujo version`).

Comandos disponibles (ejecutar `flujo --help`):
  salud / info
    health                      Chequeo general del repo
    version                     Versión y changelog
  intake / flyers
    flyer-import                Importar flyers desde correo (links IG)
    ig-redownload               Reintentar descargas fallidas de IG
    analyze                     Analizar proyecto(s) flyer
    export                      Exportar ZIP listo para PS/AI
  index / db
    index                       Reconstruir/consultar índice SQLite de flyers
    flyer-list                  Listar flyers
  jobs
    job-new                     Crear job desde texto/correo
    job-prepare                 Pipeline: privacidad → brief → estado
    job-list                    Listar jobs y estados
    job-status <path>           Estado de un job específico
    job-next                    Próximas acciones sugeridas por job
    job-activate                brief → proyecto en projects/piezas_vectoriales/
    job-report <path>           Reporte detallado de un job
  privacy
    privacy-scan <archivo>      Escanear un texto
    privacy-sanitize <archivo>  Sanitizar texto → [EMAIL], [RUT], etc.
  brief
    brief-extract <job>         Re-extraer brief desde texto del job
    brief-to-project <brief>    Convertir brief.yaml en proyecto
    brief-show <brief>          Mostrar brief en formato legible
  render
    render <config.json>        Renderizar proyecto piezas_vectoriales
    validate <config.json>      Validar config.json
    formats [w h tipo]          Listar o sugerir formatos/plantillas
  dashboard
    daily                       Generar reporte diario (md + html)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


from .version import get_version as _get_pkg_version

app = typer.Typer(
    add_completion=False,
    help=f"flujo — Dimensiones del Orden · v{_get_pkg_version()}",
    no_args_is_help=True,
)
console = Console()


# ============================================================
# Sub-apps
# ============================================================

job_app = typer.Typer(help="Gestión de jobs y briefs.", no_args_is_help=True)
privacy_app = typer.Typer(help="Privacidad para textos antes de IA externa.", no_args_is_help=True)
brief_app = typer.Typer(help="Operaciones sobre briefs.", no_args_is_help=True)
render_app = typer.Typer(help="Render y validación de piezas vectoriales.", no_args_is_help=True)
airdrop_app = typer.Typer(help="Sistema de actualización profesional (airdrops).", no_args_is_help=True)

app.add_typer(job_app, name="job")
app.add_typer(privacy_app, name="privacy")
app.add_typer(brief_app, name="brief")
app.add_typer(render_app, name="render")
app.add_typer(airdrop_app, name="airdrop")


# ============================================================
# Helpers
# ============================================================

def _err(msg: str) -> None:
    console.print(f"[red]Error:[/] {msg}")
    raise typer.Exit(1)


def _ok(msg: str) -> None:
    console.print(f"[green]✓[/] {msg}")


def _warn(msg: str) -> None:
    console.print(f"[yellow]⚠[/] {msg}")


def _section(title: str) -> None:
    console.print()
    console.print(Panel(f"[bold cyan]{title}[/]", border_style="cyan"))


# ============================================================
# Airdrop
# ============================================================

@airdrop_app.command("status")
def airdrop_status():
    """Muestra la versión actual del sistema flujo."""
    from .version import get_version
    v = get_version()
    console.print(f"\n[bold cyan]flujo version actual:[/] [bold]{v}[/]\n")


@airdrop_app.command("list")
def airdrop_list():
    """Lista los archivos pendientes de aplicar en _airdrop/."""
    from .airdrop import list_airdrop_files
    files = list_airdrop_files()
    if not files:
        _warn("No hay archivos pendientes en _airdrop/")
        return
    _section("Archivos en _airdrop/ (pendientes de aplicar)")
    for rel in files:
        console.print(f"  · [bold cyan]{rel}[/]")


@airdrop_app.command("dry-run")
def airdrop_dry_run():
    """Simula la aplicación del airdrop sin realizar cambios."""
    from .airdrop import scan_airdrop
    try:
        changes = scan_airdrop()
        if not changes:
            _warn("No hay archivos pendientes en _airdrop/")
            return
        _section("Simulación de Airdrop (_airdrop/)")
        for c in changes:
            color = "green" if c["status"] == "NEW" else "yellow"
            console.print(f"  [{color}]{c['status']:<8}[/] {c['rel']}")
        console.print(f"\n[bold]Total: {len(changes)} archivos serían afectados.[/]")
    except Exception as e:
        _err(str(e))


@airdrop_app.command("apply")
def airdrop_apply(
    message: Optional[str] = typer.Argument(
        None, help="Mensaje del checkpoint (ej. 'fix airdrop cli')"
    ),
):
    """Aplica los archivos de _airdrop/, crea backup y dispara checkpoint + push."""
    from .airdrop import apply_airdrop, run_auto_checkpoint
    try:
        changes = apply_airdrop()
        if not changes:
            _warn("No hay archivos pendientes en _airdrop/")
            return

        _section("Airdrop Aplicado")
        for c in changes:
            console.print(f"  [green]✓[/] {c['rel']}")

        _ok("Archivos aplicados exitosamente.")

        # --- AUTOMATIZACIÓN: backup -> apply -> checkpoint -> push ---
        console.print("\n[cyan]Ejecutando auto-checkpoint y push...[/]")
        if run_auto_checkpoint(message):
            _ok("Checkpoint creado y cambios subidos al servidor.")
        else:
            _warn("No se pudo realizar el auto-checkpoint. Por favor, hazlo manualmente.")

        _section("Proceso Completado")
        console.print("[bold green]Airdrop está activo y sincronizado.[/]")

    except Exception as e:
        _err(str(e))


@airdrop_app.command("rollback")
def airdrop_rollback():
    """Revierte los cambios al último backup de airdrop."""
    from .airdrop import rollback_last
    backup = rollback_last()
    if not backup:
        _err("No se encontró ningún backup para revertir.")
    _ok(f"Rollback completado desde: {backup.name}")


@airdrop_app.command("finish")
def airdrop_finish():
    """Finaliza el proceso de airdrop (estatus y sugerencias)."""
    _section("Finalización de Airdrop")
    import subprocess
    try:
        # Usar git status --short para mostrar cambios
        res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        console.print(res.stdout if res.stdout else "No hay cambios pendientes en git.")
    except Exception:
        _warn("No se pudo ejecutar git status.")

    console.print("\n[bold cyan]Pasos recomendados:[/]")
    console.print("  1. Revisar cambios: [bold]git diff[/]")
    console.print("  2. Hacer checkpoint: [bold]bash scripts/checkpoint.sh \"vX.YZ - descripción\"[/]")
    console.print("  3. Commit y push.")


# ============================================================
# Salud / info
# ============================================================

@app.command("health")
def health():
    """Chequeo general del repo."""
    from .paths import repo_root
    from .intake.email_parser import extract_instagram_links
    from .jobs.job import list_jobs
    from .jobs.lifecycle import suggest_next_action
    from .jobs.brief import load_brief

    root = repo_root()
    _section("flujo · health check")

    console.print(f"[cyan]Repo root:[/] {root}")
    console.print(f"[cyan]Versión:[/] {_get_version()}")
    console.print()

    # existence checks
    required = ["jobs", "inbox", "projects", "scripts", "tools", "docs"]
    for sub in required:
        path = root / sub
        status = "[green]OK[/]" if path.exists() else "[yellow]falta[/]"
        console.print(f"  {sub:<12} {status}")

    # jobs
    jobs = list_jobs()
    console.print(f"\n[cyan]Jobs:[/] {len(jobs)}")
    for j in jobs[:5]:
        console.print(f"  · {j.name} [{j.estado}] ({j.pendientes} pendientes)")

    # indices
    db = root / "data" / "flujo.db"
    if db.exists():
        console.print(f"\n[cyan]Index:[/] {db}")
    else:
        _warn("Index no existe. Ejecutar: flujo index --rebuild")


@app.command()
def version():
    """Muestra versión y changelog."""
    from .version import get_version, get_changelog
    v = get_version()
    _section(f"flujo · versión {v}")
    changelog = get_changelog()
    for ver, info in changelog.items():
        console.print(f"\n[bold cyan]v{ver}[/] — {info['titulo']} ({info['fecha']})")
        for h in info.get("highlights", []):
            console.print(f"  · {h}")


def _get_version() -> str:
    from .version import get_version
    return get_version()


# ============================================================
# Flyers / Instagram
# ============================================================

@app.command("flyer-import")
def flyer_import(email: Path = typer.Argument(..., help="ruta a correo.txt")):
    """Importar flyers desde correo con links de Instagram."""
    from .flyer.import_email import import_from_email
    if not email.exists():
        _err(f"No existe: {email}")
    res = import_from_email(email)
    _ok(f"Flyers creados: {res['created']} | Omitidos: {res['skipped']} | Links: {res['found']}")


@app.command("ig-redownload")
def ig_redownload(
    project: Optional[Path] = typer.Argument(None, help="proyecto flyer específico"),
    all_projects: bool = typer.Option(False, "--all", help="reintentar todos"),
):
    """Reintentar descarga de posts de Instagram que fallaron."""
    from .paths import flyer_base
    from .ig.download import download_post
    from .manifest import load_json, write_json

    base = flyer_base()
    if not base.exists():
        _err(f"No existe: {base}")

    targets = []
    if project:
        if not (project / "manifest.json").exists():
            _err(f"No es un proyecto flyer válido: {project}")
        targets = [project]
    else:
        for d in base.iterdir():
            if not d.is_dir() or not (d / "manifest.json").exists():
                continue
            targets.append(d)

    if not targets:
        _warn("No hay proyectos flyer.")
        return

    reintentos = 0
    ok = 0
    for p in targets:
        data = load_json(p / "manifest.json") or {}
        ig = data.get("instagram", {})
        if ig.get("download_status") == "downloaded":
            continue
        url = ig.get("url")
        if not url:
            continue
        reintentos += 1
        console.print(f"  · {p.name}: {url}")
        try:
            res = download_post(url, p / "input", retries=1)
            if res.get("status") == "downloaded":
                ig.update({
                    "download_status": "downloaded",
                    "manual_download_possible": False,
                    "media_type": res.get("media_type", ""),
                    "file_count": res.get("file_count", 0),
                    "owner": res.get("owner", ""),
                    "date_utc": res.get("date", ""),
                })
                data["instagram"] = ig
                write_json(p / "manifest.json", data)
                ok += 1
                _ok(f"  descargado: {p.name}")
            else:
                _warn(f"  fallo: {res.get('reason', '?')}")
        except Exception as e:
            _warn(f"  error: {e}")

    _section(f"Resultado: {ok} re-descargados de {reintentos} intentos")


@app.command()
def analyze(
    project: Optional[Path] = typer.Argument(None, help="proyecto flyer a analizar"),
    all_projects: bool = typer.Option(False, "--all", help="analizar todos"),
    force_ocr: bool = typer.Option(False, "--force-ocr", help="forzar OCR"),
):
    """Analizar colores dominantes y OCR de un proyecto flyer."""
    from .analyze.run import analyze_project, find_latest_flyer
    from .paths import flyer_base

    target = None
    if all_projects:
        base = flyer_base()
        targets = sorted([p for p in base.iterdir() if (p / "manifest.json").exists()], reverse=True)
        _section(f"Analizando {len(targets)} proyectos")
        for t in targets:
            res = analyze_project(t, force_ocr=force_ocr)
            palette = res.get("palette", {})
            colors = palette.get("colors", [])
            console.print(f"  · [cyan]{t.name}[/]: {len(colors)} colores")
        return
    else:
        target = project or find_latest_flyer()
        if not target:
            _err("No hay proyectos flyer. Crear con: flujo flyer-import")
        res = analyze_project(target, force_ocr=force_ocr)
        _section(f"Análisis: {target.name}")
        console.print(f"  status: {res.get('status')}")
        for c in res.get("palette", {}).get("colors", []):
            console.print(f"  · [bold]{c['hex']}[/] ({c['pct']*100:.1f}%)")
        if res.get("ocr", {}).get("available"):
            console.print(f"  · OCR chars: {res['ocr'].get('chars', 0)}")


@app.command()
def export(
    project: Path = typer.Argument(..., help="ruta al proyecto"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    """Exportar ZIP listo para Photoshop/Illustrator."""
    from .export.zipper import export_flyer
    if not (project / "manifest.json").exists():
        _err(f"No es un proyecto flyer válido: {project}")
    try:
        zip_path = export_flyer(project, output)
        _ok(f"ZIP: {zip_path}")
    except Exception as e:
        _err(str(e))


# ============================================================
# Index
# ============================================================

@app.command()
def index(
    rebuild: bool = typer.Option(False, "--rebuild", help="reconstruir índice"),
    duplicates: bool = typer.Option(False, "--duplicates", help="mostrar duplicados"),
):
    """Reconstruir o consultar el índice SQLite de flyers."""
    from .index.db import rebuild_index, find_duplicates, list_flyers

    if rebuild:
        res = rebuild_index()
        _ok(f"Indexados: {res['indexed']} flyers")
    elif duplicates:
        dups = find_duplicates()
        if not dups:
            _ok("Sin duplicados.")
        else:
            for d in dups:
                _warn(f"shortcode {d['shortcode']}: {d['c']} proyectos")
                for p in d["paths"].split("|"):
                    console.print(f"    {p}")
    else:
        rows = list_flyers(limit=50)
        table = Table(title=f"Flyers ({len(rows)})")
        for col in ("name", "shortcode", "owner", "status", "media_type"):
            table.add_column(col)
        for r in rows:
            table.add_row(
                str(r.get("name", ""))[:40],
                str(r.get("shortcode", ""))[:20],
                str(r.get("owner", ""))[:20],
                str(r.get("status", "")),
                str(r.get("media_type", "")),
            )
        console.print(table)


@app.command("flyer-list")
def flyer_list(
    status: Optional[str] = typer.Option(None, "--status", help="filtrar por status"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Listar flyers indexados."""
    from .index.db import list_flyers
    rows = list_flyers(status=status, limit=limit)
    table = Table(title=f"Flyers (status={status or '*'})")
    for col in ("name", "shortcode", "owner", "status", "media_type", "date_utc"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r.get("name", ""))[:40],
            str(r.get("shortcode", ""))[:20],
            str(r.get("owner", ""))[:20],
            str(r.get("status", "")),
            str(r.get("media_type", "")),
            str(r.get("date_utc", ""))[:10],
        )
    console.print(table)


# ============================================================
# Jobs
# ============================================================

@job_app.command("new")
def job_new(
    name: str = typer.Argument(..., help="nombre del pedido"),
    email: Optional[Path] = typer.Option(None, "--email", "-e", help="archivo de correo/texto fuente"),
):
    """Crear un nuevo job desde un nombre (y opcionalmente texto fuente)."""
    from .jobs.job import create_job
    job = create_job(name, source_path=email)
    _ok(f"Job creado: {job}")
    console.print(f"  Siguiente: [cyan]flujo job prepare {job}[/]")


@job_app.command("prepare")
def job_prepare(
    job: Path = typer.Argument(..., help="ruta al job"),
    no_privacy: bool = typer.Option(False, "--no-privacy", help="omitir paso de privacidad"),
):
    """Pipeline: privacidad → brief → estado."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = prepare_job(job, run_privacy=not no_privacy)
    if not res.ok:
        for e in res.errors:
            _warn(e)
    _section(f"Job: {job.name}")
    console.print(f"  estado inicial: {res.estado_inicial.value}")
    console.print(f"  estado final:   [bold]{res.estado_final.value}[/]")
    if res.privacy_report:
        console.print(f"  privacy_report: {res.privacy_report}")
    for s in res.steps:
        console.print(f"  · {s}")


@job_app.command("list")
def job_list(
    examples: bool = typer.Option(False, "--examples", help="incluir _examples"),
    status: Optional[str] = typer.Option(None, "--status", help="filtrar por estado"),
):
    """Listar jobs y sus estados."""
    from .jobs.job import list_jobs
    items = list_jobs(include_examples=examples)
    if status:
        items = [j for j in items if j.estado == status]
    if not items:
        _warn("No hay jobs.")
        return
    table = Table(title=f"Jobs ({len(items)})")
    for col in ("name", "estado", "tipo", "proyecto", "pendientes"):
        table.add_column(col)
    for j in items:
        table.add_row(j.name, j.estado, j.tipo_pieza or "?", j.proyecto or "?", str(j.pendientes))
    console.print(table)


@job_app.command("status")
def job_status_cmd(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Estado detallado de un job."""
    from .jobs.brief import load_brief
    from .jobs.lifecycle import suggest_next_action
    if not job.exists():
        _err(f"No existe: {job}")
    brief_path = job / "brief.yaml"
    if not brief_path.exists():
        _err(f"No hay brief.yaml en {job}")
    brief = load_brief(brief_path)
    _section(f"Job: {job.name}")
    console.print(f"  estado:        [bold]{brief.estado.value}[/]")
    console.print(f"  cliente:       {brief.cliente or '-'}")
    console.print(f"  proyecto:      {brief.proyecto or '-'}")
    console.print(f"  tipo_pieza:    {brief.tipo_pieza or '-'}")
    console.print(f"  medida:        {brief.medidas.ancho_cm or '?'}x{brief.medidas.alto_cm or '?'} cm")
    console.print(f"  productos:     {', '.join(brief.productos) or '-'}")
    console.print(f"  texto_aprobado: {brief.contenido.texto_aprobado}")
    console.print(f"  pendientes:    {len(brief.pendientes)}")
    for p in brief.pendientes:
        console.print(f"    · {p}")
    console.print(f"  próxima:       {suggest_next_action(brief)}")


@job_app.command("next")
def job_next():
    """Próximas acciones sugeridas para cada job."""
    from .jobs.job import list_jobs
    from .jobs.brief import load_brief
    from .jobs.lifecycle import suggest_next_action
    items = list_jobs()
    if not items:
        _warn("No hay jobs.")
        return
    for j in items:
        brief_path = j.path / "brief.yaml"
        try:
            brief = load_brief(brief_path)
            suggestion = suggest_next_action(brief)
        except Exception:
            suggestion = "revisar brief.yaml"
        console.print(f"  · [cyan]{j.name}[/] [{j.estado}] → {suggestion}")


@job_app.command("activate")
def job_activate(
    job: Path = typer.Argument(..., help="ruta al job"),
    project_name: Optional[str] = typer.Option(None, "--name", "-n"),
    template: Optional[str] = typer.Option(None, "--template", "-t"),
):
    """brief → proyecto en projects/piezas_vectoriales/."""
    from .jobs.lifecycle import activate_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = activate_job(job, project_name=project_name, template=template)
    if not res.ok:
        for e in res.errors:
            _warn(e)
        _err("No se pudo activar el job.")
    _section(f"Job activado: {job.name}")
    if res.project_path:
        _ok(f"Proyecto: {res.project_path}")
        console.print(f"  Siguiente: [cyan]flujo render {res.project_path / 'config.json'}[/]")


@job_app.command("report")
def job_report(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Generar reporte detallado de un job."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    # prepare_job también escribe reporte_job.md
    res = prepare_job(job, run_privacy=False, run_brief_extract=False)
    rep = job / "reporte_job.md"
    if rep.exists():
        _ok(f"Reporte: {rep}")
        console.print(rep.read_text(encoding="utf-8"))


# ============================================================
# Privacy
# ============================================================

@privacy_app.command("scan")
def privacy_scan(
    source: Path = typer.Argument(..., help="archivo de texto a escanear"),
):
    """Escanear un texto en busca de datos personales."""
    from .privacy import scan_text, write_report
    if not source.exists():
        _err(f"No existe: {source}")
    text = source.read_text(encoding="utf-8", errors="ignore")
    scan = scan_text(text, source=str(source.name))
    _section(f"Privacidad scan: {source.name}")
    console.print(f"  riesgo:                 [bold]{scan.risk}[/]")
    console.print(f"  total_pii:              {scan.total_pii}")
    console.print(f"  requiere_sanitizacion:  {scan.requiere_sanitizacion}")
    console.print(f"  requiere_revision_humana: {scan.requiere_revision_humana}")
    console.print(f"  aprobado_para_ia_externa: {scan.aprobado_para_ia_externa}")
    if scan.matches:
        for name, matches in scan.matches.items():
            console.print(f"  · {name}: {len(matches)} ({', '.join(matches[:3])})")
    if scan.sensitive_keywords:
        console.print(f"  · keywords: {', '.join(scan.sensitive_keywords[:10])}")


@privacy_app.command("sanitize")
def privacy_sanitize(
    source: Path = typer.Argument(..., help="archivo de texto a sanitizar"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    """Sanitizar texto reemplazando PII por placeholders."""
    from .privacy import sanitize_text
    if not source.exists():
        _err(f"No existe: {source}")
    text = source.read_text(encoding="utf-8", errors="ignore")
    output = output or source.with_name(f"{source.stem}_sanitizado.txt")
    sanitize_text(text, output)
    _ok(f"Sanitizado: {output}")


@privacy_app.command("check")
def privacy_check(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Escanear pedido_original.txt de un job + sanitizar."""
    from .privacy import scan_text, sanitize_text, write_report
    if not job.exists():
        _err(f"No existe: {job}")
    src = job / "pedido_original.txt"
    if not src.exists():
        _err(f"No hay pedido_original.txt en {job}")
    text = src.read_text(encoding="utf-8", errors="ignore")
    scan = scan_text(text, source=str(src.name))
    sanitize_text(text, job / "pedido_sanitizado.txt")
    write_report(job / "privacy_report.md", scan, source_name=str(src.name))
    _section(f"Privacy check: {job.name}")
    console.print(f"  riesgo:    {scan.risk}")
    console.print(f"  sanitizado: {job / 'pedido_sanitizado.txt'}")
    console.print(f"  reporte:    {job / 'privacy_report.md'}")


# ============================================================
# Brief
# ============================================================

@brief_app.command("extract")
def brief_extract(
    job: Path = typer.Argument(..., help="ruta al job"),
):
    """Re-extraer brief desde el texto del job."""
    from .jobs.lifecycle import prepare_job
    if not job.exists():
        _err(f"No existe: {job}")
    res = prepare_job(job, run_privacy=False, run_brief_extract=True)
    _ok(f"Brief actualizado: {job / 'brief.yaml'}")


@brief_app.command("to-project")
def brief_to_project(
    brief: Path = typer.Argument(..., help="ruta al brief.yaml"),
    name: Optional[str] = typer.Option(None, "--name", "-n"),
    template: Optional[str] = typer.Option(None, "--template", "-t"),
):
    """Convertir brief.yaml en proyecto en projects/piezas_vectoriales/."""
    from .render.piezas import create_project_from_brief
    if not brief.exists():
        _err(f"No existe: {brief}")
    project = create_project_from_brief(brief, project_name=name, explicit_template=template)
    _ok(f"Proyecto: {project}")
    console.print(f"  Siguiente: [cyan]flujo render {project / 'config.json'}[/]")


@brief_app.command("show")
def brief_show(
    brief: Path = typer.Argument(..., help="ruta al brief.yaml"),
):
    """Mostrar brief en formato legible."""
    from .jobs.brief import load_brief
    if not brief.exists():
        _err(f"No existe: {brief}")
    b = load_brief(brief)
    _section(f"Brief: {brief.parent.name}")
    console.print(f"  id:           {b.id}")
    console.print(f"  estado:       [bold]{b.estado.value}[/]")
    console.print(f"  origen:       {b.origen}")
    console.print(f"  cliente:      {b.cliente or '-'}")
    console.print(f"  proyecto:     {b.proyecto or '-'}")
    console.print(f"  tipo_pieza:   {b.tipo_pieza or '-'}")
    console.print(f"  medidas:      {b.medidas.ancho_cm or '?'}x{b.medidas.alto_cm or '?'} cm ({b.medidas.orientacion or '?'})")
    console.print(f"  productos:    {', '.join(b.productos) or '-'}")
    console.print(f"  entrega:      editable={b.entrega.editable_svg} vectorizado={b.entrega.vectorizado_svg} pdf={b.entrega.pdf_impresion} zip={b.entrega.zip}")
    console.print(f"  texto_aprobado: {b.contenido.texto_aprobado}")
    console.print(f"  pendientes:   {len(b.pendientes)}")
    for p in b.pendientes:
        console.print(f"    · {p}")


# ============================================================
# Render
# ============================================================

@render_app.command("run")
def render_run(
    config: Path = typer.Argument(..., help="ruta al config.json"),
):
    """Renderizar un proyecto piezas_vectoriales."""
    from .render.piezas import render_config
    if not config.exists():
        _err(f"No existe: {config}")
    rc = render_config(config)
    if rc != 0:
        raise typer.Exit(rc)
    _ok(f"Render OK: {config.parent}")


@render_app.command("validate")
def render_validate(
    config: Path = typer.Argument(..., help="ruta al config.json"),
):
    """Validar un config.json sin renderizar."""
    from .render.piezas import validate_config
    if not config.exists():
        _err(f"No existe: {config}")
    errors = validate_config(config)
    if errors:
        _section(f"Errores en {config}")
        for e in errors:
            _warn(e)
        raise typer.Exit(1)
    _ok(f"Config OK: {config}")


@render_app.command("formats")
def render_formats(
    width: Optional[float] = typer.Option(None, "--width", "-w", help="ancho en cm"),
    height: Optional[float] = typer.Option(None, "--height", "-h", help="alto en cm"),
    tipo: Optional[str] = typer.Option(None, "--tipo", "-t", help="tipo (etiqueta, flyer, rider...)"),
):
    """Listar o sugerir formatos/plantillas."""
    from .render.formats import list_formats, suggest_format
    if width and height:
        sugs = suggest_format(width, height, tipo or "")
        _section(f"Sugerencias para {width:g}x{height:g}cm {tipo or ''}")
        for s in sugs:
            console.print(f"  · {s}")
    else:
        formats = list_formats()
        if not formats:
            _warn("No hay INDEX_FORMATOS.json")
            return
        _section(f"Formatos disponibles ({len(formats)})")
        for f in formats:
            console.print(f"  · {f}")


# Alias: `flujo render` sin subcomando → render_run
@render_app.callback(invoke_without_command=True)
def render_default(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    _warn("Uso: flujo render run <config.json> | validate | formats")


# ============================================================
# Dashboard
# ============================================================

@app.command()
def daily(
    output_md: Optional[Path] = typer.Option(None, "--md", help="ruta al markdown"),
    output_html: Optional[Path] = typer.Option(None, "--html", help="ruta al html"),
):
    """Generar reporte diario (md + html)."""
    from .paths import context_dir
    from .dashboard import collect_items, render_markdown, render_html

    items = collect_items()
    md = render_markdown(items)
    html = render_html(items)

    md_path = output_md or (context_dir() / "DAILY.md")
    html_path = output_html or (context_dir() / "dashboard.html")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    _section(f"Daily report: {len(items)} items")
    console.print(f"  md:   {md_path}")
    console.print(f"  html: {html_path}")
    # mostrar resumen
    alta = sum(1 for i in items if i.priority.value == "alta")
    media = sum(1 for i in items if i.priority.value == "media")
    baja = sum(1 for i in items if i.priority.value == "baja")
    console.print(f"  alta: {alta}  media: {media}  baja: {baja}")


# ============================================================
# App web (Gradio)
# ============================================================

@app.command()
def serve():
    """Iniciar interfaz web local (Gradio)."""
    import importlib.util
    if importlib.util.find_spec("gradio") is None:
        _err("Falta gradio. Instalar con: pip install gradio")
    # delegar al script legacy para mantener compatibilidad
    import subprocess
    from .paths import repo_root
    root = repo_root()
    script = root / "scripts" / "app.py"
    if not script.exists():
        _err(f"No existe: {script}")
    console.print("[cyan]Iniciando Gradio app...[/]")
    subprocess.run([sys.executable, str(script)], cwd=root)


# Alias: flujo app → flujo serve
@app.command()
def app_alias():
    """Alias de serve (interfaz web)."""
    serve()


# ============================================================
# Clean
# ============================================================

@app.command()
def clean(
    cache: bool = typer.Option(True, "--cache/--no-cache", help="limpiar __pycache__"),
    generated: bool = typer.Option(False, "--generated", help="limpiar outputs regenerables"),
):
    """Limpiar archivos temporales del repo."""
    from .paths import repo_root
    import shutil
    root = repo_root()
    removed = 0
    if cache:
        for p in root.rglob("__pycache__"):
            if ".git" in p.parts:
                continue
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
        for p in root.rglob("*.pyc"):
            if ".git" in p.parts:
                continue
            p.unlink(missing_ok=True)
            removed += 1
    if generated:
        for p in root.glob("projects/piezas_vectoriales/*/salida_generada"):
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    _ok(f"Limpieza: {removed} items removidos")


# ============================================================
# Init
# ============================================================

@app.command()
def init():
    """Inicializa carpetas del repo (jobs/_template, etc.)."""
    from .jobs.job import _ensure_template
    from .paths import repo_root
    root = repo_root()
    tpl = _ensure_template(root)
    _ok(f"Template: {tpl}")
    _ok(f"Carpetas listas en {root}")


# ============================================================
# Main
# ============================================================

def main():
    app()


if __name__ == "__main__":
    main()
