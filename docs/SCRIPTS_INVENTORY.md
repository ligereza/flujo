# Inventario de scripts

Versión: v0.34.6

Este inventario evita que agentes confundan wrappers legacy con el núcleo real.

## Scripts críticos de proceso

| Script | Uso |
|---|---|
| `scripts/apply_airdrop.sh` | Copia `_airdrop/` al repo y crea backup. No hace tests. |
| `scripts/checkpoint.sh` | Commit + push con checkpoint. Solo usar después de pruebas OK. |
| `scripts/validate_airdrop.py` | Valida `_airdrop/` antes de aplicar. |
| `scripts/run_airdrop_checks.py` | Flujo seguro: valida, aplica, prueba, checkpoint. |
| `scripts/cleanup_demo_artifacts.sh` | Limpieza controlada de demos/tests históricos. |
| `scripts/cleanup_ig_temp_folders.sh` | Limpia carpetas temporales Instagram. |

## Wrappers/compatibilidad CLI

Muchos scripts en `scripts/` son wrappers o comandos históricos anteriores a la CLI Typer. Cuando exista equivalente `flujo ...`, preferir la CLI.

| Familia | Preferir |
|---|---|
| `job_*.py`, `job_new.sh` | `flujo job ...` |
| `privacy_*.py` | `flujo privacy ...` |
| `piezas_*.py`, `project_*.py` | `flujo render ...` / `flujo brief ...` |
| `flyer_*.py`, `flyer_*.sh` | `flujo flyer-import`, `flujo analyze`, `flujo index` |
| `ig_*.py` | `flujo ig-redownload` o módulo `flujo.ig` |

## Scripts activos por área

### Airdrop / mantenimiento

- `apply_airdrop.sh`
- `checkpoint.sh`
- `validate_airdrop.py`
- `run_airdrop_checks.py`
- `cleanup_demo_artifacts.sh`
- `cleanup_ig_temp_folders.sh`
- `cleanup_safe.sh`, `cleanup_moderate.sh`, `cleanup_legacy_aggressive.sh`

### Jobs / briefs

- `job_new.sh`
- `job_prepare.py`
- `job_activate.py`
- `job_status.py`
- `job_report.py`
- `job_next_actions.py`
- `brief_to_project.py`

### Render / proyectos

- `project_render.py`
- `project_delivery_manifest.py`
- `project_inspect.py`
- `project_new_from_template.py`
- `piezas_generar.py`
- `piezas_validate_config.py`
- `piezas_check_outputs.py`

### Flyers / Instagram

- `flyer_from_email.py`
- `flyer_analyze.py`
- `flyer_index.py`
- `ig_download.py`
- `ig_redownload.py`

## Regla para futuros airdrops

Si un airdrop modifica scripts legacy, debe explicar por qué no modifica primero la CLI `src/flujo/cli.py` o el módulo vivo correspondiente en `src/flujo/`.
