# flujo — Dimensiones del Orden

**arte + automatización · v0.16**

Sistema de automatización para flujos creativos. CLI unificada para manejar
jobs, flyers, privacidad, render de piezas vectoriales y dashboard.

## Estado actual (v0.16)

- CLI unificada `flujo` con 25+ comandos
- Pipeline completo de jobs: correo → brief → proyecto → render
- Módulos Python con tests: `flujo.jobs`, `flujo.privacy`, `flujo.render`, `flujo.dashboard`
- Track M (integración directa PS/AI desde `analysis/palette.json`)
- Sistema de airdrop profesional
- Privacidad integrada (Ley 21.719 y buenas prácticas)

## Quick start

```bash
py -m pip install -e .

# Crear job desde correo
flujo job new "etiquetas acme" --email inbox/correo.txt

# Pipeline completo
flujo job prepare jobs/2026-06-17_etiquetas-acme
flujo job activate jobs/2026-06-17_etiquetas-acme
flujo render run projects/piezas_vectoriales/etiquetas-acme/config.json

# Dashboard diario
flujo daily

# Interfaz web local
flujo serve
```

## Flujos principales

```bash
# Flyers desde Instagram (vía correo)
flujo flyer-import inbox/correo.txt
flujo analyze
flujo export <proyecto>

# Privacidad
flujo privacy scan inbox/correo.txt
flujo privacy sanitize inbox/correo.txt --out inbox/correo_sanitizado.txt

# Piezas vectoriales
flujo render formats                          # listar plantillas
flujo render formats -w 16.5 -h 6.5 -t etiqueta  # sugerir
flujo render validate projects/.../config.json
flujo render run projects/.../config.json
```

## Reglas

- No automatizar Photoshop / Illustrator / Blender
- Solo instaloader (no yt-dlp)
- Mantener checkpoints
- Privacidad primero antes de IAs externas

## Estructura

```txt
src/flujo/                    # paquete Python (CLI, lógica)
  cli.py                      # CLI unificada Typer
  jobs/                       # lifecycle de jobs
  privacy/                    # PII scanner + sanitizer
  render/                     # piezas vectoriales
  dashboard/                  # reporte diario
  intake/                     # parseo de correos
  flyer/                      # importación de flyers
  analyze/                    # colores + OCR
  export/                     # ZIP listo PS/AI
  index/                      # SQLite de flyers
  ig/                         # descarga Instagram
  version.py                  # versión + changelog

scripts/                      # wrappers shell/Python deprecados
tests/                        # pytest suite
docs/                         # documentación
tools/                        # herramientas (piezas_vectoriales, etc.)
```

## Documentación

- [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) — guía para agentes IA
- [`docs/CLI.md`](docs/CLI.md) — referencia completa de la CLI
- [`docs/JOB_PIPELINE.md`](docs/JOB_PIPELINE.md) — ciclo de vida de un job
- [`docs/RELEASE_v016.md`](docs/RELEASE_v016.md) — release notes de v0.16
- [`docs/ESTADOS_JOB.md`](docs/ESTADOS_JOB.md) — estados y transiciones
- [`docs/ANALISIS.md`](docs/ANALISIS.md) — análisis de colores y OCR
- [`docs/COMANDOS.md`](docs/COMANDOS.md) — referencia portable de comandos

---

**Versión:** v0.16
