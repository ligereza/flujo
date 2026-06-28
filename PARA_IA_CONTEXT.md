# 🤖 Contexto para IA (Handover Document)

**Estado del Proyecto:** flujo v0.34.10
**Fecha de última actualización:** 2026-06-22

## 👉 Empieza por aquí (AHORRO DE TOKENS)

**Si tienes pocos tokens o es una sesión nueva / quieres continuar trabajo:**
1. Ejecuta **`flujo app`** (o `flujo app --desktop`) — **única entrada diaria obligatoria** (lanza servidor real + APIs + sirve hub pro + visualizadores como UI completa).
2. **`context/LAST_HANDOFF.md`** ← **LA PIEZA MÁS IMPORTANTE PARA CONTINUIDAD**
3. `docs/AGENT_OPERATING_MANUAL.md` (flujos + modelo delegación a sub-agentes)
4. `py -m flujo daily` + usa el hub (tabs + datadrop + delegate)

**Solo si necesitas profundidad después de lo anterior:**
- `context/flujo_hub.html` (el workspace principal: intake, visualizadores SVG/plano + UI delegación)
- `context/svg_visualizer.html` y `context/plano_demo.html`
- `README.md` + `docs/REPO_MAP.md`
- `docs/AGENT_OPERATING_MANUAL.md` (roles especializados + prompts listos)

**Nunca leas todos los handoffs/checkpoints antiguos al principio.** El `LAST_HANDOFF.md` + `flujo daily` deben bastar para continuar.

Después clona el repo actual desde GitHub en una carpeta limpia y verifica el
estado real con:

```bash
py -m pip install -e ".[dev]"
py -m compileall -q src scripts tests
py -m pytest tests/ -q --tb=short
py -m flujo health
py -m flujo version
```

En Linux/macOS puedes usar `python3` o `python` en vez de `py`.

**Estado actual (2026-06-22) — Avances clave (usa consistentemente):**

`flujo app` (or --desktop) es la SINGLE daily entry point: lanza real stdlib server + APIs (brand, parse, jobs, delegate, SSE, datadrop) + sirve los 3 HTMLs como full pro UI.

Hub (flujo_hub.html) ahora con tabs (Intake/Jobs, Visuales, Planos, Agentes/Delegate con 5 parallel roles, Herramientas) + fully working Datadrop section (inverse airdrop).

Datadrop MVP complete: drop photos of delivered work to datadrops/incoming/ (easy bulk), Escanear incoming (button or `flujo datadrop scan`) processes ALL reliably to dated/ dirs + rich manifests (palette from analysis/, OCR, visual_traits, for_future_ai teaching notes). Clean list (never shows raw 'incoming'), card UI with thumbs/swatches, modal viewer (structured + close robust: X/Esc/backdrop), prepare _review_package.txt.

Parallel delegation maximized (recently 2+1 supervisor for datadrop buttons fix; 5 roles: Visual Polish, Pipeline, Brand Guardian, Future, Packaging). Hub has copy-prompt + live delegate API.

LAST_HANDOFF.md as low-token source of truth + auto for continuation. Launchers (ps1/bat) from root for desktop.

Brand enforced strictly via projects/flujo/flujo.json.

Recent: datadrop button (header link) fixed to reliably open tab+scroll, robust scan/list/modal, hygiene.

**Hacia dónde vamos:**
- Auto-compact of chat sessions (using parallel delegation + LAST_HANDOFF to speed work before platform auto kicks in).
- linea_editorial v4.1 full integration: use real datadrop ground-truth (palettes, densities, OCR texts, traits from delivered pieces) for validation §10/11.
- Streamlined daily: always `flujo app` → hub as single workspace for intake + datadrop + delegate + jobs.
- Packaging to standalone .exe (flujo package), more multi-path resilience (UI/CLI/auto/harvest).
- Hygiene, privacy, local analysis only. More agent specialization.

## 🛠️ Cambios recientes

- **v0.34.10:** hotfix del runner de airdrops: evita que `scripts/flujo.py` sombree al paquete `src/flujo` cuando se ejecuta `py scripts/run_airdrop_checks.py`.
- **Datadrop (airdrop inverso) MVP functional:** en hub (`flujo app` → Herramientas/Datadrop) + CLI (`flujo datadrop list|scan|prepare`). Fotos reales terminadas → datadrops/<id>/ + manifests (palette/OCR/traits/for_future_ai) listos para feed IA futura + linea_editorial/v4.1.md §10 validación. Hub delegation paralela + launchers.
- **v0.34.9:** sincronización de documentación para agentes: este contexto,
  El hub (`context/flujo_hub.html`), visualizadores y LAST_HANDOFF quedan alineados con el estado actual.
- **v0.34.8+:** `flujo app` única entrada + app real (APIs+datadrop+SSE+delegate). Confiabilidad airdrop + compact direction + v4.1.
- **v0.34.7:** runner de airdrop compatible con Windows/Git Bash, sin invocar
  bash internamente para apply/checkpoint.
- **v0.34.6:** mapa del repo e higiene estructural.
- **v0.34.5:** guardrails de airdrop, validador y logs de error.

PARA files cubiertos (root + _airdrop/PARA_IA_CONTEXT.md) con datadrop/hub/compact.

## 🔑 Cómo entregas tu trabajo

NO tienes push. Entregas un **ZIP** con carpeta `_airdrop/` que replica la
estructura final del repo, sin subcarpetas de versión. Incluye siempre:

- `HANDOFF_<fecha>.md` o `HOTFIX_<fecha>.md`
- cambios en sus rutas reales dentro de `_airdrop/`
- tests para la lógica nueva
- versión bumpeada en `src/flujo/version.py` y `pyproject.toml`
- changelog en `src/flujo/version.py`
- documentación relevante actualizada

Validación recomendada antes de aplicar:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion"
```

Si el airdrop toca `src/flujo/airdrop.py`, requiere revisión explícita:

```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "vX.Y.Z - descripcion" --allow-airdrop-engine
```

## ⚠️ Reglas innegociables

1. **Instagram:** solo `instaloader`. Prohibido `yt-dlp`.
2. **Entorno:** sin venvs pesados; usar `py` / `python3`.
3. **Privacidad:** `flujo privacy` antes de mandar datos a IAs externas.
4. **Checkpoints:** cada avance commiteado y pusheado, sin mensajes vacíos.
5. **Borrado:** no destructivo; usar scripts de limpieza seguros o documentar
   claramente el movimiento a `_archive/`.
6. **Lógica nueva:** en `src/flujo/`, con tests.

## 🗺️ Pipeline actual

Pedido (correo / JSON) → Privacy Scan → Brief → Job → Proyecto (`config.json` +
plantilla de formato) → Render → Export ZIP.

## 🚧 Próximos pasos (actualizado con foco en continuidad de tokens)

1. **Madurar el Low-Token Continuation System** (`context/LAST_HANDOFF.md` + helpers + `flujo handoff`). Esto es la mejora más importante para que otra IA pueda continuar cuando se acaben los tokens.
2. Implementar `flujo intake json <archivo>` que consuma `schemas/intake.schema.json`.
3. Mejorar layouts/planos/estructuras con primitivas declarativas compartidas (formatos + plano).
4. Decidir canal de recepción automática.
5. Mantener **siempre actualizado** `context/LAST_HANDOFF.md` al final de cada sesión.
6. Usar datadrops reales + linea_editorial v4.1 en flujos de validación (ground-truth de entregas).
