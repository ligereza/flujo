# flujo · CLI Reference (v0.16)

La CLI `flujo` es la puerta de entrada única al sistema. Reemplaza la mayoría de
los scripts sueltos de `scripts/` por comandos tipados y autodocumentados.

## Instalación

```bash
py -m pip install -e .
```

## Ayuda general

```bash
flujo --help                    # lista todos los grupos
flujo <grupo> --help            # ayuda de un grupo
flujo <comando> --help          # opciones de un comando
```

## Grupos de comandos

```txt
salud       health, version
intake      flyer-import, ig-redownload, analyze, export
index       index, flyer-list
job         new, prepare, list, status, next, activate, report
privacy     scan, sanitize, check
brief       extract, to-project, show
render      run, validate, formats
diario      daily
varios      serve, clean, init
```

## Comandos principales (ejemplos)

```bash
# Importar flyers desde correo con links de Instagram
flujo flyer-import inbox/correo.txt

# Analizar último flyer
flujo analyze

# Crear job desde texto/correo
flujo job new "etiquetas acme" --email inbox/correo.txt

# Pipeline de preparación: privacidad + brief + estado
flujo job prepare jobs/2026-06-17_etiquetas-acme

# Ver próximos pasos
flujo job next

# Activar job → crear proyecto
flujo job activate jobs/2026-06-17_etiquetas-acme

# Renderizar proyecto
flujo render run projects/piezas_vectoriales/etiquetas-acme/config.json

# Generar dashboard
flujo daily

# Levantar interfaz web
flujo serve
```

## Estado y ciclo de vida

### Estados de un job

```txt
borrador
  ↓ (pegar texto del pedido)
brief_extraido_pendiente_revision
  ↓ (revisar/completar brief)
pendiente_datos  → listo_para_disenar
                    ↓ (job activate)
                  en_diseno
                    ↓ (render)
                  generado
                    ↓ (entrega)
                  entregado
```

Transiciones válidas y sugerencias se gestionan automáticamente
en `flujo.jobs.brief.EstadoJob` y `flujo.jobs.lifecycle.suggest_next_action`.

## Flags útiles

| Comando | Flag | Significado |
|---------|------|-------------|
| `flyer-import` | `--force` | recrear duplicados |
| `analyze` | `--all` | analizar todos los proyectos |
| `analyze` | `--force-ocr` | forzar OCR aunque falle |
| `index` | `--rebuild` | reconstruir desde cero |
| `index` | `--duplicates` | mostrar duplicados por shortcode |
| `job list` | `--examples` | incluir jobs `_examples` |
| `job list` | `--status X` | filtrar por estado |
| `job prepare` | `--no-privacy` | saltar paso de privacidad |
| `job activate` | `--name X` | nombre custom del proyecto |
| `job activate` | `--template X` | forzar plantilla |
| `daily` | `--md` / `--html` | rutas custom |
| `clean` | `--no-cache` | no limpiar `__pycache__` |
| `clean` | `--generated` | limpiar `salida_generada/` |

## Configuración del repo

La CLI asume estructura estándar:

```txt
.
├── jobs/                 # jobs (borrador → entregado)
├── inbox/                # correos/textos sin procesar
├── projects/
│   ├── flyer_eventos/    # proyectos de flyers descargados
│   └── piezas_vectoriales/  # proyectos piezas_vectoriales
├── tools/                # herramientas (piezas_vectoriales, etc.)
└── data/                 # SQLite index (data/flujo.db)
```

Si necesitas cambiarlas, exporta variables de entorno:

```bash
export FLYER_BASE=/ruta/custom/flyers
```

## Tests

```bash
py -m pytest tests/ -q
```

## Migración desde scripts/

| Antiguo | Nuevo |
|---------|-------|
| `py scripts/job_from_text.py` | `flujo job new` |
| `py scripts/job_prepare.py` | `flujo job prepare` |
| `py scripts/job_status.py` | `flujo job list` |
| `py scripts/job_activate.py` | `flujo job activate` |
| `py scripts/brief_to_project.py` | `flujo brief to-project` |
| `py scripts/project_render.py` | `flujo render run` |
| `py scripts/flujo_daily.py` | `flujo daily` |
| `py scripts/privacy_check_job.py` | `flujo privacy check` |
| `py scripts/privacy_scan_text.py` | `flujo privacy scan` |
| `py scripts/privacy_sanitize_text.py` | `flujo privacy sanitize` |
| `py scripts/piezas_formatos.py` | `flujo render formats` |
| `py scripts/flujo_health.py` | `flujo health` |
| `py scripts/app.py` | `flujo serve` |

Los scripts siguen funcionando (wrappers) pero se descontinúan gradualmente.
