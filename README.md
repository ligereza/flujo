# flujo — Dimensiones del Orden

**arte + automatización · v0.18**

Sistema de automatización para flujos creativos. CLI unificada para manejar
jobs, flyers, privacidad, render de piezas vectoriales y dashboard.

## Estado actual (v0.18)

- CLI unificada `flujo` con 17+ comandos
- Pipeline completo de jobs: correo → brief → proyecto → render
- Intake inteligente de correos con parseo de links de Instagram
- Track M (integración directa PS/AI desde `analysis/palette.json`)
- Sistema de airdrop profesional
- Privacidad integrada (escaneo PII + sanitización)
- Dashboard diario con scoring de prioridades

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
- Solo instaloader para descarga de IG
- Mantener checkpoints
- Privacidad primero antes de IAs externas

## Estructura

```
src/flujo/        # paquete Python (CLI + módulos)
  cli.py          # CLI unificada Typer (17+ comandos)
  jobs/           # lifecycle de jobs
  privacy/        # escaneo PII
  render/         # piezas vectoriales
  dashboard/      # reporte diario
  intake/         # parseo de correos
  flyer/          # importación flyers IG
  analyze/        # colores + OCR
  export/         # ZIP + scripts JSX
  index/          # SQLite flyers
  ig/             # descarga Instagram
scripts/          # utilidades (checkpoint, airdrop, app.py)
tests/            # pytest (60+ tests)
docs/             # documentación
jobs/             # trabajos creativos (no commitear)
projects/         # proyectos generados
inbox/            # bandeja de entrada
data/             # índice SQLite
context/          # reportes diarios
```

## Comandos CLI

```bash
flujo health          # chequeo general
flujo version         # versión y changelog
flujo job {new,prepare,list,status,next,activate,report}
flujo privacy {scan,sanitize,check}
flujo brief {extract,to-project,show}
flujo render {run,validate,formats}
flujo analyze [--all] [--force-ocr]
flujo index [--rebuild|--duplicates]
flujo flyer-list
flujo flyer-import <correo.txt>
flujo ig-redownload [--all]
flujo export <proyecto>
flujo daily
flujo serve           # interfaz web Gradio
flujo clean [--generated]
flujo init
```

## Airdrop

```bash
# Aplicar actualización
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply
pip install -e .
py -m pytest tests/ -v
```

## Licencia

MIT
