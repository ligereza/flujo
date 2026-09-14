"""Digest mecanico del repo (0 tokens, sin ningun modelo).

Recorre el repo e imprime un mapa compacto: arbol de carpetas + archivos clave con
su primera linea util (titulo/docstring). Sirve como CONTEXTO barato para pasarle a
Claude/agentes en vez de que exploren (ahi se van ~500k tokens). Es os.walk + lectura
de encabezados: no llama a Gemini ni a Claude.

Uso:
    py contexto_repo.py                 # imprime el mapa
    py contexto_repo.py > contexto.txt  # lo guardas para pasarlo como contexto
"""
from __future__ import annotations

import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
              ".pytest_cache", "dist", "build", "agentes", "estado", "buzon",
              "checkpoints", "state", "actions-runner", "WIN", "curatoria_inbox",
              "RD", "OneDrive", "GoogleDrive", "Documents", "Documentos",
              "Desktop", "Escritorio", "Downloads", "Descargas", "Pictures",
              "Imágenes", "Videos", "Vídeos", "Music", "Música", "Público",
              "portfolio_media", "n8n-local", "searxng"}


def _skip(d: str) -> bool:
    # salta ocultos (.), internos/backups (_) y la lista negra
    return d in _SKIP_DIRS or d.startswith(".") or d.startswith("_")
# carpetas que son SALIDA generada (no tocar / no explorar a mano)
_GENERADAS = {"jobs", "projects", "datadrops", "context/*.html"}
_KEY_NAMES = {"README.md", "SKILL.md", "pyproject.toml", "cli.py", "AGENTS.md"}
_MAXDEPTH = 3


def _primera_linea_util(p: Path) -> str:
    try:
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip().lstrip("#").lstrip('"').strip()
            if s and not s.startswith(("---", "import", "from", "#!/")):
                return s[:90]
    except Exception:  # noqa: BLE001
        return ""
    return ""


def _arbol():
    print("== ARBOL (carpetas, prof " + str(_MAXDEPTH) + ") ==")
    for root, dirs, _files in os.walk(_REPO):
        rel = Path(root).relative_to(_REPO)
        depth = len(rel.parts)
        dirs[:] = sorted(d for d in dirs if not _skip(d))
        if depth >= _MAXDEPTH:
            dirs[:] = []
        if str(rel) == ".":
            continue
        print("  " * (depth - 1) + "- " + rel.parts[-1] + "/")


def _clave():
    print("\n== ARCHIVOS CLAVE (con su titulo) ==")
    vistos = 0
    for root, dirs, files in os.walk(_REPO):
        dirs[:] = [d for d in dirs if not _skip(d)]
        for f in sorted(files):
            if f in _KEY_NAMES:
                p = Path(root) / f
                rel = p.relative_to(_REPO)
                print(f"  {rel}  ->  {_primera_linea_util(p)}")
                vistos += 1
    if not vistos:
        print("  (ninguno)")


def _map():
    print(f"# CONTEXTO DEL REPO: {_REPO}\n# (digest mecanico, 0 tokens)\n")
    _arbol()
    _clave()
    print("\n== ZONAS GENERADAS / NO TOCAR A MANO ==")
    for z in sorted(_GENERADAS):
        print(f"  {z}  (salida generada; leer solo si el pipeline lo requiere)")
    print("\n== COMO USAR ESTE MAPA ==")
    print("  Pasaselo a un agente como 'contexto' o leelo en vez de explorar.")
    print("  Para el detalle de un archivo puntual: leelo directo (barato).")


# tarea -> rutas recomendadas (fuentes de verdad a leer + rutas gordas a derivar)
_TASK_ROUTES = [
    (("web", "hub", "react", "vite", "visualizer", "studio", "svg studio"),
     ["web/src/components/", "web/src/App.tsx", "context/flujo_hub.html (generado)"]),
    (("cli", "comando", "command", "typer"),
     ["src/flujo/cli.py", "docs/CLI.md"]),
    (("flyer", "suplemento", "dark", "vectoriz", "logo", "pieza", "brief", "packs", "svg"),
     [".claude/skills/entregas-rd/", ".claude/skills/taller-svg-rd/SKILL.md",
      "assets/logo/", "svg/suplementos_rd/ (derivar: muchos SVG)"]),
    (("voz", "gemini", "agente", "handoff", "contexto"),
     ["/home/mak/AGENTS.md", "DECISIONES.md"]),
    (("resolume", "chataigne", "noisette"),
     ["src/flujo/resolume/automator.py",
      "BLOQUEADOR: sin .noisette real; no adivinar el schema (ver LAST_HANDOFF)"]),
    (("airdrop", "entrega", "release"),
     ["scripts/validate_airdrop.py"]),
    (("test", "pytest"),
     ["tests/", "/home/mak/AGENTS.md"]),
]


def _task(keywords: str):
    kw = keywords.lower()
    print(f"# CONTEXTO PARA LA TAREA: {keywords}\n")
    print("== LEER PRIMERO (fuente de verdad, barato) ==")
    for r in ("/home/mak/AGENTS.md", "DECISIONES.md"):
        print(f"  {r}")
    hits = [routes for keys, routes in _TASK_ROUTES if any(k in kw for k in keys)]
    print("\n== RUTAS RELEVANTES A LA TAREA ==")
    if hits:
        for routes in hits:
            for r in routes:
                print(f"  {r}")
    else:
        print("  (sin match; corre 'map' y elige a mano)")
    print("\n== COMO USARLO (bajo consumo) ==")
    print("  1. Lee tu las fuentes de verdad de arriba (poco volumen, critico).")
    print("  2. Rutas gordas -> derivar a un subagente Sonnet (Agent tool, model sonnet).")
    print("  3. Da a Aider SOLO los archivos de la tarea. Ver docs/AIDER_API_SETUP.md.")


def main():
    import sys
    args = sys.argv[1:]
    cmd = args[0] if args else "map"
    if cmd == "task":
        _task(" ".join(args[1:]) or "(sin keywords)")
    else:  # 'map' o sin args (retrocompatible)
        _map()


if __name__ == "__main__":
    main()
