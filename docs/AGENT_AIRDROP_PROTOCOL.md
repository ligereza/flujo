# Protocolo operativo de airdrop para agentes

Este documento es la regla base para integrar trabajo de agentes sin push directo.

## Principio

Un agente no pega archivos sueltos ni instrucciones ambiguas. Un agente entrega un ZIP con `_airdrop/` en la raiz. Esa carpeta replica rutas finales del repo.

## Estructura correcta

```txt
_airdrop/HANDOFF_2026-06-30_descripcion.md
_airdrop/context/LAST_HANDOFF.md
_airdrop/src/flujo/ejemplo.py
_airdrop/tests/test_ejemplo.py
_airdrop/docs/ejemplo.md
```

## Estructura incorrecta

```txt
airdrop/
_airdrop/_airdrop/
v0.48/_airdrop/
src/flujo/ejemplo.py fuera de _airdrop
archivos como enlaces Markdown en vez de archivos reales
```

## Contenido obligatorio

Cada airdrop debe traer:

1. `HANDOFF_*.md` o `HOTFIX_*.md`.
2. `context/LAST_HANDOFF.md` actualizado en ASCII-only.
3. Archivos reales en rutas finales del repo.
4. Verificacion reportada.
5. Lista de archivos del ZIP.

## Prohibido

```txt
__pycache__/
.pytest_cache/
node_modules/
dist/
build/
_airdrop_backups/
_logs/
*.zip dentro del airdrop
*.db
credenciales
tokens
cookies
archivos pesados reales
_delete.txt
delete.txt
```

Prohibido tocar `src/flujo/airdrop.py` salvo autorizacion explicita del usuario.

## Validacion y apply

Desde raiz del repo en Windows/Git Bash:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje corto"
```

Si ya aplico cambios pero fallo despues:

```bash
py scripts/run_airdrop_checks.py --resume "mensaje corto"
```

Si el usuario autorizo tocar motor de airdrop:

```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "mensaje corto" --allow-airdrop-engine
```

## Que hace el runner

El runner debe:

1. Validar `_airdrop/`.
2. Simular cambios.
3. Aplicar con backup/manifest.
4. Instalar el paquete en modo dev.
5. Ejecutar compileall, pytest, health, version y smoke cuando exista.
6. Crear checkpoint/commit/push si todo pasa.

## Regla de fallo

Si algo falla, no declarar exito. Reportar:

```txt
comando ejecutado
codigo de salida
error exacto
archivo de log si existe
```

## Limpieza despues de aplicar

```bash
rm -rf _airdrop
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf .pytest_cache
git status --short
git log --oneline -5
```
