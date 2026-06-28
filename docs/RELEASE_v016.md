# flujo v0.16 — CLI Completo + Pipeline Unificado

Fecha: 2026-06-17

## Resumen

`flujo` pasa de 3 comandos a 25+, organizados en grupos (job, privacy, brief,
render, intake). Toda la lógica dispersa en `scripts/*.py` se consolida en
módulos Python dentro de `src/flujo/` con tests, modelos Pydantic-like y CLI
tipada con Typer.

## Qué cambia

### Nuevos módulos

- `flujo.jobs` — lifecycle de jobs (borrador → ... → entregado)
  - `Brief` dataclass + YAML I/O (parser propio sin dependencia)
  - `EstadoJob` enum con transiciones válidas
  - `create_job`, `list_jobs`, `find_job`
  - `prepare_job`, `activate_job`, `suggest_next_action`
- `flujo.privacy` — escaneo + sanitización de PII
  - `scan_text` con regex (email, RUT, teléfono, URL, tarjeta)
  - `sanitize_text` con placeholders (`[EMAIL]`, `[RUT]`, ...)
  - `write_report` (markdown)
- `flujo.render` — piezas vectoriales
  - `formats.load_index` + `suggest_format` (por tamaño o tipo)
  - `piezas.create_project_from_brief` (reemplaza `brief_to_project.py`)
  - `piezas.validate_config` + `render_config`
- `flujo.dashboard` — reporte diario
  - `scoring.score_job/lyer/pieza`
  - `report.render_markdown/html`
- `flujo.intake.pipeline` — pipeline correo → jobs/briefs (extiende intake previo)
- `flujo.version` — versión + changelog embebido
- `flujo.templates.jobs_template/` — archivos base para nuevos jobs

### Nuevos comandos CLI

```bash
flujo version                  # ver versión + changelog
flujo job new NOMBRE [--email FILE]    # crear job
flujo job prepare JOB          # privacidad → brief → estado
flujo job list [--status X]    # listar jobs
flujo job status JOB           # estado detallado
flujo job next                 # sugerencias por job
flujo job activate JOB         # brief → proyecto
flujo job report JOB           # generar reporte_job.md
flujo privacy scan FILE        # escanear texto
flujo privacy sanitize FILE    # sanitizar (--output opcional)
flujo privacy check JOB        # escanear pedido_original.txt del job
flujo brief extract JOB        # re-extraer brief
flujo brief to-project BRIEF   # crear proyecto desde brief
flujo brief show BRIEF         # mostrar brief legible
flujo render run CONFIG        # renderizar proyecto
flujo render validate CONFIG   # validar config.json
flujo render formats           # listar o sugerir formatos
flujo analyze [--all]          # analizar flyer
flujo index [--rebuild|--duplicates]
flujo flyer-list [--status]
flujo ig-redownload [--all]
flujo daily [--md PATH] [--html PATH]
flujo serve                    # interfaz web Gradio
flujo clean [--no-cache] [--generated]
flujo init                     # crear jobs/_template
```

### Archivos a eliminar (eventualmente)

Estos scripts quedan como wrappers deprecados que llaman a `flujo`:

- `scripts/job_from_text.py` → `flujo job new`
- `scripts/job_prepare.py` → `flujo job prepare`
- `scripts/job_status.py` → `flujo job list`
- `scripts/job_activate.py` → `flujo job activate`
- `scripts/brief_to_project.py` → `flujo brief to-project`
- `scripts/project_render.py` → `flujo render run`
- `scripts/flujo_daily.py` → `flujo daily`
- `scripts/privacy_check_job.py` → `flujo privacy check`
- `scripts/privacy_scan_text.py` → `flujo privacy scan`
- `scripts/privacy_sanitize_text.py` → `flujo privacy sanitize`
- `scripts/piezas_formatos.py` → `flujo render formats`
- `scripts/flujo_health.py` → `flujo health`
- `scripts/app.py` → `flujo serve`

Los scripts siguen funcionando, pero la documentación apunta a la CLI.

### Tests añadidos

- `tests/test_jobs_brief.py` — Brief model, YAML I/O, brief_from_text
- `tests/test_jobs_lifecycle.py` — create_job, prepare_job, activate_job
- `tests/test_privacy.py` — scan, sanitize, write_report
- `tests/test_render_formats.py` — formats index, suggest, validate
- `tests/test_dashboard.py` — scoring, render_markdown/html
- `tests/test_intake.py` — email_parser
- `tests/test_cli_smoke.py` — CLI integration tests

Total: ~30 tests.

## Compatibilidad

- **Python**: 3.10+
- **Dependencias nuevas**: ninguna (pydantic ya estaba en pyproject).
  El parser YAML simple evita dependencia obligatoria de `pyyaml`,
  pero se usa si está disponible.
- **No breaking changes**: la API vieja (`scripts/*.py`, `flujo health`,
  `flujo flyer-import`, `flujo export`) sigue funcionando.

## Aplicar este airdrop

```bash
bash scripts/apply_airdrop.sh --dry-run   # revisar
bash scripts/apply_airdrop.sh --apply     # aplicar
bash scripts/finish_airdrop.sh            # guía final

py -m pip install -e .
flujo version
flujo health
py -m pytest tests/ -q
```

## Próximo (v0.17 ideas)

- Notificaciones por Telegram / email cuando cambia estado de un job
- Mejor OCR (EasyOCR / PaddleOCR) sin tesseract externo
- Tests e2e con proyectos de ejemplo
- Integración con Notion / Linear como panel externo opcional
- Render paralelo de proyectos piezas_vectoriales en CI
