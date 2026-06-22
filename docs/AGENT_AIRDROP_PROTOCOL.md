# Protocolo para agentes que entregan airdrops

## Regla central

No tienes push directo. Entregas un ZIP con una carpeta `_airdrop/` que replica rutas finales del repo.

Ejemplo correcto:

```text
_airdrop/src/flujo/cli.py
_airdrop/docs/AGENT_GUIDE.md
_airdrop/HANDOFF_2026-06-21_x.md
```

Ejemplo incorrecto:

```text
_airdrop/v0.35/src/flujo/cli.py
src/_airdrop/...
[cli.py](http://cli.py)
```

## Obligatorio (Windows primero, español prioritario)

- ZIP con archivos reales dentro de `_airdrop/`.
- `HANDOFF_*.md` o `HOTFIX_*.md` + **actualizar siempre `context/LAST_HANDOFF.md`** (incluye 1-2 tareas simples claras para otros agentes + nota plataforma: "Windows: py | Linux: python3").
- Rutas planas (usa / ), sin links Markdown.
- Comandos finales desde la raíz, usa `py` (Windows/Git Bash). Prueba en clon limpio.
- Mostrar lista de archivos del ZIP.
- En handoff: usa español primero para reducir malentendidos. Incluye sección "Tareas simples (low token)" como órdenes claras.

## Prohibido salvo autorización explícita

- `delete.txt` o `_delete.txt`.
- Cambios al motor de airdrop (`src/flujo/airdrop.py`).
- `--no-checkpoint` o nuevos flujos de checkpoint.
- Dependencias nuevas no justificadas.
- Archivos generados: `__pycache__`, `.pytest_cache`, `.egg-info`, `data/*.db`, medios pesados, ZIPs, outputs.

## Comandos finales (Windows: usa 'py'. Linux: python3)

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje"
```

Incluye en LAST_HANDOFF: tareas simples claras + nota "probado en Windows".

Limpieza opcional:
```bash
rm -rf _airdrop _airdrop_backups
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf .pytest_cache
git status --short
git log --oneline -3
```

## Si algo falla

No digas que está OK. Entrega el archivo `_logs/airdrop_error_*.txt` o pega su contenido como texto plano.


Nota Windows/Git Bash: `scripts/run_airdrop_checks.py` usa el motor Python de airdrop y no invoca `bash` internamente para apply/checkpoint.
