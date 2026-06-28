# HOTFIX 2026-06-28 - airdrop checkpoint timeout

## Motivo

El runner podia quedarse pegado en el paso final:

```txt
flujo.airdrop.run_auto_checkpoint()
```

Causa mas probable: `git push` ejecutado con `capture_output=True`, sin timeout y sin salida en vivo. En Windows esto oculta prompts de Git Credential Manager, errores de autenticacion o esperas de red.

## Cambios

- `src/flujo/airdrop.py`
  - `_git()` ahora acepta `timeout` y `live`.
  - `git push` corre con salida en vivo.
  - `git push` tiene timeout de 180 segundos.
  - `git add`, `git commit` y comandos auxiliares tienen timeout.
  - `run_auto_checkpoint(message, push=True)` permite saltar el push.
  - Si hay timeout, informa que hacer en vez de quedar pegado.

- `scripts/run_airdrop_checks.py`
  - Nuevo flag `--skip-push`.
  - Permite hacer apply + checks + commit local sin push automatico.

- Tests actualizados:
  - `tests/test_airdrop_checkpoint.py`
  - `tests/test_run_airdrop_checks.py`

## Uso recomendado si el push se pega

Desde root del repo:

```bash
py scripts/run_airdrop_checks.py --resume "logo clean lab experimental" --skip-push
```

Eso deja el commit local hecho y no intenta push. Luego hacer manual:

```bash
git push
```

Si GitHub pide login, completar login en la ventana o prompt.

## Uso normal

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "logo clean lab experimental"
```

Si ya aplicaste el airdrop anterior y fallo despues del apply:

```bash
py scripts/run_airdrop_checks.py --resume "logo clean lab experimental" --skip-push
```

## Nota

Este ZIP incluye tambien el proyecto experimental `projects/logo_clean_lab/` del airdrop anterior, para que puedas aplicar todo junto si el apply anterior no alcanzo a terminar.
