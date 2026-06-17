# AIRDROP v3 — flujo pro

Fecha: 2026-06-16
Versión: 0.12.0

Reconstrucción con libertad total. Arte + automatización.

## Qué cambia (paredes derrumbadas)

### Estructura Python pro
- `pyproject.toml` – instala con `py -m pip install -e .`
- `src/flujo/` – paquete real, no scripts sueltos
- Comando CLI: `flujo` (instalado vía `[project.scripts]`)
- También: `py -m flujo`

### Modelos validados
- `src/flujo/models.py` – Manifest pydantic
- `src/flujo/manifest.py` – load/save con merge seguro, preserva campos desconocidos
- Adiós dicts sueltos

### CLI unificado (Typer + Rich)
```
flujo health
flujo flyer-import inbox/correo.txt
flujo flyer-list
flujo ig-redownload
flujo daily
flujo app
flujo new-flyer "nombre"
```
- Colores, tablas, ayuda automática

### Instagram
- `src/flujo/ig/download.py` – instaloader only, con retry/backoff
- Detecta rate_limit
- Guarda carrusel + caption + owner + date

### Flyer import
- `src/flujo/flyer/import_email.py`
- Proyectos nombrados `ig_<shortcode>`
- Manifest con producer_suggested

### Docs
- `README.md` – limpio, artístico, con link a tapiz
- `docs/TAPIZ.md` – ASCII carpet completo
- `docs/AGENT_GUIDE.md` – PARA_IA + AGENTS unificados
- `PARA_IA.md` / `AGENS.md` – stubs que apuntan a la guía

### Repo hygiene
- `.gitignore` corregido: ya NO ignora `*.jpg` globalmente
  Solo ignora media en `projects/**/input/*`
  Imágenes en `docs/` y raíz están permitidas
- `requirements.txt` actualizado: + pydantic, typer, rich
- `start.sh` portable: detecta py/python3, ejecuta `py -m flujo app`

### Compatibilidad
Scripts legacy en `scripts/` son shims que importan desde `flujo.*`:
- `scripts/flyer_from_email.py` → `flujo.flyer.import_email`
- `scripts/ig_download.py` → `flujo.ig.download`
- `scripts/flujo.py` → `flujo.cli`
- `scripts/flyer_status.py` → versión mejorada incluida
- `scripts/ig_redownload.py` → shim a CLI

Los bash wrappers `flyer_list.sh`, `flyer_status_latest.sh`, etc. siguen funcionando.

## Instalar

```bash
# desde la raíz del repo
py -m pip uninstall -y yt-dlp  # por si quedó
py -m pip install -e .

# probar
flujo health
flujo flyer-import inbox/correo_prueba.txt
```

## Archivos incluidos

```
pyproject.toml
src/flujo/
  __init__.py
  __main__.py
  paths.py
  models.py
  manifest.py
  cli.py
  ig/download.py
  flyer/project.py
  flyer/import_email.py
README.md
docs/TAPIZ.md
docs/AGENT_GUIDE.md
PARA_IA.md
AGENTS.md
requirements.txt
.gitignore
start.sh
scripts/flyer_from_email.py
scripts/ig_download.py
scripts/flujo.py
scripts/flyer_status.py
scripts/ig_redownload.py
```

## Migración

1. Aplicar airdrop
2. `py -m pip install -e .`
3. `flujo health`
4. `pytest -q`  (tests smoke existentes siguen pasando)
5. checkpoint

Los manifests antiguos se leen sin problema – pydantic con `extra="allow"`.

## Próximo

- Fase B: OCR + palette auto
- Fase C: SQLite index
- Fase D: Gradio con auth

— flujo v0.12 // arte y automatización
