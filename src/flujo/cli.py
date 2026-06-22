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
    job prepare                 Pipeline: privacidad → brief → estado
    job-list                    Listar jobs y estados
    job-status <path>           Estado de un job específico
    job-next                    Próximas acciones sugeridas por job
    job activate                brief → proyecto en projects/piezas_vectoriales/
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
  plano
    plano <evento.json>         Generar plano SVG/rider/costos de stands
  aistetic
    aistetic list               Lista ejemplos + estado de JSONs descriptivos
    aistetic analyze <ejemplo>  Genera stub JSON descriptivo desde carpeta de ejemplo
  cotizaciones
    cotizaciones <evento.json> --para productora|interno  Cotización dual (aistetic + formatos)
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

aistetic_app = typer.Typer(help="Línea editorial aistetic + análisis de ejemplos reales para extraer identidad.", no_args_is_help=True)
app.add_typer(aistetic_app, name="aistetic")


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


def _validate_airdrop_or_exit(allow_airdrop_engine: bool = False) -> None:
    """Ejecuta el validador conservador antes de aplicar un airdrop."""
    import subprocess
    from .paths import repo_root

    root = repo_root()
    script = root / "scripts" / "validate_airdrop.py"
    if not script.exists():
        _warn("No existe scripts/validate_airdrop.py; no se pudo validar automáticamente.")
        return
    cmd = [sys.executable, str(script)]
    if allow_airdrop_engine:
        cmd.append("--allow-airdrop-engine")
    res = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
    if res.stdout:
        console.print(res.stdout.rstrip())
    if res.stderr:
        console.print(res.stderr.rstrip())
    if res.returncode != 0:
        _err(
            "Validación de _airdrop/ falló. No se aplicó nada. "
            "Usa --allow-airdrop-engine solo si revisaste cambios al motor."
        )


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
    skip_validation: bool = typer.Option(
        False, "--skip-validation", help="omitir scripts/validate_airdrop.py"
    ),
    allow_airdrop_engine: bool = typer.Option(
        False,
        "--allow-airdrop-engine",
        help="permitir cambios al motor src/flujo/airdrop.py tras revisión explícita",
    ),
):
    """Aplica los archivos de _airdrop/, crea backup y dispara checkpoint + push."""
    from .airdrop import apply_airdrop, run_auto_checkpoint, scan_airdrop
    try:
        pending = scan_airdrop()
        if not pending:
            _warn("No hay archivos pendientes en _airdrop/")
            return

        if not skip_validation:
            _validate_airdrop_or_exit(allow_airdrop_engine=allow_airdrop_engine)

        changes = apply_airdrop()

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

        # Mejora para continuidad de tokens: recordar/actualizar LAST_HANDOFF
        if message:
            try:
                from pathlib import Path
                from datetime import datetime
                lh = Path("context/LAST_HANDOFF.md")
                if lh.exists():
                    content = lh.read_text(encoding="utf-8")
                    append = f"\n\n**Post-airdrop {datetime.now().strftime('%Y-%m-%d %H:%M')}**: {message}\n(Actualiza manualmente las secciones 'Estado' y 'Próximas acciones'.)"
                    lh.write_text(content.rstrip() + append, encoding="utf-8")
                    _ok("LAST_HANDOFF.md actualizado automáticamente con el mensaje del airdrop.")
            except Exception:
                _warn("No se pudo auto-actualizar LAST_HANDOFF.md (hazlo manualmente con 'flujo handoff create').")

        _section("Proceso Completado")
        console.print("[bold green]Airdrop está activo y sincronizado.[/]\n[cyan]Recuerda: 'flujo handoff' para que la próxima IA continúe con pocos tokens.[/]")

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


@app.command("handoff")
def handoff(action: str = typer.Argument("last", help="last | create"), 
            message: str = typer.Option("", "--message", "-m", help="Resumen corto para create")):
    """Gestiona el archivo de continuidad de baja token para otras IAs.
    
    Ejemplos:
      flujo handoff last
      flujo handoff create -m "Añadido soporte grid_2x a planos + LAST_HANDOFF"
    """
    from pathlib import Path
    from datetime import datetime

    p = Path("context/LAST_HANDOFF.md")

    if action == "last" or action == "show":
        if p.exists():
            console.print(p.read_text(encoding="utf-8"))
        else:
            _warn("context/LAST_HANDOFF.md no existe. Crea uno con 'flujo handoff create'.")
        return

    if action == "create":
        if not p.exists():
            _warn("LAST_HANDOFF.md no existe, créalo primero con la plantilla básica.")
            return
        if not message:
            _warn("Usa -m 'resumen corto de lo hecho y siguiente paso'")
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = p.read_text(encoding="utf-8")
        # Append a compact update section at the end (keeps file small)
        update = f"\n\n---\n\n**Actualización {now}**\n\n{message}\n\nActualiza la sección 'Próximas acciones' manualmente si es necesario."
        p.write_text(content.rstrip() + update, encoding="utf-8")
        _ok(f"LAST_HANDOFF.md actualizado con: {message}")
        console.print("Recuerda: agrega tareas simples claras + nota Windows (py) / Linux. Español primero.")
        return

    _warn("Acción desconocida. Usa 'last' o 'create -m ...'")


def _get_version() -> str:
    from .version import get_version
    return get_version()


# ============================================================
# Aistetic — Línea editorial + análisis de ejemplos
# ============================================================

@aistetic_app.command("list")
def aistetic_list():
    """Lista ejemplos en aistetic/ejemplos/ y estado de sus JSON descriptivos."""
    from pathlib import Path
    ejemplos = Path("projects/aistetic/ejemplos")
    jsons = Path("projects/aistetic/json")
    if not ejemplos.exists():
        _warn("No existe projects/aistetic/ejemplos/")
        return
    _section("Ejemplos aistetic")
    for d in sorted([p for p in ejemplos.iterdir() if p.is_dir()]):
        json_path = jsons / f"{d.name}.json"
        status = "✅ JSON" if json_path.exists() else "⏳ pendiente"
        console.print(f"  {d.name}  [{status}]")


@aistetic_app.command("analyze")
def aistetic_analyze(
    example: str = typer.Argument(..., help="nombre de la subcarpeta en ejemplos/"),
    force: bool = typer.Option(False, "--force", help="sobrescribir JSON existente"),
):
    """Analiza un ejemplo y genera/actualiza su JSON descriptivo en json/.

    Escanea archivos, extrae info básica y crea un stub listo para que el agente complete
    con análisis estético (colores, layout, motifs, etc.).
    """
    from pathlib import Path
    import json as jsonlib
    from datetime import datetime

    base = Path("projects/aistetic")
    ex_dir = base / "ejemplos" / example
    json_dir = base / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    out = json_dir / f"{example}.json"

    if out.exists() and not force:
        _err(f"Ya existe {out}. Usa --force para sobrescribir.")

    if not ex_dir.exists():
        _err(f"No existe el ejemplo: {ex_dir}")

    files = [str(p.relative_to(ex_dir)) for p in ex_dir.rglob("*") if p.is_file()][:20]
    stub = {
        "example_id": example,
        "source_paths": [f"projects/aistetic/ejemplos/{example}"],
        "aesthetic_summary": "PENDIENTE: completar por agente tras analizar los archivos",
        "files_found": files,
        "colors": [],
        "typography": {},
        "layout": {},
        "motifs": [],
        "composition_rules": "",
        "tone_visual": "",
        "tags": [],
        "generated_at": datetime.now().isoformat(),
        "notes_for_agent": "Analiza los archivos reales (imágenes, config.json, SVGs, etc.) y llena las secciones. Usa el schema schemas/example_description.schema.json"
    }
    out.write_text(jsonlib.dumps(stub, indent=2, ensure_ascii=False), encoding="utf-8")
    _ok(f"JSON descriptivo generado: {out}")
    console.print("  Siguiente: edita el JSON o pídele al agente que lo complete con análisis estético.")


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
        console.print(f"  Siguiente: [cyan]flujo render run {res.project_path / 'config.json'}[/]")


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
    area: Optional[str] = typer.Option(None, "--area", "-a", help="filtrar por área (eventos, suplementos)"),
    medio: Optional[str] = typer.Option(None, "--medio", "-m", help="filtrar por medio (impresion, digital)"),
    herramienta: Optional[str] = typer.Option(None, "--herramienta", help="filtrar por herramienta (illustrator, photoshop, blender)"),
):
    """Listar, filtrar o sugerir formatos/plantillas.

    Ejemplos:
      flujo render formats                      # todos
      flujo render formats -a suplementos       # solo área suplementos
      flujo render formats -m impresion         # solo impresión (Illustrator)
      flujo render formats -w 16.5 -h 6.5 -t etiqueta   # sugerir por medida
    """
    from .render.formats import list_formats, suggest_format
    if width and height:
        sugs = suggest_format(width, height, tipo or "")
        _section(f"Sugerencias para {width:g}x{height:g}cm {tipo or ''}")
        for s in sugs:
            console.print(f"  · {s}")
    else:
        formats = list_formats(area or "", medio or "", herramienta or "")
        if not formats:
            _warn("No hay formatos que coincidan (o falta INDEX_FORMATOS.json)")
            return
        filtros = " ".join(x for x in [
            f"área={area}" if area else "",
            f"medio={medio}" if medio else "",
            f"herramienta={herramienta}" if herramienta else "",
        ] if x)
        title = f"Formatos disponibles ({len(formats)})" + (f" — {filtros}" if filtros else "")
        _section(title)
        for f in formats:
            console.print(f"  · {f}")


@render_app.command("rescale")
def render_rescale(
    config: Path = typer.Argument(..., help="ruta al config.json"),
    dpi: Optional[float] = typer.Option(None, "--dpi", help="resolución objetivo (ej. 300)"),
    width: Optional[float] = typer.Option(None, "--width", "-w", help="nuevo ancho en cm (cambio de proporción)"),
    height: Optional[float] = typer.Option(None, "--height", "-h", help="nuevo alto en cm (cambio de proporción)"),
    scale_elements: Optional[bool] = typer.Option(
        None, "--scale-elements/--no-scale-elements",
        help="reposicionar elementos al nuevo tamaño (por defecto: sí en --dpi, no en proporción)",
    ),
    out: Optional[Path] = typer.Option(None, "--out", help="archivo de salida (por defecto sobrescribe)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="solo mostrar el cálculo, no escribir"),
):
    """Reescalar proporción (medida cm) o resolución (DPI) de un config.json.

    Ejemplos:
      flujo render rescale c.json --dpi 300            # subir resolución (anti-pixelado)
      flujo render rescale c.json -w 14 -h 10          # cambiar proporción a 14x10 cm
    """
    from .render.rescale import load_config, set_dpi, set_real_size, save_config, current_dpi

    if not config.exists():
        _err(f"No existe: {config}")
    if dpi is None and (width is None or height is None):
        _err("Indica --dpi, o bien --width y --height (cm).")

    try:
        cfg = load_config(config)
    except Exception as e:
        _err(f"No se pudo leer el config: {e}")

    try:
        if width is not None and height is not None:
            se = bool(scale_elements) if scale_elements is not None else False
            new_cfg, info = set_real_size(cfg, width, height, dpi=dpi, scale_elements=se)
        else:
            se = bool(scale_elements) if scale_elements is not None else True
            new_cfg, info = set_dpi(cfg, dpi, scale_elements=se)
    except ValueError as e:
        _err(str(e))

    _section(f"Rescale ({info['modo']}) — {config.name}")
    ca, cd = info["canvas_antes"], info["canvas_despues"]
    console.print(f"  canvas: [yellow]{ca[0]}x{ca[1]}px[/] → [green]{cd[0]}x{cd[1]}px[/]")
    if info["modo"] == "dpi":
        da = info["dpi_antes"]
        console.print(f"  dpi:    [yellow]{da:.0f}[/] → [green]{info['dpi_despues']:.0f}[/]" if da else f"  dpi:    → [green]{info['dpi_despues']:.0f}[/]")
    else:
        ra, rd = info["real_antes"], info["real_despues"]
        console.print(f"  medida: [yellow]{ra[0]}x{ra[1]}cm[/] → [green]{rd[0]}x{rd[1]}cm[/] @ {info['dpi_usado']:.0f}dpi")
    console.print(f"  elementos reescalados: {'sí' if info['elementos_reescalados'] else 'no'}")
    if info.get("aviso"):
        _warn(info["aviso"])

    if dry_run:
        _ok("Dry-run: no se escribió nada.")
        return

    target = out or config
    save_config(new_cfg, target)
    _ok(f"Guardado: {target}")


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
# Plano (stands de eventos)
# ============================================================

@app.command()
def plano(
    evento: Path = typer.Argument(..., help="ruta al JSON del evento"),
    rider: bool = typer.Option(False, "--rider", help="imprimir rider de texto"),
    costs: bool = typer.Option(False, "--costs", help="imprimir desglose de costos"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="archivo SVG de salida (solo sin --rider)"),
    px_por_metro: float = typer.Option(90.0, "--scale", help="escala px por metro"),
):
    """Generar plano SVG, rider o costos de stands desde un JSON de evento.

    Ejemplo:
      flujo plano projects/plano/ejemplos/evento_ejemplo.json
      flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
      flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs
      flujo plano <evento.json> -o plano.svg
    """
    from .plano import load_evento, render_svg, render_rider, resumen_costos
    if not evento.exists():
        _err(f"No existe: {evento}")
    try:
        ev = load_evento(evento)
    except Exception as e:
        _err(f"No se pudo leer el evento: {e}")

    if costs:
        console.print(resumen_costos(ev))
    elif rider:
        console.print(render_rider(ev))
    else:
        svg = render_svg(ev, px_por_metro=px_por_metro)
        if output:
            output.write_text(svg, encoding="utf-8")
            _ok(f"SVG guardado: {output}")
        else:
            console.print(svg)


@app.command("cotizaciones")
def cotizaciones(
    evento: Path = typer.Argument(..., help="evento.json (reusa el de plano)"),
    para: str = typer.Option("productora", "--para", help="productora | interno | empresa"),
):
    """Genera cotización dual integrada con aistetic.

    --para productora: versión externa branded (infografía para productoras, estilo ONG Reduciendo Daño)
    --para interno/empresa: desglose detallado interno.
    """
    from projects.cotizaciones.engine import generar_cotizacion
    if not evento.exists():
        _err(f"No existe: {evento}")
    texto = generar_cotizacion(evento, audiencia=para)
    console.print(texto)


# ============================================================
# App web (Gradio)
# ============================================================

@app.command()
def serve(
    port: int = typer.Option(7860, "--port", "-p", help="puerto del servidor"),
    host: str = typer.Option("127.0.0.1", "--host", help="host (0.0.0.0 para red local)"),
    legacy: bool = typer.Option(False, "--legacy", help="usar el script antiguo scripts/app.py"),
):
    """Iniciar el editor visual local (Gradio).

    Editor propio en src/flujo/web/ (catálogo → editar datos/proporción →
    preview SVG → exportar). Con --legacy usa el antiguo scripts/app.py.
    """
    import importlib.util
    if importlib.util.find_spec("gradio") is None:
        _err("Falta gradio. Instalar con: pip install gradio")

    if not legacy:
        try:
            from .web.editor import launch
            console.print(f"[cyan]Editor flujo en http://{host}:{port}[/]")
            launch(server_name=host, server_port=port)
            return
        except Exception as e:
            _warn(f"No se pudo iniciar el editor nuevo ({e}). Probando script legacy...")

    # fallback: script legacy
    import subprocess
    from .paths import repo_root
    root = repo_root()
    script = root / "scripts" / "app.py"
    if not script.exists():
        _err(f"No existe el editor legacy: {script}")
    console.print("[cyan]Iniciando Gradio app (legacy)...[/]")
    subprocess.run([sys.executable, str(script)], cwd=root)


# Alias: flujo app → flujo serve
@app.command("app")
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
