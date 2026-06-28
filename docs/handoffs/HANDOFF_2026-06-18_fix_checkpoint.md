# 🤝 Handoff 2026-06-18 — flujo v0.29.0 — Auto-checkpoint en Python puro (fix Windows)

## El problema (reportado por el dueño)

Al correr `flujo airdrop apply "..."` en Windows:

```
Ejecutando auto-checkpoint y push...
<3>WSL (9 - Relay) ERROR: CreateProcessCommon:800: execvpe(/bin/bash) failed: No such file or directory
⚠ No se pudo realizar el auto-checkpoint. Por favor, hazlo manualmente.
```

**Causa raíz:** `run_auto_checkpoint()` llamaba a `subprocess.run(["bash", "scripts/checkpoint.sh", ...])`.
En Windows, Python resuelve `bash` al `bash.exe` de **WSL** (no al de Git Bash),
y WSL falla con `execvpe(/bin/bash) failed`. Resultado: el airdrop copiaba los
archivos pero **NO commiteaba ni pusheaba**.

> Por eso el remoto quedó en 0.27.0 aunque el editor (0.28.0) se aplicó local: el
> push del editor nunca ocurrió.

## La solución

`run_auto_checkpoint()` reescrita en **Python puro**: llama a `git` directamente
(`git add` / `commit` / `push`), sin pasar por `bash` ni por `checkpoint.sh`.
- Funciona igual en Windows / Linux / macOS.
- Genera el archivo `checkpoints/<fecha>_<slug>.md` en Python (equivalente al .sh).
- Reintenta el commit (hasta 3 veces) si un pre-commit hook modifica archivos.
- Pushea a la rama actual (`git rev-parse --abbrev-ref HEAD`).

`scripts/checkpoint.sh` se mantiene (sirve para uso manual desde Git Bash), pero
el airdrop ya **no depende** de él.

## Qué incluye

| Archivo | Cambio |
|---|---|
| `src/flujo/airdrop.py` | `run_auto_checkpoint` en Python puro (git directo) + helpers `_git`, `_write_checkpoint_file`. |
| `tests/test_airdrop_checkpoint.py` | **NUEVO.** 4 tests: no invoca bash, commitea+pushea (local==remoto), reintenta con hook, falla sin repo git. |
| `version.py`, `pyproject.toml` | Versión 0.29.0 + changelog. |

## ⚠️ Importante sobre el estado del repo del dueño

El dueño tiene el **editor (0.28.0) ya aplicado localmente pero SIN pushear**
(el push falló por este bug). Al aplicar este airdrop:

1. `flujo airdrop apply` copia los archivos de este fix.
2. El nuevo `run_auto_checkpoint` hace `git add -A` → **toma TODO lo pendiente**
   (el editor 0.28.0 + este fix 0.29.0) y lo commitea + pushea de una.

→ Con un solo `flujo airdrop apply` el remoto pasa de 0.27.0 a 0.29.0 con el
editor incluido. No se pierde nada.

## Verificación hecha

```
✅ compileall src/  → OK
✅ run_auto_checkpoint probado en repo git simulado → local == remoto (sin bash)
✅ con pre-commit hook que modifica y aborta → reintenta y pushea igual
✅ caso "sin cambios" y "sin repo git" → no rompe
✅ pytest tests/ → 103 passed, 1 skipped (eran 99; +4)
✅ test que verifica que el código NO invoca bash ni checkpoint.sh
```

## Cómo aplicar (dueño, en Windows / Git Bash)

```bash
cd /c/IA/flujo
unzip -o airdrop_2026-06-18_fix_checkpoint_v0.29.0.zip
flujo airdrop apply "v0.29.0 - fix auto-checkpoint sin bash (+ editor 0.28.0)"
py -m pip install -e .
flujo version            # 0.29.0
py -m pytest tests/ -q   # 103 passed, 1 skipped
```

Ahora el `apply` debería terminar con:
`✓ Checkpoint creado y cambios subidos al servidor.` (sin el error de WSL).

### Si por alguna razón el push aún fallara
Diagnóstico rápido (en Git Bash, dentro del repo):
```bash
git status
git remote -v
git push -u origin main
```
Pero con este fix ya no se usa bash, así que el error de WSL no debería volver.

## Próximos pasos (retomar el plan)

Seguíamos con el editor visual (0.28.0, ahora incluido). Pendientes que quedaron:
1. Elemento `image` en el **generador oficial** (hoy solo en el preview).
2. **Auto-fit de texto** ("misma medida, distinto texto").
3. Pestaña de **avisos de Instagram** en el editor.
4. Botón **"acusar recibo"** (mailto/Gmail).
