# PARA IA

Este repo se llama **flujo** — arte y automatización.

**Punto de entrada obligatorio para agentes:** `context/flujo_hub.html`

Desde el hub podés:
- Pegar pedidos y generar brief + match de formatos + comandos
- Usar visualizadores reales de SVG (Eventos vs Suplementos) y Plano Demo
- Ver el estado actual y tareas

Lee en orden:
1. `context/flujo_hub.html`
2. `context/LAST_HANDOFF.md`
3. `docs/AGENT_OPERATING_MANUAL.md`

Comandos clave (Windows: `py -m flujo ...`):

```bash
flujo version
flujo health
flujo daily
flujo job new "..." --email inbox/correo.txt
flujo job prepare jobs/<job>
flujo render run projects/.../config.json --for illustrator|blender
flujo cotizaciones <json> --para productora|interno
flujo plano projects/plano/ejemplos/evento_ejemplo.json --rider --costs
```

Herramientas activas: instaloader (solo), análisis de colores + OCR, export a AI/PS/Blender.

Privacidad: `flujo privacy scan/sanitize` antes de IAs externas.

Reglas: Español primero, aistetic siempre, Windows con `py`.
`README.md`, `context/ESTADO.md`, `docs/RELEASE_v016.md`.

**No uses yt-dlp. No crees venvs pesados. Usa `py`.**

## Airdrops: validación obligatoria

Antes de aplicar cualquier entrega externa:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion"
```

Los errores quedan en `_logs/airdrop_error_*.txt` para compartirlos sin deformación de la web.

## Mapa antes de tocar

Antes de modificar archivos, lee `docs/REPO_MAP.md` y `docs/SCRIPTS_INVENTORY.md`. No uses `_archive/`, `reference_old/` ni checkpoints como fuente primaria salvo que el dueño lo pida explícitamente.
