# PARA IA

Este repo se llama **flujo** — arte y automatización.

**Punto de entrada obligatorio (diario) para agentes:** `flujo app` (o `flujo app --desktop`) — lanza la app real (stdlib server + APIs reales brand/parse/jobs/delegate/SSE/datadrop) + sirve los 3 HTMLs como UI pro completa. O abre `context/flujo_hub.html` (fallback estático).

El hub (dentro de la app) es el workspace pro central con tabs: Intake/Jobs, Visuales, Planos, Agentes/Delegate (5 roles), Herramientas + Datadrop (inverse airdrop fully working).

**Estado actual (2026-06-22) / Avances recientes:**
- `flujo app` = SINGLE daily entry point. Hub tabs + Datadrop MVP: fotos a datadrops/incoming/ → scan (`flujo datadrop scan` o botón) → dated/ + rich manifests (palette/OCR/visual_traits/for_future_ai). Clean list, cards thumbs/swatches, modal robusto, _review_package.txt.
- Parallel delegation maximizada (reciente fix): 5 roles (Visual Polish, Pipeline & Integration, Brand Guardian, Future/Modern, Packaging). Hub copy-prompt + live delegate API.
- LAST_HANDOFF.md low-token source of truth + continuation. Brand strict via projects/flujo/flujo.json. Launchers desktop. Higiene + robust scan/list/modal.
- Packaging: `flujo package` para .exe standalone.

**Hacia dónde vamos:**
- Auto-compact chat sessions (parallel delegation + LAST_HANDOFF).
- linea_editorial v4.1 full integration usando datadrop ground-truth para §10/11 validation.
- Streamlined daily: `flujo app` → hub como único workspace (intake + datadrop + delegate + jobs).
- Packaging .exe, multi-path resilience, más hygiene/privacy/local analysis, agent specialization.

Lee en orden:
1. Ejecuta `flujo app` (o `flujo app --desktop`) — entrada diaria obligatoria.
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
flujo datadrop scan
```

Herramientas activas: instaloader (solo), análisis de colores + OCR (en analysis/), export a AI/PS/Blender. Datadrop para ground-truth de entregas.

Privacidad: `flujo privacy scan/sanitize` antes de IAs externas.

Reglas: Español primero, flujo siempre, Windows con `py`.
Para reanudación: usa `context/LAST_HANDOFF.md` + `docs/AGENT_OPERATING_MANUAL.md` (prioriza sobre legacy).

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
