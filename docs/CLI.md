# flujo · CLI Reference (v0.34.10)

**Entrada diaria principal:** `flujo app` (o `flujo app --desktop`) — lanza servidor + hub pro workspace.

La CLI `flujo` es la entrada principal al sistema. Reemplaza la mayoría de los
scripts sueltos de `scripts/` por comandos tipados y autodocumentados. `flujo app` activa el hub como workspace central + APIs reales.

## Instalación

```bash
py -m pip install -e ".[dev]"
```

En Linux/macOS puedes usar `python3` o `python`.

## Ayuda general

```bash
flujo --help
flujo <grupo> --help
flujo <comando> --help
py -m flujo --help
```

## Verificación del repo

```bash
py -m compileall -q src scripts tests
py -m pytest tests/ -q --tb=short
py -m flujo health
py -m flujo version
```

## Grupos y comandos principales

```txt
salud/info      health, version, init
intake/flyers   flyer-import, ig-redownload, analyze, export
index/db        index, flyer-list
job             job new, prepare, list, status, next, activate, report
privacy         privacy scan, sanitize, check
brief           brief extract, to-project, show
render          render run, validate, formats, rescale
diario          daily
web             serve, app, package (build .exe desktop)
airdrop         airdrop list, dry-run, apply, rollback, status, finish
plano           plano <evento.json> [--rider] [--costs]
varios          clean
```

## Ejemplos operativos

```bash
# Salud / versión
flujo health
flujo version

# Crear job desde correo/texto
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/2026-06-17_etiquetas-acme
flujo job status jobs/2026-06-17_etiquetas-acme
flujo job activate jobs/2026-06-17_etiquetas-acme

# Brief
flujo brief extract jobs/2026-06-17_etiquetas-acme
flujo brief show jobs/2026-06-17_etiquetas-acme/brief.yaml
flujo brief to-project jobs/2026-06-17_etiquetas-acme/brief.yaml

# Privacidad
flujo privacy scan inbox/correo.txt
flujo privacy sanitize inbox/correo.txt --output inbox/correo_sanitizado.txt
flujo privacy check jobs/2026-06-17_etiquetas-acme

# Render
flujo render formats
flujo render formats -w 16.5 -h 6.5 -t etiqueta
flujo render validate projects/piezas_vectoriales/mi-proyecto/config.json
flujo render run projects/piezas_vectoriales/mi-proyecto/config.json
flujo render rescale projects/piezas_vectoriales/mi-proyecto/config.json --dpi 300

# Flyers / Instagram
flujo flyer-import inbox/correo.txt
flujo ig-redownload --all
flujo analyze --all
flujo export projects/flyer_eventos/mi-flyer
flujo index --rebuild
flujo flyer-list

# Dashboard / web + delegación
flujo daily
flujo app                   # ENTRADA DIARIA: app + hub pro (recomendado)
flujo app --desktop         # ventana nativa (pywebview)
flujo package               # construye .exe standalone (PyInstaller gratis): doble clic abre flujo app --desktop sin consola
flujo delegate visual-polish "tarea aquí"   # o pipeline | brand | future
flujo serve                 # alias (usa --hub por defecto)

# Packaging desktop (free, PyInstaller + pywebview)
# Pre: py -m pip install -e .[web,desktop-extras,build]
# Luego: flujo package   → dist/flujo-hub.exe  (onefile noconsole)
# Doble clic: lanza directo "flujo • Workspace" nativo con icono, tray, assets bundled (context/svg/brand), jobs en flujo_workspace/ sibling.
# Actualiza rebuild tras cambios en HTMLs/paths.
# (Mantiene flujo app --desktop intacto en source; exe = standalone pro daily)

# Plano
flujo plano projects/plano/ejemplos/evento_ejemplo.json
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs
```

## Airdrops

```bash
flujo airdrop list
flujo airdrop dry-run
flujo airdrop apply "mensaje"
flujo airdrop rollback
flujo airdrop status
```

Desde v0.34.8, `flujo airdrop apply` valida `_airdrop/` antes de aplicar. Si el
airdrop modifica `src/flujo/airdrop.py`, hay que autorizarlo explícitamente:

```bash
flujo airdrop apply "mensaje" --allow-airdrop-engine
```

Runner recomendado para aplicar y probar en una pasada:

```bash
py scripts/run_airdrop_checks.py "mensaje"
py scripts/run_airdrop_checks.py "mensaje" --allow-airdrop-engine
```

## Estados de job

```txt
borrador
  ↓
brief_extraido_pendiente_revision
  ↓
pendiente_datos  → listo_para_disenar
                    ↓
                  en_diseno
                    ↓
                  generado
                    ↓
                  entregado
```

Transiciones válidas y sugerencias viven en `flujo.jobs.brief.EstadoJob` y
`flujo.jobs.lifecycle.suggest_next_action`.

## Migración desde scripts

| Antiguo | Nuevo |
|---------|-------|
| `py scripts/job_from_text.py` | `flujo job new` |
| `py scripts/job_prepare.py` | `flujo job prepare` |
| `py scripts/job_status.py` | `flujo job list` / `flujo job status` |
| `py scripts/job_activate.py` | `flujo job activate` |
| `py scripts/brief_to_project.py` | `flujo brief to-project` |
| `py scripts/project_render.py` | `flujo render run` |
| `py scripts/flujo_daily.py` | `flujo daily` |
| `py scripts/privacy_check_job.py` | `flujo privacy check` |
| `py scripts/privacy_scan_text.py` | `flujo privacy scan` |
| `py scripts/privacy_sanitize_text.py` | `flujo privacy sanitize` |
| `py scripts/piezas_formatos.py` | `flujo render formats` |
| `py scripts/flujo_health.py` | `flujo health` |
| `py scripts/app.py` | `flujo serve` / `flujo app` (legacy Gradio: `flujo serve --legacy`) |
