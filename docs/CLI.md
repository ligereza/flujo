# flujo · CLI Reference (v0.56.1)

**Entrada diaria del usuario:** `flujo app` (o `flujo app --desktop`) — lanza servidor + hub pro workspace.
La CLI `flujo` (Typer, `src/flujo/cli.py`) es la entrada principal al sistema. La mayoria de los scripts sueltos historicos de `scripts/` fueron archivados por estar superados por comandos `flujo ...`.

Este documento es la unica referencia de comandos que hace falta leer. `docs/INTEGRACION_CLI.md` es un doc aparte (arquitectura interna de como se registra el namespace `flujo hub ...`), no un duplicado de este.

## Instalacion

```bash
python -m pip install -e ".[dev]"
```

En Windows también puedes usar `py` en lugar de `python`.

## Ayuda general

```bash
flujo --help
flujo <grupo> --help
flujo <comando> --help
python -m flujo --help
```

## Verificacion del repo

```bash
py -m compileall -q src scripts tests
py -m pytest tests/ -q --tb=short
py -m flujo health
py -m flujo verify
py -m flujo doctor
py -m flujo version
```

## Grupos y comandos (fuente: `src/flujo/cli.py`, verificado v0.56.1)

```txt
salud/info      health, version, doctor, verify, ai-prompt, github-sync, delegate
intake/flyers   intake json, flyer-import, ig-redownload, analyze, export
index/db        index, flyer-list
job             job new, prepare, list, status, next, activate, report
privacy         privacy scan, sanitize, check
brief           brief extract, to-project, paquete-cotizacion, show
render          render run, illustrator, bridge, validate, formats, rescale
suplementos     suplementos list, contraportada, validate, illustrator
eventos         eventos flyer-auto
resolume        resolume automatizar
datadrop        datadrop scan, list, ingest, prepare
knowledge       knowledge list, show, classify, ingest-example, logo-source, logo-lab
hub (addon)     hub serve, index, route  (registrado via cli_addons.py, ver INTEGRACION_CLI.md)
diario          daily, cotizaciones
web             app, serve, package (build .exe desktop)
varios          plano, clean, init
```

**Datadrop:** `flujo datadrop scan` (incoming bulk), `list` (solo procesados), `ingest <archivo>`, `prepare` (paquete review `_review_package.txt`). UI principal: hub (`flujo app` -> Herramientas -> Datadrop).

## Ejemplos operativos

```bash
# Salud / version / diagnostico
flujo health
flujo version
flujo doctor
flujo verify

# Intake JSON estructurado (valida + crea job/brief/acuse)
flujo intake json schemas/ejemplos/flyer_evento.json

# Crear job desde correo/texto
flujo job new "etiquetas acme" --email inbox/correo.txt
flujo job prepare jobs/2026-06-17_etiquetas-acme
flujo job status jobs/2026-06-17_etiquetas-acme
flujo job activate jobs/2026-06-17_etiquetas-acme
flujo job list
flujo job next
flujo job report jobs/2026-06-17_etiquetas-acme

# Brief
flujo brief extract jobs/2026-06-17_etiquetas-acme
flujo brief show jobs/2026-06-17_etiquetas-acme/brief.yaml
flujo brief to-project jobs/2026-06-17_etiquetas-acme/brief.yaml
flujo brief paquete-cotizacion jobs/<job>

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
flujo render illustrator projects/piezas_vectoriales/mi-proyecto/config.json
flujo render bridge projects/piezas_vectoriales/mi-proyecto/config.json

# Suplementos RD
flujo suplementos list
flujo suplementos contraportada <nombre> --brief "beneficios..."
flujo suplementos validate svg/suplementos_rd/04_contraportadas/generadas/*.svg
flujo suplementos illustrator <nombre>

# Flyers / Instagram
# Descarga IG: parth-dl via primaria (pip install parth-dl; video usa
# thumbnail, carrusel solo primera imagen; ver eventos/flyer_auto.py).
# imginn.com quedo 403 Cloudflare 2026-07-22 (solo fallback best-effort).
# instaloader no funciona (IG exige login). No yt-dlp.
flujo flyer-import inbox/correo.txt
flujo ig-redownload --all
flujo analyze --all
flujo export projects/flyer_eventos/mi-flyer
flujo index --rebuild
flujo flyer-list

# Eventos / Resolume
flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/"
flujo resolume automatizar jobs/<job_id>

# Knowledge base
flujo knowledge list productoras
flujo knowledge show <id>
flujo knowledge classify "texto del correo"

# Dashboard / cotizaciones / web + delegacion
flujo daily
flujo cotizaciones projects/plano/ejemplos/evento_ejemplo.json --para productora
flujo app                   # ENTRADA DIARIA: app + hub pro (recomendado)
flujo app --desktop         # ventana nativa (pywebview)
flujo package               # construye .exe standalone (PyInstaller gratis)
flujo delegate visual-polish "tarea aqui"   # o creative-director | pipeline | brand | future | packaging
flujo serve                 # alias de app

# Plano
flujo plano projects/plano/ejemplos/evento_ejemplo.json
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider
flujo plano projects/plano/ejemplos/evento_ejemplo.json --costs

# Hub addons (namespace separado, ver docs/INTEGRACION_CLI.md)
py -m flujo hub serve --open
py -m flujo hub index agent-brief "etiqueta creatina"
py -m flujo hub route where --area eventos --pieza flyer
```

## Airdrops -- retirado 2026-08-28

El subcomando `flujo airdrop` ya no existe. La cadena entera se retiro a
`/home/mak/_archive/orden-limpieza-20260828/por-razon/subsistema-retirado-20260814/`
tras verificar que estaba muerta desde el 2026-08-14: `_airdrop/`, el
directorio de staging sobre el que operaba, tiene **cero eventos en toda la
historia de git**, y el protocolo documental se borro ese mismo dia
en la purga de las 12:44.

Con la cadena se fueron `src/flujo/airdrop.py`, `src/flujo/intake/reception.py`
(el canal de correo, que segun su propio test no llamaba nadie), cinco scripts,
`.github/workflows/airdrop_gate.yml` y cinco archivos de test.

Para entregar cambios: rama, PR y CI, como cualquier otro trabajo.

## Estados de job

```txt
borrador
  |
brief_extraido_pendiente_revision
  |
pendiente_datos  -> listo_para_disenar
                    |
                  en_diseno
                    |
                  generado
                    |
                  entregado
```

Transiciones validas y sugerencias viven en `flujo.jobs.brief.EstadoJob` y `flujo.jobs.lifecycle.suggest_next_action`.

## Migracion desde scripts legacy (archivados)

Estos scripts fueron archivados en `_archive/legacy_20260703_1413/` (2026-07-03) por estar superados por la CLI Typer:

| Antiguo (archivado) | Nuevo |
|---------|-------|
| `py scripts/job_from_text.py` | `flujo job new` |
| `py scripts/job_prepare.py` | `flujo job prepare` |
| `py scripts/job_status.py` | `flujo job list` / `flujo job status` |
| `py scripts/job_activate.py` | `flujo job activate` |
| `py scripts/project_render.py` | `flujo render run` |
| `py scripts/privacy_check_job.py` | `flujo privacy check` |
| `py scripts/privacy_scan_text.py` | `flujo privacy scan` |
| `py scripts/privacy_sanitize_text.py` | `flujo privacy sanitize` |
| `py scripts/piezas_formatos.py` | `flujo render formats` |
| `py scripts/rider_new.py` | `flujo plano ... --rider` |

Nota: `scripts/piezas_generar.py`, `scripts/piezas_check_outputs.py` y `scripts/flyer_create_project.py` NO fueron archivados — siguen vivos en `.github/workflows/render_piezas_vectoriales.yml` y `make new-flyer` respectivamente. `scripts/flujo.py` (wrapper legacy pre-Typer) tampoco fue archivado pero no tiene uso real en CI/Makefile; preferir siempre `flujo ...`.
