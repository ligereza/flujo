# Revisión local de airdrops

Este repo usa airdrops porque los agentes externos no hacen push directo. El dueño reemplaza manualmente `_airdrop/` en la raíz y luego ejecuta los comandos de validación.

## Comandos estándar

Desde la raíz del repo:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion"
```

Si todo termina OK, limpieza opcional:

```bash
rm -rf _airdrop
# Los _airdrop_backups ahora están en .archive/ si se movieron
# rm -rf .archive/_airdrop_backups
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf .pytest_cache
git status --short
git log --oneline -5
```

## Qué valida `scripts/validate_airdrop.py`

- `_airdrop/` existe.
- Contiene archivos reales, no solo carpetas vacías.
- No hay archivos de 0 bytes.
- Incluye un `HANDOFF_*.md` o `HOTFIX_*.md`.
- No incluye caches, `.egg-info`, bases de datos, medios pesados, ZIPs ni outputs generados.
- No incluye `_delete.txt`.
- No toca `src/flujo/airdrop.py` salvo autorización explícita con `--allow-airdrop-engine`.
- Detecta rutas deformadas por Markdown/autolink como `[archivo.py](http...)`.

## Qué hace `scripts/run_airdrop_checks.py`

Ejecuta en orden:

1. `py scripts/validate_airdrop.py`
2. `bash scripts/apply_airdrop.sh --dry-run`
3. `bash scripts/apply_airdrop.sh --apply`
4. `py -m pip install -e ".[dev]"`
5. `py -m compileall -q src scripts tests`
6. `py -m pytest tests/ -q`
7. `py -m flujo health`
8. `py -m flujo version`
9. chequeo `get_version() in get_changelog()`
10. `bash scripts/checkpoint.sh "mensaje"`

Si un paso falla, se detiene y escribe un log en `_logs/airdrop_error_*.txt`.

## Regla importante

No se hace checkpoint si `compileall`, `pytest`, `health`, `version` o el chequeo de changelog fallan.


Nota Windows/Git Bash: `scripts/run_airdrop_checks.py` usa el motor Python de airdrop y no invoca `bash` internamente para apply/checkpoint.
