# AIRDROP v0.16 — flujo v0.16 — CLI Completo + Pipeline Unificado

Fecha: 2026-06-17

## Resumen

Convierte `flujo` en un sistema CLI unificado con módulos Python testeables.
Reemplaza gradualmente los scripts sueltos de `scripts/` por comandos tipados
en `src/flujo/cli.py`.

## Qué incluye

### Nuevos módulos en `src/flujo/`

```txt
src/flujo/
├── cli.py                 # CLI completa (25+ comandos)
├── version.py             # versión + changelog embebido
├── paths.py               # ampliado con helpers (jobs_dir, piezas_base, etc.)
├── jobs/
│   ├── brief.py           # Brief dataclass + YAML parser propio
│   ├── job.py             # create_job, list_jobs, find_job
│   └── lifecycle.py       # prepare_job, activate_job, suggest_next_action
├── privacy/
│   ├── scan.py            # ScanResult + regex de PII
│   ├── sanitize.py        # placeholders [EMAIL], [RUT], [TELEFONO]
│   └── report.py          # markdown report
├── render/
│   ├── formats.py         # INDEX_FORMATOS + suggest_format
│   └── piezas.py          # create_project_from_brief, validate, render
├── dashboard/
│   ├── scoring.py         # score_job/flyer/pieza
│   └── report.py          # markdown + html dashboard
├── intake/
│   ├── email_parser.py    # extendido con más tipos (rider, one_page, etc.)
│   └── pipeline.py        # process_email_to_jobs (correo → jobs/briefs)
└── templates/
    └── jobs_template/     # archivos base para nuevos jobs
        ├── brief.yaml
        ├── estado.md
        ├── resultado.md
        └── pedido_original.txt
```

### Tests añadidos (~30 tests)

```txt
tests/test_jobs_brief.py
tests/test_jobs_lifecycle.py
tests/test_privacy.py
tests/test_render_formats.py
tests/test_dashboard.py
tests/test_intake.py
tests/test_cli_smoke.py
tests/test_smoke.py         # actualizado con imports
```

### Documentación nueva / actualizada

```txt
docs/CLI.md                # referencia completa de la CLI
docs/JOB_PIPELINE.md       # ciclo de vida de un job
docs/RELEASE_v016.md       # release notes de v0.16
docs/AGENT_GUIDE.md        # actualizado
docs/COMANDOS.md           # actualizado
docs/ESTADOS_JOB.md        # ampliado
docs/OPERADOR_IA_RAPIDO.md # actualizado
README.md                  # reescrito con quick start
AGENTS.md                  # actualizado
PARA_IA.md                 # actualizado
CONTRIBUTING.md            # actualizado
```

### Nuevos comandos CLI (todos con `--help`)

```bash
flujo version
flujo health
flujo job {new,prepare,list,status,next,activate,report}
flujo privacy {scan,sanitize,check}
flujo brief {extract,to-project,show}
flujo render {run,validate,formats}
flujo analyze [--all]
flujo index [--rebuild|--duplicates]
flujo flyer-list
flujo ig-redownload
flujo daily
flujo serve
flujo clean
flujo init
flujo export
flujo flyer-import
```

### Archivos modificados

- `pyproject.toml` — versión 0.16.0
- `src/flujo/__init__.py` — versión 0.16.0 + exposición de helpers
- `src/flujo/__main__.py` — invoca `app`
- `src/flujo/paths.py` — ampliado
- `src/flujo/intake/email_parser.py` — extendido

## Aplicar este airdrop

```bash
# 1. Revisar cambios (dry-run)
bash scripts/apply_airdrop.sh --dry-run

# 2. Aplicar
bash scripts/apply_airdrop.sh --apply

# 3. Instalar
py -m pip install -e .

# 4. Probar
flujo version
flujo health
py -m pytest tests/ -q

# 5. Checkpoint
bash scripts/checkpoint.sh "flujo v0.16 - CLI Completo + Pipeline Unificado"
```

## Compatibilidad

- **No breaking changes**: la API vieja sigue funcionando.
- **Dependencias**: ninguna nueva obligatoria (typer y rich ya estaban).
- **Python**: 3.10+ (sin cambios).

## Próximo (v0.17 ideas)

- Notificaciones (Telegram/email) al cambiar estado de job.
- OCR mejorado (EasyOCR/PaddleOCR) sin tesseract externo.
- Tests e2e con proyectos de ejemplo.
- Render paralelo en CI.
- Integración opcional con Notion/Linear.
