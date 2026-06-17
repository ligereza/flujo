import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(add_completion=False, help="flujo — Dimensiones del Orden // arte y automatización")
console = Console()

@app.command()
def health():
    """Health check del repo"""
    from .paths import repo_root
    root = repo_root()
    console.print(f"[cyan]flujo[/] @ {root}")
    checks = [
        ("requirements.txt", (root / "requirements.txt").exists()),
        ("tools/flyer_eventos", (root / "tools" / "flyer_eventos").exists()),
        ("projects/flyer_eventos", (root / "projects" / "flyer_eventos").exists()),
    ]
    try:
        import instaloader, yaml, matplotlib, gradio
        checks.append(("instaloader", True))
    except Exception as e:
        checks.append((f"deps: {e}", False))

    for name, ok in checks:
        console.print(f"  {'✓' if ok else '✗'} {name}", style="green" if ok else "red")

@app.command("flyer-import")
def flyer_import(
    email: Path = typer.Argument(..., help="ruta a correo.txt con links IG"),
    force: bool = typer.Option(False, "--force", help="forzar duplicados"),
):
    """Crear proyectos flyer desde un correo con links de Instagram"""
    from .flyer.import_email import import_from_email
    res = import_from_email(email, force=force)
    console.print(f"[green]Creados:[/] {res['created']}  [yellow]Omitidos:[/] {res['skipped']}  [dim]Encontrados: {res['found']}[/]")

@app.command("flyer-list")
def flyer_list():
    """Listar proyectos flyer"""
    from .paths import flyer_base
    base = flyer_base()
    if not base.exists():
        console.print("sin proyectos")
        return
    table = Table("Fecha", "Proyecto", "Estado")
    for p in sorted(base.iterdir(), reverse=True):
        if not p.is_dir(): continue
        mf = p / "manifest.json"
        status = "-"
        if mf.exists():
            import json
            try:
                d = json.loads(mf.read_text(encoding="utf-8"))
                status = d.get("status", "")
            except: pass
        table.add_row(p.name[:10], p.name, status)
    console.print(table)

@app.command("ig-redownload")
def ig_redownload(
    all: bool = typer.Option(False, "--all", help="reintentar también los descargados"),
    project: Path = typer.Option(None, "--project", help="proyecto específico"),
):
    """Reintentar descarga IG en proyectos fallidos"""
    from .paths import flyer_base
    from .manifest import load_json, write_json
    from .ig.download import download_post
    import datetime
    base = flyer_base()
    projects = [Path(project)] if project else sorted([p for p in base.glob("*") if (p / "manifest.json").exists()]) if base.exists() else []
    ok = fail = skip = 0
    for proj in projects:
        data = load_json(proj / "manifest.json") or {}
        ig = data.get("instagram", {}) if isinstance(data.get("instagram"), dict) else {}
        url = ig.get("url", "")
        if not url: continue
        if not all and ig.get("download_status") == "downloaded":
            skip += 1; continue
        console.print(f"→ {proj.name}  {url}")
        res = download_post(url, proj / "input")
        manifest_path = proj / "manifest.json"
        full = load_json(manifest_path) or {}
        full.setdefault("instagram", {}).update({"download_result": res, "download_retry_at": datetime.datetime.now().isoformat(timespec="seconds")})
        if res.get("status") == "downloaded":
            full["instagram"].update({
                "download_status": "downloaded",
                "media_type": res.get("media_type",""),
                "file_count": res.get("file_count",0),
                "owner": res.get("owner",""),
                "date_utc": res.get("date",""),
            })
            ok += 1
            console.print(f"  [green]OK {res.get('media_type')}[/]")
        else:
            fail += 1
            console.print(f"  [red]FAIL {res.get('reason')}[/]")
        write_json(manifest_path, full)
    console.print(f"\nOK={ok} FAIL={fail} SKIP={skip}")

@app.command()
def daily():
    """Generar reporte diario"""
    import subprocess
    from .paths import repo_root
    root = repo_root()
    subprocess.run([sys.executable, str(root / "scripts" / "flujo_daily.py")], check=False)

@app.command()
def app_cmd():
    """Iniciar interfaz Gradio"""
    import subprocess
    from .paths import repo_root
    root = repo_root()
    subprocess.run([sys.executable, str(root / "scripts" / "app.py")])

# alias para que `flujo app` funcione
app.command(name="app")(app_cmd)

@app.command("new-flyer")
def new_flyer(name: str = typer.Argument(..., help="nombre del evento")):
    """Crear proyecto flyer manual"""
    from .flyer.project import create_flyer_project
    p = create_flyer_project(None, name, source_type="manual")
    console.print(f"[green]Creado:[/] {p}")

def main():
    app()

if __name__ == "__main__":
    app()
