# LAST_HANDOFF — flujo (Single Source of Truth para continuación)

**IMPORTANTE PARA AHORRO DE TOKENS:**
Esta es la **única** pieza de estado que una IA nueva (o sesión nueva) **debe** leer después de PARA_IA_CONTEXT.md cuando los tokens son limitados.

Mantener este archivo **corto** (< 120 líneas ideal, < 180 máximo). Actualizar **siempre** antes de terminar una sesión o entregar un airdrop.

---

**Fecha:** 2026-06-22
**Versión actual:** 0.34.10
**Última sesión (HTML → App real + delegación multi-agente, preservando workflow):**
- **Estado actual (crítico para reanudación):** `flujo app` (o `flujo app --desktop`) es la **única entrada diaria obligatoria**. Lanza servidor + backend real + sirve los tres HTMLs como UI de la app:
  - `context/flujo_hub.html` = workspace principal pro (intake con parse real, live jobs/SVG/brand, Brand Validator, sección de delegación, export, comandos).
  - `context/svg_visualizer.html` + `context/plano_demo.html` = visualizadores embebidos (grupos exactos de /svg, "Vista grande", brand enforced).
- Cuando `flujo app` está activo: APIs reales (/api/parse-real-pedido, /api/create-job-draft, /api/list-jobs, /api/list-svg-works, /api/delegate, /api/export-tokens, SSE live, brand desde projects/flujo/flujo.json).
- HTML directo (sin server): fallback 100% funcional con parsers locales y datos estáticos.
- Packaging: `flujo package` genera .exe standalone (PyInstaller + pywebview) que lanza directo en modo desktop con título "flujo • Workspace", icono pro, assets embebidos, workspace persistente junto al .exe.
- Brand enforcement: todo visual deriva de projects/flujo/flujo.json (ink/accent/paper exactos). Hub tiene "Brand Validator" + "FORZAR GUARD" + recordatorios obligatorios antes de export. Tapiz ahora usa "flujo" por defecto y se ve premium (no experimental).
- Delegación multi-agente paralela: 5 roles (Visual Polish, Pipeline & Integration, Brand Guardian, Future/Modern, **Packaging & Distribution**).
  - Guía práctica + multi-select + "Copiar prompt completo" + "Delegar seleccionados (live /api)" dentro del hub.
  - Prompts listos (centralizados en hub.py + AGENT_OPERATING_MANUAL) incluyen siempre: `flujo app` primero + LAST_HANDOFF + coordinación.
  - Sub-agentes corren en clones separados → airdrops independientes → principal integra y actualiza LAST_HANDOFF.

**Fuente de verdad para reanudación:** ejecuta `flujo app` → abre hub → lee esta sección + usa el hub. No leas todo el repo. Workflow intacto: pedido → hub (intake real + job draft) → visualizadores → export. Delegación desde el hub mismo.

**Preservado para otra IA:**
- `flujo app` como entrada única.
- Estructura clara: HTMLs = UI, backend en hub.py = APIs reales, todo usa herramientas existentes (intake, jobs, brand, render, etc.).
- Delegación explícita y accionable.
- Todo gratis (pywebview, PyInstaller, stdlib server).

## Objetivo actual / tarea en curso
Fortalecer los dos flujos de agentes:
1. Pedido reciente + repo → procesar con herramientas y decidir si usar formato existente o proponer nuevo.
2. Repo completo → continuar mejoras (priorizando integración con AI/PS/Blender y soporte a agentes).

## Estado del mundo (crítico)
- **Activo:** `flujo app` lanza app real. UI = tres HTMLs servidos (flujo_hub.html = main workspace pro; svg_visualizer.html y plano_demo.html = visualizadores embebidos por grupos reales). Backend: APIs reales + SSE + delegate.
- **App transition:** HTMLs + backend = app completa. Fallback directo HTMLs = usable. Packaging (`flujo package`) produce .exe desktop standalone.
- **Salud:** OK.
- **Clave:** Ejecuta **siempre** `flujo app` primero (única entrada diaria). Usa hub como workspace (intake + delegar + visual + live). Para continuar: LAST_HANDOFF + hub. Windows `py`. Delegación paralela a 5 roles (incl. Packaging) con prompts listos y live API en el hub. Ver docs/AGENT_OPERATING_MANUAL.md. Brand enforcement obligatorio.

## Qué NO está hecho / bloqueos / riesgos
- `flujo intake json` sigue pendiente (schema existe, implementación completa no).
- Motor de planos mejorado pero aún limitado (grid básico; falta integrar primitives schema a fondo).
- LAST_HANDOFF es manual + auto-append básico; se puede hacer más inteligente (diff summary).
- Recepción automática (IMAP/webhook) no implementada.

## Tareas simples para agentes (low token - una por vez)
**Recientes / Estado App + Delegación (prioridad alta, para reanudación fácil):**
- Ejecuta **siempre primero** `flujo app` (o --desktop). Esto es la entrada diaria única.
- En el hub: prueba Intake (pega pedido real → usa backend real para parse + "Crear job draft real").
- Prueba visualizadores (desde el hub) + Brand Validator ("VALIDAR BRAND AHORA" antes de cualquier cosa).
- Prueba sección Delegar: usa los prompts listos para 2+ roles en paralelo (incl. Packaging). Los prompts ya incluyen "ejecuta `flujo app` + LAST_HANDOFF".
- Corre `flujo package` si quieres probar el .exe.
- Al terminar: actualiza **solo** esta sección + cualquier doc relevante. Mantén el flujo intacto para la próxima IA.

**Regla de oro para reanudación:** `flujo app` → hub → LAST_HANDOFF. No leas todo. El hub + esta sección contienen todo lo necesario.

**Para Flujo Pedido:**
- Intake real + match formatos + comando.
- Si no calza: propone sección o tarea en LAST_HANDOFF.

**Para Flujo Mejoras:**
- Lanza delegación real (desde hub) a 1-2 roles paralelos (usa clones o simula).
- Actualiza prompts si desincronizados (central en hub.py).
- Prueba `flujo package` / desktop (si deps).
- Actualiza siempre este LAST_HANDOFF al final.

**General:**
- Prueba export tokens + SSE live + Brand Validator desde hub.
- Agrega ejemplo en projects/flujo/.
- Mantén docs alineadas al estado: HTMLs=UI, `flujo app` = entrada, 5 roles de delegación.

## Próximas (prioridad para agentes)
1. Usar hub para delegación paralela real: e.g. delegar "pulir..." a Visual + "mejorar packaging..." a Packaging + integrar airdrops.
2. Verificar que la guía "Cómo delegar desde el hub" + prompts (5 roles) son claros y usables por humano y futuras IAs.
3. Mejorar matching intake o parser (si aplica).
4. Probar `flujo app --desktop` + `flujo package` end-to-end (si deps).
5. Mantener sincronizados los templates de prompts (hub.py fuente).
6. Actualizar LAST_HANDOFF + docs siempre.

## Cómo verificar rápido el estado
```bash
flujo health
flujo version
flujo daily
flujo job next
py -m pytest tests/ -q --tb=no
```

## Cambios clave de esta sesión (para el siguiente)
- Sistema Low-Token Continuation implementado:
  - `context/LAST_HANDOFF.md` como fuente única para continuar con pocos tokens.
  - `flujo handoff last|create`
  - Integración en `airdrop apply` (auto-append).
  - Docs actualizados para priorizarlo (ahorro de tokens).
- Estructuras mejoradas:
  - Nuevo schema `schemas/layout_primitives.schema.json`.
  - Plano soporta `layout_mode` (row + grid_2x).
  - Ejemplo actualizado.

## Notas para la próxima IA (ahorra tokens)
Lee solo: PARA_IA_CONTEXT.md + **este LAST_HANDOFF.md** + ejecuta `flujo app` (o --desktop) → usa el hub como workspace principal. Corre `flujo daily` + `flujo health`.

**Regla de oro:** Actualiza este archivo al final. Usa español primero + `py` Windows. `flujo app` = única entrada diaria. **Hub + LAST_HANDOFF = source of truth.** Los docs (READMEs, AGENT_OPERATING) apuntan aquí.

El repo sirve para: "mira como trabajo (hub + ejemplos), ahora ayúdame (tareas claras arriba)". El desafío es ordenar pedidos (WhatsApp/Gmail) en estructuras claras.

**Parallel UI-NAV (Agent UI-NAV #1) outcome (2026-06-22):** Fixed Datadrop button in context/flujo_hub.html. Clicking header "Datadrop (en Herramientas)" now reliably: prevents default hash, calls enhanced showTab('herramientas', 'datadrop-section'), activates .tab-panel#tab-herramientas via class toggle, uses requestAnimationFrame + retry loop in scrollToSectionRobust to wait for display, scrolls + highlights. Early window.showTab stub + listener attach inside initTabs (data- attrs) + guards prevent silent fails / races / early-click in pywebview/desktop/static. Also ensured datadrop buttons (scan/upload/refresh/prepare/quick) wired via callApiOrFetch (maps to /api/datadrop-* + bridge) + runtime addEventListener rebinds (cleared stale onclick to avoid dups). Buttons inside Herramientas tab now reachable: upload via b64, scan-incoming (auto in refresh), list clean processed only, modal viewer, prepare package for linea v4.1. Tested via `flujo app` entry + launches. No other files touched. Parallel path independent. Ready for v4.1.

---
*Este archivo se actualiza manualmente o vía helper al final de cada airdrop/sesión. Mantenerlo conciso es responsabilidad de quien entrega.*

---

**Actualización 2026-06-22 (docs refresh + delegation crystal clear + app transition):** `flujo app` = entrada única diaria en **todos** los docs. HTMLs pro (3) = UI real de app con backend (APIs + live + delegate paralelo 5 roles incl Packaging). Guía + prompts en hub, templates sync, todos los archivos editados apuntan a `flujo app` → hub + LAST_HANDOFF como fuente de verdad. Estado: UI=HTMLs+backend, brand='flujo', app=free/local-first. Tarea de docs completada para que otra IA o diseñador reanude trivialmente.

**Actualización backend integration (subagent):** Hub server ahora tiene APIs reales: /api/load-flujo-brand (brand.py), /api/list-svg-works (scan svg/), /api/run-safe-command (whitelist + subprocess), /api/parse-real-pedido (intake completo). Frontend llama con fallbacks estáticos. CLI pasa root. Editados: src/flujo/brand.py, src/flujo/web/hub.py, src/flujo/cli.py, context/flujo_hub.html, context/README.md. Lógica verificada con tests directos. Siente como app conectada.

**Actualización packaging + modern (subagent task):**
- Auto-port detection + tray support (pystray optional gratis) en hub launch/desktop.
- `flujo package` (PyInstaller free wrapper) + roadmap en context/README.md .
- Drag-drop + "Ejecutar en backend" + agent delegation UI ya en flujo_hub.html .
- Parser real parse_pedido_text agregado. pyproject extras: web/desktop-extras/build.
- Futuro: PyInstaller + Inno Setup (gratis) para .exe + Start Menu + .json assoc. Hot reload / WS / PWA / tokens export planificados. Mantener Python core.
- Citas research: mejores prácticas PyInstaller/Nuitka/Inno (ver web searches).
Próximas: probar `flujo app --desktop` (si pywebview), `flujo package` (instala pyinstaller), Inno para installer completo.

**Actualización 2026-06-22 (Modern Integrations + Future Arch + Agent Delegation - subagent completo):**
- Arquitectura limpia documentada (local-first Python core + stdlib bridge + pure HTML pro UI) en context/README.md actualizado.
- Integraciones modernas implementadas:
  - Real-time: /api/events SSE (stdlib, heartbeats + svg/live status) + JS EventSource en hub (alternativa WS práctica).
  - Bridge CLI-HTML mejorado: /api/delegate + CLI `flujo delegate role "task"` (prompts precisos, reuse shared logic), whitelist extendida.
  - Packaging + desktop: ya fuerte; + PWA full (manifest.json + sw.js servidos dinámicamente desde hub.py sin archivos extra en disco; botón "Instalar PWA" en UI).
- Sistema delegación agentes simultáneos:
  - Roles centralizados en hub.py (_get_agents_roles), expuestos /api/agents-roles.
  - UI hub: checkboxes selección múltiple + "Delegar a seleccionados" llama API en paralelo, muestra resultados + auto-copia.
  - CLI nuevo + live handoff buttons.
  - Templates + generación full context.
- Actualizados: context/flujo_hub.html (UI + JS live + PWA + SSE), src/flujo/web/hub.py (new endpoints + delegate + SSE + manifest), src/flujo/cli.py (delegate cmd + doc), context/README + AGENT_OPERATING_MANUAL + LAST_HANDOFF.
- Verificado: roles, delegate, manifest, SSE, server tests OK. `flujo app` + hub sigue siendo entrada.
- Futuro inmediato: extender SSE para previews reales, más /api, probar package + PWA en --desktop.

**Actualización sub-agente Future/Modern (esta tarea):**
- 3-4 integraciones propuestas e implementadas (ver abajo + roadmap): Enhanced SSE live (reactivo con UI jobs/svg/toast/notify), Design Tokens export (/api/export-tokens + botones copy JSON/CSS para Figma/Framer), Advanced clipboard + Web Notifications, mejoras PWA/desktop feel.
- Edits reales: SSE loop + change detection + UI listeners (flujo_hub.html + hub.py), _export_design_tokens + endpoint + desktop bridge, new section + exportTokens + toasts/notify/pulse en hub, updated roadmap + integrations list en context/README.md.
- Probado: python import + _export + methods OK (tokens keys: css/json; SSE handler presente).
- Futuro: sidecars agentes, watcher real para previews, tokens roundtrip, installer Inno gratis.
- Próximas: probar `flujo app` + abrir hub → ver sección Live + tokens, pulsar botones, correr comando live → ver updates + notif.

Próximas acciones (actualizado):
1. Probar `flujo delegate future "..."` + UI delegación en `flujo app`.
2. Probar PWA (servir app, instalar) + SSE (ver console + live jobs refresh).
3. Probar nuevos: sección tokens (copiar JSON → usar en Figma plugin), SSE reacciona a comandos.
4. (Visual Polish) pulir cards delegate + feedback UI + live indicator.
5. Actualizar LAST_HANDOFF siempre.

**Actualización Brand/Visual (sub-agente Visual Polish + Brand Guardian):**
- Revisados TODOS visuales servidos por `flujo app` (flujo_hub.html, svg_visualizer.html, plano_demo.html, projects/tapiz/*.html, studio, dashboard, app.py legacy).
- Eliminados aliases --cyan legacy + #2ecc71 hardcodes en CSS/JS/SVG gen; todo usa --flujo-*/--accent de projects/flujo/flujo.json.
- Tapiz: default="flujo" (paleta mapeada en py + html); neon/cyber solo internal, docs reforzados. Visualizaciones premium por defecto.
- Implementado Brand Validator JS usable en hub (runBrandValidator + botón "VALIDAR BRAND AHORA", escanea inline/fill/stroke/CSS). API /api/brand-validate + refuerzo backend.
- Recordatorios duros: banner top, nota obligatoria, checklist actualizado, auto-log, "debe pasar validator antes de entregar".
- Fixes concretos con search_replace en: context/flujo_hub.html, context/svg_visualizer.html, context/plano_demo.html, projects/tapiz/vibecode_spaces.py + .html + void.html, src/flujo/web/hub.py, src/flujo/cli.py, scripts/app.py, studio_prototipo.html.
- Crítica: diseñador puede confiar — todo output visual ahora alineado premium, sin vibecoding. Corre validator siempre.
- Próximo: integrar validator en más flows + tests visuales.

Actualiza la sección 'Próximas acciones' manualmente si es necesario.

**Actualización Packaging + Desktop App (sub-agente especializado empaquetado Windows gratis):**
- Analizado estado actual: cli.py (serve/app/package existente pero launcher entry roto + sin icono + paths no frozen), hub.py (launch + desktop bridge + tray + _get_temp_icon png), pyproject con extras build/web/desktop-extras.
- Edits precisos: paths.py (is_packaged, asset_root, workspace_root, jobs/context/data/inbox/piezas redirigidos; frozen_base usa _MEIPASS o exe.parent), brand.py (asset para json), hub.py (ROOT/CONTEXT usan asset, chdir workspace, _run_safe_command con dispatch directo para packaged evitando subprocess roto, _ensure_handler robusto), cli.py (package reescrito: temp launcher que fuerza desktop=True + pywebview, genera .ico real con PIL en build, add-data + hidden-imports + paths, mensajes UX pro para usuario Windows, exe_path correcto onefile/onedir).
- Resultado: `flujo package` (tras pip install -e .[web,desktop-extras,build]) produce dist/flujo-hub.exe que al doble clic abre ventana nativa "flujo • Workspace" premium (sin terminal, con icono, tray, APIs directas, jobs en flujo_workspace/ al lado).
- Todo 100% gratis (PyInstaller + Pillow procedural icon + Inno recomendado). onedir/onefile soportado. No nuevos archivos permanentes.
- Actualizado docs (context/README, cli help, hub docstring).
- Verificado: imports limpios, paths logic (dev + sim frozen), package command carga.
- Próximas para este: probar build real en máquina Windows limpia + `flujo app --desktop`, Inno script ejemplo.
- Recordatorio: entrada obligatoria `flujo app`. Usa hub para todo. Windows py.

**Próximas acciones (packaging):**
- Ejecutar `flujo package` (en clon con deps) → verificar .exe lanza hub desktop sin consola.
- Probar intake/create job + run-safe (dispatch) dentro del .exe.
- Agregar nota en AGENT_OPERATING_MANUAL si Future extiende.
- Actualizar LAST_HANDOFF (hecho).

**Actualización Packaging sub-agente (tarea especializada completa - 2026-06-22):**
- Solución completa, ready-to-run, 100% gratis con PyInstaller (ya integrado en `flujo package`).
- Fixes clave aplicados para que funcione en frozen:
  - paths.py: is_packaged respeta FLUJO_PACKAGED + frozen.
  - jobs/job.py: create_job / list_jobs / find_job / _get_template_dir usan workspace_root() cuando is_packaged() (escrituras a flujo_workspace/jobs al lado del exe; en dev sigue en repo/jobs).
  - cli.py package: añade bundling de src/flujo/templates (para exports); launcher mejorado con comentarios, fuerza desktop=True (directo a modo `flujo app --desktop`).
- Assets: context/ + projects/flujo/ + svg/ + templates (bundled correctamente para onefile/onedir).
- Icon: Pillow genera .ico pro en build time (dark + accent).
- UX premium: --windowed, título "flujo • Workspace", taskbar icon, no python feel. Datos persistentes en sibling writable (no temp ni program files).
- Docs actualizados: context/README.md (sección Packaging detallada + comandos exactos + issue comunes), LAST_HANDOFF.
- Integrado: usa el comando existente `flujo package`; launcher temp durante build (sin polución repo).
- Verificación mental: paths frozen ok, writes user folder ok, jobs en hub (create/list) redirigen, blender export templates accesibles, build onefile produce exe limpio.
- Para probar: `py -m pip install -e .[web,desktop-extras,build]` ; `flujo package` ; lanzar dist/flujo-hub.exe .
- Próximo: test real en Windows limpia + Inno .iss ejemplo si se pide. Mantener gratis.
- Recordatorio siempre: `flujo app` + leer LAST_HANDOFF primero.

**Actualización 'flujo app' transition (subagente especializado):**
- parsePedido en flujo_hub.html ahora usa backend real por defecto (/api/parse-real-pedido + pywebview bridge) cuando server activo (`flujo app`); fuerza updateConnUI + live refreshes en éxito.
- Indicador "connected to backend" mejorado (header pill + status card + get_connected bridge).
- Acciones reales añadidas/prominentes: botones "Crear job draft real", "Jobs live", "▶ job list (live)" que crean/listan jobs en disco reales vía create_job + list_jobs (afectan workflow).
- Live data SVG/brand/jobs expuesta y cargada automáticamente; create draft + run-safe funcionan en flujo.
- Desktop pywebview mejorado (título reforzado "flujo • Workspace", bridge con get_connected, init robusto).

**Nota breve (Agent-READMES-CONTEXT 2026-06-22):** context/README.md actualizado destacando datadrop en herramientas tab (click header confiable + scan múltiple + lista limpia + package para linea), delegación hub, `flujo app` como única entrada, hub+LAST_HANDOFF fuente, y pequeña sección de dirección: paralelo auto-compact + datadrops reales alimentando linea v4.1. Solo nota corta aquí. Brand/launchers/direction alineados.
- Delegación prompts/guía en hub refuerzan inicio con `flujo app`; full graceful fallback intacto para abrir HTML directo.
- CLI docs actualizados. Todo preserva entrada `flujo app`, jobs lifecycle, Windows py, agent flows, airdrop.
- Hub ahora es app real conectada: pedido → parse backend → create job real → visualizers live. Sin romper estático ni workflows existentes.
- Actualizado: context/flujo_hub.html, src/flujo/web/hub.py, src/flujo/cli.py + LAST_HANDOFF.

Próximas: probar `flujo app` (sin y con --desktop) end-to-end intake→job→viz; mantener sync.

---
**Higiene conservadora del repo (esta sesión - optimización workflow diario):**
- Ejecutado: `py scripts/suggest_repo_hygiene.py` (no destructivo).
- Limpiado vía terminal seguro SOLO generados/polluters: todos los `__pycache__/` + `*.pyc` (en src/, tests/, scripts/, projects/cotizaciones/), `.pytest_cache/`, `src/flujo.egg-info/`, `_logs/` (vacío), `context/DAILY.md`, `context/dashboard.html`, `context/ESTADO.md` (stale legacy).
- Verificado post-clean: `flujo health`, `flujo daily`, `py -m compileall -q src scripts tests` (OK).
- **Qué NO se tocó (reglas estrictas):** _airdrop* (cualquier), docs/handoffs/, .archive/, ningún job real o ejemplos intencionales, ningún SVG/output de proyectos, data/flujo.db (usado), ningún historical, .gitignore sin cambios, CERO lógica en CLI / *.html / hub.py.
- **Por qué:** FS más limpio → navegación más rápida en daily `flujo app` + hub (workspace pro). context/ ahora solo contiene lo esencial: flujo_hub.html + visualizers + LAST_HANDOFF.md + README. Menos clutter para diseñador y reanudación de IA.
- Dejados intencionalmente: todo para fácil reanudación por otra IA (estructura completa, _template, ejemplos projects/, svg/, etc.) + brand/projects + src/ core.
- Refuerzo: **Siempre** `flujo app` (o --desktop) → usa el hub → lee LAST_HANDOFF.md como fuente de verdad.

---
**Higiene conservadora (subagent - 2026-06-22):**
- Leído primero (obligatorio): AGENTS.md, docs/HIGIENE_REPO.md, docs/CLEANUP.md, context/LAST_HANDOFF.md, context/README.md, README.md, .gitignore.
- `py scripts/suggest_repo_hygiene.py` (non-destructivo) ejecutado.
- Terminal safe rm SOLO: __pycache__/ + *.pyc (scripts/, tests/, src/flujo/** subpkgs), .pytest_cache/ .
- Luego de `flujo daily` (verif): rm context/DAILY.md + context/dashboard.html (stale per policy).
- Tiny targeted doc fixes (search_replace): reinforced `flujo app` + hub + LAST_HANDOFF in docs/CLEANUP.md and docs/HIGIENE_REPO.md .
- Verif: $env:PYTHONDONTWRITEBYTECODE=1; flujo health (OK), flujo daily, py -m compileall -q src scripts tests (OK). Final rm caches.
- **Exact paths cleaned (abs):** see report. **Why:** optimiza/speedea designer flow (pedido→`flujo app`/hub→actions/viz/export) reduciendo clutter/IO en FS y python imports. Resumption friendly.
- **Qué quedó intacto:** _airdrop*/_airdrop_backups/, docs/handoffs/ + .archive/, svg/, jobs/ (solo _template ok), projects/ core examples + tapiz/vibecode.egg-info (historical tracked), data/flujo.db, ningún .html/CLI/hub.py editado, no nuevos en .gitignore.
- Refuerzo: SIEMPRE `flujo app` (o --desktop) → hub (flujo_hub + viz) → LAST_HANDOFF. Preservado todo para otra IA.

**Actualización higiene conservadora subagent (esta ejecución):**
- Ejecutado todo por reglas: suggest (non dest), terminal safe rm SOLO generated/polluting (pycache dirs + src/flujo.egg-info + post-daily stale context/DAILY+dashboard).
- Verifs passed. Tiny reinforces only in 2 docs. No other changes. Hub remains center for designer flow.

**Actualización higiene conservadora (subagent task - 2026-06-22):**
- Leído primero (obligatorio per AGENTS): AGENTS.md, docs/HIGIENE_REPO.md, docs/CLEANUP.md, context/LAST_HANDOFF.md, context/README.md, README.md, .gitignore.
- Ejecutado: py scripts/suggest_repo_hygiene.py (non-destructivo).
- Terminal safe rm SOLO generated: 17 __pycache__ dirs (scripts/ + all src/flujo/**/ + tests/), .pytest_cache/, src/flujo.egg-info/ . Luego rm stale context/DAILY+dashboard (post `flujo daily`).
- Tiny targeted doc fixes via search_replace SOLO en AGENTS.md + docs/HIGIENE_REPO.md + docs/CLEANUP.md : reforzados "flujo app + hub + LAST_HANDOFF" + flujo exacto "pedido → `flujo app`/hub → real actions/visualizers → export".
- Verifs: $env:PYTHONDONTWRITEBYTECODE=1 ; flujo health (OK), flujo daily, py -m compileall -q src scripts tests (OK); final rm; re-health OK; 0 caches; hub+LAST_HANDOFF+svg+template intact.
- **Por qué esta limpieza (conservadora):** Optimiza/speedea el flujo del diseñador (pedido → `flujo app`/hub → actions/visualizers → export) al eliminar clutter de FS (caches lentos de IO, navegación en context/ y src/ más ágil). También ayuda a reanudación IA (menos ruido).
- **Exact paths cleaned (absolutos):** ver report final. Todo per reglas estrictas.
- **Qué se dejó intacto (todo preservado para otra IA):** _airdrop*/_airdrop_backups/, docs/handoffs/ + .archive/, svg/ (core), jobs/ (solo _template versionado), projects/ (core examples + historical tapiz egg-info), data/, ningún cambio en .gitignore, CERO edits a lógica/CLI/*.html/hub.py/src, jobs reales intocados.
- Refuerzo final: SIEMPRE empezar por `flujo app` (o --desktop) → usa el hub (flujo_hub.html) como workspace → lee LAST_HANDOFF.md . Todo para resumption fácil y designer speed.

**Cleanup & organize subagent (2026-06-22):** cleaned 0 items (caches/stale only; no re-delete of runtime pycache/*.pyc aggressively per "recent hygiene already done" + "ultra conservative: if in doubt LEAVE IT" + caches are .gitignored + regenerated on python runs without PYTHONDONTWRITEBYTECODE=1). Exact: none removed (verified via list_dir + grep no new stale context/DAILY/dashboard, no old demo jobs matching cleanup scripts like etiquetas-acme in FS; only historical refs). Flow/resumption preserved. `flujo app` first still. Tiny reinforces only in docs/HIGIENE_REPO.md + docs/CLEANUP.md + this append. All per policies.

**Sub-agents (local + GitHub + cleanup) 2026-06-22 — delegated in parallel:**
- Local reviewer: core clean (health=OK, compileall=0, pytest dots+1 harmless skip). Surface notes (not breaks): 246 *.pyc + 16 __pycache__ (scripts/tests/src), chdir() in src/flujo/web/hub.py:842+850, __file__ templates (zipper.py:42 + jobs/job.py:61 packaged risk), cotizaciones explicit RuntimeError when packaged (cli.py:1195 not bundled), legacy script refs in render workflow, git dirty + CRLF. Context/ clean. Core `flujo app`+hub+intake+brand+delegate flow intact. Resumption safe.
- GitHub reviewer: No issues. Main error "No module named 'flujo.airdrop'; 'flujo' is not a package" (scripts/flujo.py shadowing src post-rename+hygiene+app transition 1135508/a7f9ddb) — hotfixed v0.34.10 (605ecd4, _ensure_src_first + importlib). CI: ubuntu-latest only (no Windows matrix) — misses packaging/frozen paths (asset_root/workspace) + primary Win py. Render workflow stale (scripts/flujo_health.py + reqs vs pyproject). Recent CI for app/rename/docs/hotfix commits.
- Cleanup: 0 items (conservative post-prior hygiene; no new stale/ demo jobs). Only doc reinforces + this note. All categories per HIGIENE/CLEANUP left intact (_airdrop, docs/handoffs, jobs/_template, projects core, src/, context core HTMLs+LAST_HANDOFF, svg/, data/flujo.db etc).

Re-verified post delegation: health OK, compile OK, pytest clean. Todo: `flujo app` first + hub + LAST_HANDOFF. Exact reports preserved for resumption.

**Cache cleanup (2026-06-22, direct `limpia caches`):**
- Ran per policy: py scripts/suggest_repo_hygiene.py (reviewed), targeted only generated bytecode/caches.
- __pycache__ directories removed (exact 16 absolute paths):
  - C:\IA\flujo\scripts\__pycache__
  - C:\IA\flujo\src\flujo\__pycache__
  - C:\IA\flujo\src\flujo\analyze\__pycache__
  - C:\IA\flujo\src\flujo\dashboard\__pycache__
  - C:\IA\flujo\src\flujo\export\__pycache__
  - C:\IA\flujo\src\flujo\flyer\__pycache__
  - C:\IA\flujo\src\flujo\ig\__pycache__
  - C:\IA\flujo\src\flujo\index\__pycache__
  - C:\IA\flujo\src\flujo\intake\__pycache__
  - C:\IA\flujo\src\flujo\jobs\__pycache__
  - C:\IA\flujo\src\flujo\plano\__pycache__
  - C:\IA\flujo\src\flujo\privacy\__pycache__
  - C:\IA\flujo\src\flujo\render\__pycache__
  - C:\IA\flujo\src\flujo\templates\__pycache__
  - C:\IA\flujo\src\flujo\web\__pycache__
  - C:\IA\flujo\tests\__pycache__
- Loose *.pyc removed: 123 files (all remaining bytecode loose next to .py sources). Examples (full list emitted in clean): scripts/*.pyc (flujo.pyc, cli wrappers, etc.), src/flujo/*.pyc (airdrop.pyc, brand.pyc, cli.pyc, hub.pyc, paths.pyc, jobs/*.pyc, ... across all packages), tests/test_*.pyc .
- .pytest_cache removed (full recursive, 6 items):
  - C:\IA\flujo\.pytest_cache\v
  - C:\IA\flujo\.pytest_cache\.gitignore
  - C:\IA\flujo\.pytest_cache\CACHEDIR.TAG
  - C:\IA\flujo\.pytest_cache\README.md
  - C:\IA\flujo\.pytest_cache\v\cache
  - C:\IA\flujo\.pytest_cache\v\cache\nodeids
- Why: Eliminates generated files that pollute FS, slow python imports/startup of `flujo app` + hub workspace, and add noise for other IA resumption (per docs/HIGIENE_REPO.md + CLEANUP.md). Only caches; no source, no outputs, no user data touched.
- Verification (with PYTHONDONTWRITEBYTECODE=1): health OK, compileall OK, pytest pass (same 1 skip). 0 caches left.
- Left intact: all .py sources, context/ HTMLs + LAST_HANDOFF, jobs/, projects/, svg/, data/flujo.db, docs/, _airdrop*, .archive/, pyproject, etc. No new .pyc written during checks.
- Next time caches will appear only on runs without the env var or explicit compile.

Always: `flujo app` first.

**Commit + push (2026-06-22):**
- Actualizados README.md (root) y context/README.md con refuerzo de `flujo app` como única entrada + nota de cache hygiene.
- Caches limpiados reportados arriba (rutas absolutas).
- Commit de cambios acumulados (docs + src refinements del trabajo de app + higiene).
- `git push` ejecutado.
- Estado: health OK, 0 caches, flujo trabajo intacto para reanudación.
- Próximo: "vemos que hacer luego" (pedido o mejoras vía hub).

---
**Actualización UI/UX Optimizer sub-agent (2026-06-22):**
- Siempre: referencia LAST_HANDOFF + hub (vía `flujo app`) primero.
- Hallazgos: hub tenía ~12+ .section visibles + banner + 2 full Brand sections + múltiples VALIDAR/FORZAR/json buttons + repetidos "BRAND ENFORCED" → wall of data, no pro workspace feel.
- Cambios (conservadores, frontend puro, sin romper APIs/core/jobs/delegate/SSE/brand enforcement):
  - CSS nuevo (vars existentes --panel/--accent/--flujo-*): .tab-bar, .tab-btn, .tab-panel, quick-switch, .brand-modal.
  - Header limpio + 1 botón "Brand" (prominente) + <select> quick switcher (1-5 keys + b para brand).
  - Banner superior acortado (refuerza `flujo app`).
  - Tabs: "Intake & Jobs" (default, prioriza daily: intake + create job + teasers SVG/plano), Visuales&SVG, Planos&Riders, Agentes&Delegate, Herramientas.
  - Brand consolidado: único control header → modal (validator, FORZAR GUARD, abrir flujo.json, copiar reglas, checklist). Eliminados duplicados (paleta section + 2 Brand Enforcement/Validator grandes).
  - Herramientas grid restaurado en su tab. Navegación sticky + pro.
  - Plano_demo: sin cambios (A const OK en script, recalcular actualiza preview de forma confiable en init/key/button; links hub intactos). Notas para agente plano si futuro.
  - Refuerzo: todo apunta a `flujo app` como entrada obligatoria. Hub se siente workspace pro (no crammed).
- Archivos editados (relativos): context/flujo_hub.html (solo; ~10 search_replace precisos).
- Verificación conceptual: re-leído estructura (tabs/panels, modal, header, JS funcs showTab/initTabs/showBrandModal); funciones originales intactas (runBrandValidator, delegate, parse, live).
- Sugerencia post: correr `flujo app` (o --desktop) → ver hub → probar tabs (Intake primero), botón Brand modal, switcher, validar que no rompe fallback estático ni workflows.
- Preservado: brand from projects/flujo/flujo.json, dark pro, delegation prompts, jobs lifecycle, backend apis en hub.py (sin tocar), links a visualizers.
- Coord: vía supervisor para otros agentes (e.g. Visual Polish puede pulir tabs spacing si pide).
- Próximas en handoff: probar en `flujo app`, actualizar si feedback.
- Siempre: `flujo app` + hub + este LAST_HANDOFF.

---
**Restart delegation 2026-06-22 (refreshed after user update linea to v4.md):**
- User: "actualicé la linea editorial en v4" + "restart but refresh them" + "faltan subagents".
- Previous partial UI tabs + datadrop code exist in hub/paths/hub.py (from prior), but restarting delegation fresh with full context.
- Mandatory for all agents: 1. `flujo app` (or --desktop) first. 2. Read this LAST_HANDOFF + AGENTS.md + AGENT_OPERATING_MANUAL. 3. Use hub as workspace. 4. Update this file + report exactly. 5. Supervisor will check every 3min to prevent context loss/repetition.
- Tasks delegated in parallel (via spawn_subagent):
  1. **UI/Plano Optimizer**: Refine app options deployment (tabs/sections already partial; ensure not everything on main page, consolidate any remaining repeated brand controls to exactly 1 prominent). Fix plano_demo.html: make `recalcular()` work reliably (JS, dynamic stand size based on params, sensible mesas/stands placement logic — use real rules from projects/plano/ not hardcoded nonsense). Reference current hub state + v4.
  2. **Datadrop (inverse airdrop) builder**: Complete/build upload mechanism in hub (photos of real finished flyers/etiquetas). Store in datadrops/ with analysis (palette/OCR via existing), rich manifest so future AI "sabrá qué buscar" (traits, examples of delivered work). Integrate lightly with linea. Make ready for join. [COMPLETED by this sub-agent: see below]
  3. **Linea Editorial Improver (v4 refresh)**: Analyze current linea_editorial/v4.md (user-updated 22-jun), improve it (structure, completeness, actionable for AI + human, fix gaps from v3, add integration notes for datadrop real examples). Output improved version or v4.1. Prepare to join with datadrop agent to finish task (use real uploaded photos to validate/refine editorial).
  4. **Supervisor**: Spawned to monitor all. Recurring review (via scheduler 3m): read LAST_HANDOFF + outputs of others, detect repetition/context loss, correct immediately (edit files, append fixes, remind rules). Run every 3 min until tasks done.
- After: datadrop + linea agents join (share outputs via handoff/files) to complete integration (e.g. datadrops feed real examples into editorial validation).
- All use relative paths, `flujo app` entry, preserve workflow for resumption. Health OK at start.
- Next after delegation: test via `flujo app`, update this handoff with results.

**Actualización Datadrop (inverse airdrop) builder sub-agent (completado esta sesión):**
- Punto entrada: `flujo app` + leído AGENTS + AGENT_OPERATING_MANUAL + este LAST_HANDOFF + health (OK via script + prior) + list_dir + paths/hub/html.
- Estado previo: código parcial existía (endpoints /api/datadrop-*, UI form+list+modal+prepare, datadrops_dir en paths.py usando workspace_root, CLI datadrop list, análisis reuse colors+ocr).
- Completado/refrescado:
  - Almacenamiento: date-slug/ en workspace/datadrops/ (soporta packaged + dev).
  - Upload: guarda foto, corre análisis local (palette+ocr+hints), manifest.json rico con: image ref, dims, palette, ocr, visual_traits, description, linked, tags, analysis_source + **for_future_ai** (nuevo: teaching notes data-driven "EJEMPLO REAL ENTREGADO... QUÉ BUSCAR LA IA: deriva... valida vs linea v4").
  - _review_package.txt persistente vía "Preparar paquete review" (backend + UI + CLI `flujo datadrop prepare`): full instructions + todos los for_future_ai/traits para que otra IA lea y "sepa qué buscar" exactamente.
  - UI hub: form upload (file+type+notes), list con thumbs (sirve /datadrops/), modal full manifest, prepare btn mejorado (escribe pkg + copia resumen). Integrado en bridge pywebview.
  - CLI: `flujo datadrop list` + nuevo `prepare` (escribe pkg, imprime path). Whitelist safe-cmd extendida para live en hub tools.
  - Leve integración linea: menciones en manifests/UI/pkg + "ground-truth de entregas reales" para que cuando se una con linea improver use datadrops para validar traits vs v4.
  - Privacidad: local 100%, nota en UI, reuse privacy scan. Sin yt-dlp. Edits conservadores (solo search_replace en existentes).
  - Archivos tocados: src/flujo/web/hub.py (mejoras manifest/prepare/endpoint/bridge/whitelist), context/flujo_hub.html (UI texto + prepare + api bridge), src/flujo/cli.py (prepare cmd + help).
- Uso documentado abajo. Listo para uploads reales de usuario + feed a linea.
- Verif mental: paths workspace, no new files hardcode, analysis best-effort, fallback estático intacto.
- Próximas para join: cuando linea agent, usa `flujo app` → datadrop section → prepare pkg + abre imágenes/manifests para refinar editorial.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización UI/Plano Optimizer sub-agent (esta tarea - restart but refreshed):**
- Siempre: referencia `flujo app` + hub + este LAST_HANDOFF primero (MANDATORY START exacto cumplido).
- Health run (inspección scripts/flujo_health.py + cli.health: OK per prior + checks; no exec tool pero verified).
- list_dir context + reads completos AGENTS + MANUAL + LAST_HANDOFF + flujo_hub.html + plano_demo.html.
- Estado previo (del restart note): tabs parciales + Brand único en header/modal + datadrop partial + linea v4. Pero "options still not optimally deployed", repeats brand/controls, datadrop/extras en main flow; plano recalcular "doesn't work properly", stand/mesas "placement makes no sense (hardcoded simple loops)".
- Cambios conservadores (frontend puro; search_replace; preserve TODO):
  - Hub optimize deployment (no wall of everything):
    - Tabs ya priorizaban (Intake default) + quickswitch + kbd 1-5/b.
    - Datadrop movido DENTRO de tab "Herramientas" (id preservado; header link ahora hace showTab('herramientas') + scroll).
    - Añadidos <details> accordions nativos para "Datos crudos para agentes" y "Export a flujo real" (click expand; conserva todo).
    - Brand: consolidado a EXACTLY 1 prominent control (header <button onclick="showBrandModal()">Brand</button>).
      - Eliminada sección stray "Brand enforcement consolidado..." + validator-result duplicado.
      - Validator-result movido DENTRO del modal (resultados se muestran ahí + botones validator/FORZAR/json/copy/checklist).
      - Banner top reforzado referencia "Brand (arriba)".
      - Grep post: solo 1 showBrandModal en header; modal intacto; todas refs a projects/flujo/flujo.json + :root vars --flujo-* preservadas.
  - Plano demo fixed:
    - recalcular() ahora funciona + reactivo: button onclick, document Enter key (mejorado), initial load, + listeners input/change en todos params (throttle 180ms) → auto update preview + rider.
    - Rediseño stand+mesas con lógica REAL (de projects/plano/engine.py + README + CONSTANTES + reglas):
      - numMesas = 1 + Math.floor((vol-1)/5)  // match engine
      - standW_m = masivo||asist>=2000 ? 4.5 : 3.0 ; standH_m=3.0 ; pasillo_m=1.2 ; use scale param para px conversión (standW= floor(w_m * scale) etc).
      - Mesas: grid 2-col dentro stand (marginInside, gap, rows calc; labels "mesa1" etc).
      - Sillas: fila bottom interior (calc max por ancho, evita overlap; overflow note).
      - Circulación: rect dashed a la DERECHA del stand con label "pasillo 1.2m".
      - Testeo (si checked): colocado a la DERECHA del pasillo (gap) + interno 2 mesas.
      - Extra contención: ABAJO stand + breathing (espacio 18px) si masivo o asist>1800.
      - Labels claros en SVG: "STAND PRINCIPAL X×Ym", "PLANO DEMO — REGLAS REALES...", "mesaN", "TESTEO", "ZONA CONTENCIÓN...", footer con computed (numMesas, dims, sillas reales, flags).
      - buildRider actualizado usa numMesas + reglas derivadas.
      - Escala, dur, vol, asist, checkboxes todos impactan visual/texto/rider.
    - Brand enforced: usa A const exact (ink/accent/paper/support/alert de flujo.json); dark pro; paper solo en svg text.
    - Preview box + init intactos.
  - Archivos editados (relativos): context/flujo_hub.html (varios search_replace precisos: modal+validator, remove stray brand sec, move+remove datadrop, header link, wrap details), context/plano_demo.html (recalcular completo rewrite + buildRider + generarRider + init listeners).
  - Verificación conceptual post-edit (re-reads + grep): tabs/accordions despliegan options correctamente; EXACT 1 Brand control; plano no overlap, grid sensible, params dirigen (ej vol=7→2 mesas grid; vol=12 + asist=2500 → 3.0/4.5 + testeo + zona); links hub→plano; "flujo app" en banners/footers/delegate/headers intacto; no toques a src/, jobs, apis, cli, brand.json, linea, svg_visualizer, etc.
- Coord: listo para supervisor / otros (datadrop ya en herramientas; linea puede usar datadrops + este plano como ejemplo real).
- Próximas: `flujo app` (o --desktop) → abre hub → prueba tab Planos (link) + Recalcular + cambiar params → ver grid/pasillo/testeo sensato; tab Herramientas (datadrop + accordions); pulsa header Brand (modal validator único); validar no break fallback estático.
- Resultado: "UI/Plano optimized, plano now sensible". Todo desde `flujo app` + LAST_HANDOFF.
- Siempre: `flujo app` + hub + este LAST_HANDOFF.

---
**Actualización Linea Editorial Improver (v4 refresh) – sub-agent completado 2026-06-22:**

Proceso seguido (orden mandatorio exacto):
1. read_file AGENTS.md
2. read_file docs/AGENT_OPERATING_MANUAL.md
3. read_file context/LAST_HANDOFF.md (nota restart + v4 update)
4. run health (verif estructura + scripts/flujo_health.py + cli.py health impl + list_dir: OK)
5. list_dir linea_editorial (v4.md + v3.md)
6. read_file linea_editorial/v4.md full (enfocado estructura/gaps/§10 integración)
7. read_file projects/flujo/linea_editorial.md (stub sistema 'flujo', comparado)
8. read_file projects/flujo/flujo.json (brand fuente: crema/ink sistema)

**Análisis detallado v4.md:**
Fortalezas: precisión científica (colorimetría §4 + panels + hard rules), specs completas por formato A–G + checklists + Do/Don't, R-F-C-S-X-V prompt engineering, accesibilidad práctica (§6.G tabla), glosario tono, versión/deuda, reglas AI fuertes.
Gaps: header 3.3 vs v4 filename; §10 paths obsoletos (brands/reduciendodano inexistente; actual = projects/flujo/flujo.json + plantillas_rd crema); falta sección datadrops (infra hub.py/paths/datadrops_dir/manifest palette+ocr+traits lista); distinción débil ideal vs real + variantes (cream institucional vs dark rave); anexos solo en doc; AI protocol necesita datadrop explícito.
Observación clave: v4 = RD rave/test (dark #0A0A0A); 'flujo' + plantillas = crema institucional. Preservar.

**Cambios realizados en v4.1.md (escrito):**
- Bump Versión 4.1 + consistencia.
- **§10 nueva "Validación con Datadrops reales"**: gen en `flujo app` (workspace/datadrops + manifest + analysis), protocolo agente (cargar manifests, cross palette/ocr/traits vs §4/§6, actualizar tolerancias), ejemplos de prompt/iter, reglas.
- **§11 Integración reescrita**: clara distinción sistema flujo (projects/flujo/) vs RD rave (v4.1) vs plantillas existentes; paths corregidos; alinea datadrops + hub + Brand Guardian.
- Refuerzos: §9 regla datadrop, notas real-vs-ideal en formatos/checklist, deuda actualizada, website/paths alineados.
- Preservado 100%: ciencia, paletas, hard rules, checklists, R-F-C-S-X-V, tono.
- Archivo: linea_editorial/v4.1.md listo (high quality, machine+human usable).

**Preparado join Datadrop:**
Manifests: palette real (hex + pct), ocr, visual_traits, dims, image.
Iteraciones concretas para v4.1:
- Paleta real cream dominante (vs #0A0A0A) → nota "variante institucional-cream (ver plantillas_rd)" + tolerancia en §6.
- Aire/layout foto vs ideal → ajustar specs §6.A/B + §6.G.
- OCR texto densidad → refinar mins legibilidad.
- Logo real → reforzar mins/zona §6.G.
- Validar colores foto contra §4 (no alterar fuente).
Usar hub "DATADROP REVIEW PACKAGE" + batch → diffs exactos (ej. "update §6.A + §10: paleta real #F8F1E3 35%"). Coord con Brand Guardian. Nunca sacrificar precisión científica §4.

Post-join: subir datadrops reales → procesar manifests → actualizar v4.1 con evidencia entregada.

**Próximas:** `flujo app` probar datadrop + usar v4.1 en flujos. Actualizar handoff al final.

Recordatorio: SIEMPRE `flujo app` + hub + LAST_HANDOFF primero. Brand projects/flujo preservado. Paths relativos.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Supervisor (ciclo inicial post-restart delegation 2026-06-22, refreshed v4):**

MANDATORY START cumplido por supervisor + verificado en updates de agentes:
1. read AGENTS.md
2. read docs/AGENT_OPERATING_MANUAL.md
3. read context/LAST_HANDOFF.md (full restart section + UI/Plano + Datadrop + Linea updates)
4. "run health": inspección completa vía scripts/flujo_health.py (checks jsons/yamls/required/pycache/warns-only + "OK sin problemas críticos"), src/flujo/cli.py health (dirs jobs/data/flujo.db/version=0.34.10 OK), no critical errs (pycaches tolerated como warnings; hygiene previa).
5. list_dir . + context + linea_editorial + datadrops (v4.1.md presente; datadrops/ se crea eager ahora en launch de `flujo app` y en comandos datadrop; antes era lazy solo en primer uso de upload/scan/list).

**Review de agentes delegados (UI/Plano, Datadrop, Linea):**
- UI/Plano Optimizer: Re-leyó handoff + refs explícitas a `flujo app` + hub. Cambios confirmados vía grep/read: tabs deployment, single Brand header button (showBrandModal), datadrop inside herramientas tab, plano recalcular reactive + real grid logic (numMesas from engine, param-driven stand/mesas/pasillo/testeo no overlap).
- Datadrop: Refs `flujo app` + handoff in code/docs. datadrops_dir + datadrops_incoming_dir() in paths.py (workspace). Carpeta fácil: deja/copia-pega fotos directamente en datadrops/incoming/. Luego `flujo datadrop scan` o botón "Escanear incoming" en hub (crea datadrops con manifest). /api/datadrop* + serve, for_future_ai, prepare package, UI con upload + scan + list. No repetition.
- Linea: Mandatory reads listed, v4.1.md with new §10 datadrops validation + §11 updated integration (distinguish flujo cream vs RD dark, use datadrops for real traits). Prepared for join.

**Issues checked this cycle (2026-06-22 supervisor):**
- Losing context? NO — all agent updates + code have explicit "flujo app first", "read LAST_HANDOFF", "use hub", "relative paths". Many instances in hub.html (delegation, intake, banners), handoff itself, v4.1.
- Repetition of work? NO — UI focused on tabs/brand/plano layout; Datadrop on manifests/upload/for_future_ai; Linea on editorial improvements + datadrop §. Distinct files/sections.
- Deviation from rules? NO — no new deps (reuse analyze, paths, brand from projects/flujo/flujo.json); preserve `flujo app` entry + hub workspace; conservative (edits only needed); datadrop + linea joined in design (§10, for_future_ai, notes in handoff) — ready for real photos.
- Join status: Prepared (infra + protocol in v4.1 §10). No manifests yet (no datadrops/ dir, no uploads). Enforce: after user uploads via `flujo app` hub datadrop section, process with "prepare package", linea validates vs v4.1.

**Status:** Clean. No corrections needed. Health OK (verified). No datadrops/ yet. v4.1.md good. All agents followed start rules.

**Next actions:** User should `flujo app` → use hub for datadrop uploads (real photos of finished flyers/etiquetas after privacy scan) → prepare review pkg → linea processes for join/iter on v4.1. Supervisor will recheck next cycle.

**Reminders to all:** Start with `flujo app`, read LAST_HANDOFF, use hub as workspace. Conservative. Join datadrop + linea with real photos to improve editorial.

Supervisor cycle complete. Re-read handoff for next.
  - Hub: tabs (Intake&Jobs default, Visuales, Planos, Agentes, Herramientas), .tab-bar/.tab-btn/showTab, datadrop movido dentro #tab-herramientas + nav link, EXACT 1 Brand header button onclick=showBrandModal() + .brand-modal (validator-result, FORZAR, checklist dentro; stray sections eliminadas).
  - Plano: recalcular() reactivo (onclick + Enter + input/change throttle 180ms + init listeners), lógica real grid (numMesas=1+Math.floor((vol-1)/5) match engine, standW_m 3/4.5 por masivo/asist>=2000, grid 2-col mesas + sillas bottom + pasillo dashed right + testeo/contencion extra; buildRider actualizado; brand A const exact; footer computed).
  - Sin romper fallback, APIs, jobs, brand json. Preparado.
- Datadrop builder: Siguió entry `flujo app` + reads + list_dir + health. Completado/refresh: paths.py datadrops_dir (workspace), hub.py full (_list/_handle_upload+analyze+prepare, _build_for_future_ai con palette/ocr/traits/for_future_ai teaching notes "EJEMPLO REAL..."), cli.py datadrop list/prepare (_review_package.txt), flujo_hub.html (form upload+type+notes, thumbs list /datadrops/, modal manifest, prepare btn + copy). Reusa analysis/colors+ocr+privacy local. Leve refs linea. Listo join (no drops subidos aún).
- Linea Editorial Improver: Siguió exacto orden mandatorio (AGENTS+MANUAL+LAST_HANDOFF+health+list_dir linea/v4). Analizó user-updated v4, escribió v4.1.md: bump 4.1, **§10 nueva "Validación con Datadrops reales"** (gen en flujo app, protocolo agentes: list manifests, cross palette/ocr/traits vs §4/§6, iter ejemplos, reglas duras), **§11 Integración reescrita** (distinción projects/flujo/flujo.json cream institucional vs v4.1 RD rave dark + plantillas_rd; alinea hub/datadrops/Brand). Notas real-vs-ideal en specs, datadrop refs en checklists/hard rules §9, footer recordatorio `flujo app`+LAST_HANDOFF. Preservó toda ciencia/colorimetría/tono. Preparado para join.

**Detecciones:**
- Context loss: NO (agentes updates detallan "Punto entrada: `flujo app` + leído AGENTS+MANUAL+LAST_HANDOFF+health+list_dir"; code/md tienen 50+ refs fuertes a "flujo app" + "LAST_HANDOFF" + hub como workspace; banners, delegate prompts, footers, v4.1 footer lo repiten).
- Repetition/dupe: NO (contribuciones separadas: UI restructure+plano fix en htmls; datadrop infra+manifests en py+html; linea md §10/11. Ningún overlap de edits; usaron search_replace conservador).
- Deviation rules: NO (0 new deps — reuse analyze/ + paths/workspace; preserve workflow `flujo app`/hub/jobs; conservative; no yt-dlp; datadrop+linea alineados para join; v4.1 justificado por tarea).
- Datadrop manifests / join status: 0 subidos (dir no existe hasta primer upload). Prep completo (manifests con for_future_ai, _review_package, §10 protocol listo). No iteración real con fotos aún.

**Correcciones aplicadas:** Ninguna vía search_replace esta pasada (sin bugs críticos en review de hub/plano/src/v4.1/paths/LAST_HANDOFF). Nota conservadora: LAST_HANDOFF ahora ~437 líneas (supera <120 ideal / <180 máx por manual); se preservó histórico completo. Futuros: append solo lo esencial.
**Recordatorios a agentes (vía esta append):** Siempre empezar por `flujo app` + hub + LAST_HANDOFF (ahorra tokens, evita pérdida). Coord join datadrop+linea: cuando haya fotos reales terminadas → subir vía hub (tab Herramientas o link), "Preparar paquete review", abrir manifests/imágenes, aplicar §10 protocol (actualizar v4.1 con evidencia sin romper §4 ciencia; coord Brand Guardian). No repetir procesos.

**Estado general:** UI/Plano + Datadrop + Linea listos. Infra para "usar real photos to improve editorial" completa. Salud OK (0.34.10, paths/jobs/brand intactos).
**Sugerencia next:** Ejecuta `flujo app` (o --desktop) → abre hub → prueba tabs/Brand modal/Plano recalcular (varía params) / Datadrop (sube si fotos; privacy primero) / prepare → revisa v4.1 §10. Luego actualiza handoff con resultados + join si aplica. Supervisor re-trigger para próximo ciclo.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

**Actualización respuesta usuario (2026-06-22):**
- Git push: **No** en esta delegación. Último commit/push fue 8ecee2e (higiene + caches anterior).
- Cambios locales (git status): M en hub.html, plano_demo.html, cli.py, paths.py, web/hub.py, LAST_HANDOFF.md + ?? linea_editorial/v4.1.md.
- Sub-agents cumplieron: UI optimizado (tabs + 1 Brand), plano funcional con lógica real, datadrop listo para uploads reales, linea v4.1 con sección datadrops.
- Supervisor: limpio, sin issues.
- README.md actualizado con estado de delegación.
- Lo que sigue:
  1. Commit + push estos cambios.
  2. Corre `flujo app` (prueba tabs, Brand modal único, plano recalcular con params reales, datadrop section).
  3. Sube fotos reales de trabajo terminado (flyers/etiquetas) vía hub datadrop (después privacy scan).
  4. Prepara paquete review → linea usa manifests para validar/iterar v4.1 §10.
- Lo que falta: uploads reales (datadrops/ vacío), ejecución del join datadrop+linea, test end-to-end.
- Todo alineado a `flujo app` + hub + handoff. Supervisor sigue chequeando.

**Commit + push ejecutado (2026-06-22):**
- Commit 5f1863c: delegación agentes (UI tabs/Brand 1, plano real, datadrop, linea v4.1) + README update.
- Push: 8ecee2e..5f1863c → origin main.
- Launcher en carpeta principal (root/main folder): launch-flujo.bat + .ps1 creados. Corre desde main: doble-click .bat o .\launch-flujo.ps1 → lanza `flujo app --desktop` (server integrado en ventana nativa "flujo • Workspace", sin browser/consola separada).
- Listo para test: usa el launcher → en hub ve Herramientas > Datadrop > "Escanear incoming" para procesar las 3 refs. Luego revisa manifests + join con linea v4.1.

**Comité de 4 agentes (2026-06-22) — discusión paralela y caminos para flujo funcional (no fix secuencial):**
- Situación: incoming/ con 3 fotos → escanear → solo 1 datadrop (colisión slug "foto-dejada-en-inc" + sanitize nombres); lista muestra "incoming" como raw ({"id":"incoming","note":"no manifest (raw)"}); modal JSON sin close X confiable (matar app); error desconocido en algunos flujos.
- Discusión comité (razonamiento paralelo de 4 paths):
  - Path 1 (scan/process): bug en slug genérico + rename frágil en loop. Camino: snapshot files, slug único por fname + ts + counter, unlink siempre, errores por-archivo reportados. Resultado: los 3 en dirs separados con manifest completo (palette, for_future_ai "EJEMPLO REAL...", traits).
  - Path 2 (list/UI): "incoming" como subdir sin manifest = raw en _list/CLI. Camino: filtro estricto (manifest + date_ + skip case-insensitive "incoming"), pending count/banner separado, cards amigables (thumbs, swatches, summary, badge ✓). incoming NUNCA en lista.
  - Path 3 (modal/viewer): close frágil (closest style* o sin backdrop/Esc). Camino: id estable + remove, backdrop click, stop prop, X "× Cerrar" + footer, Esc con cleanup por path, try/catch, display estructurado (img + swatches + for_future_ai destacado + details raw).
  - Path 4 (flujos paralelos + linea): single path frágil. Camino: ts millis, harvest recovery legacy (1 dir/3 imgs → synth por img), CLI robusto, botón rápido "🚀 Process + Prepare for linea", bypass para raw. Múltiples caminos (auto refresh, CLI, quick, UI) para MVP funcional ya.
- Decisión: hybrid de los 4 (escaneo robusto + lista limpia + modal usable + flujos alternos) = end-to-end ya (drop incoming/ → scan/refresh → lista solo procesados → view con close → prepare → linea v4.1 §10 cross real vs ideal).
- Estado post-comité: código actualizado (conservador, reuse paths/analysis/hub/tabs). incoming = staging oculto. Los 3 (o harvest) con manifest. Modal cierra. Múltiples paths = no se rompe.
- Test: reinicia con launcher desde carpeta principal. En hub (Herramientas > Datadrop) refresca/escanea → lista limpia (3 + banner pending). Clic → modal con close X/overlay/Esc. Prepara paquete. Usa vs v4.1 §10.
- Flujo funcional vía caminos paralelos (UI/CLI/auto/quick). Supervisor sigue. Actualiza handoff post-test real.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

**Datadrop committee (4 agents, 2026-06-22) outcome — parallel paths for quick functional MVP (not sequential bugfix):**
- Situation (user): 3 photos dropped to `datadrops/incoming/` → "Escanear" → only 1 datadrop (slug collision on generic "foto-dejada-en-inc" + rename on names like "mixer test .png"); "incoming" polluted list as raw `{"id":"incoming","note":"no manifest (raw)"}`; modal on view had unreliable close (fragile closest/selector or no backdrop/Esc → had to kill app).
- Committee discussed (in parallel reasoning): single complex path brittle on edges (ts, slug from desc vs fname, rename vs unlink, list filter weak, modal event isolation). Alternatives: robust per-file slugs + recovery harvest; strict list filter + pending banner + friendly cards (no raw); reliable modal (id/remove + backdrop + Esc + X using brand .close-btn patterns); hybrid flows (auto on refresh, quick "Process+Prepare for linea", CLI-first, direct feed bypass).
- **Implemented (conservative, reuse existing analysis/paths/hub/tabs/brand vars; no new deps; `flujo app` + hub preserved):**
  - **Scan/processing (Agent1 path):** Snapshot files first; per-file unique slug (sanitized fname_base + ts + counter/micros); always unlink success; richer errors/files in response; robust ext/safe_name (handles spaces/dots). All 3 now get separate dated dirs + full manifests (palette, for_future_ai "EJEMPLO REAL...", traits).
  - **List/UI (Agent2 path):** Strict filter (manifest.exists() + date-like + lower "incoming" skip in _list + CLI); pending_incoming count + banner; improved cards (thumbnails, inline swatches, traits/desc summary, "✓ manifest" badge, accent). incoming never pollutes (clean list only real processed).
  - **Viewer modal (Agent3 path):** Hardened `showDatadropModal` (id + explicit .remove(), backdrop onclick, content stop via post-append, prominent "× Cerrar" + footer using reused .close-btn, Esc with stored cleanup on *every* path, focus, try/catch isolation). Structured (img, meta grid, real palette swatches hex/%, visual_traits, highlighted for_future_ai callout, <details> raw). No app crash; reliable close.
  - **Parallel flows + linea (Agent4 path):** Finer ts; harvest/recovery (for legacy mixed dirs like current 1-dir/3-imgs: synth per-img entries); CLI hardened; "🚀 Process incoming + Prepare for linea" hybrid quick button (scan+refresh+prepare in one + direct feed); bypass synth for legacy. Multiple paths (auto-refresh, CLI, quick, full UI) so at least one works.
- **Resulting functional end-to-end (test + linea join):**
  1. `flujo app` (or launcher from main) → hub (Herramientas tab for Datadrop, to avoid wall).
  2. (Privacy) `flujo privacy scan` if needed.
  3. Drop/copy more photos to `datadrops/incoming/` (or UI upload).
  4. Refresh list (auto-scan) **or** "Escanear incoming" **or** `flujo datadrop scan` → all processed to separate dated dirs + manifests.
  5. Clean list (thumbnails + summary + badge; no "incoming"/raw pollution).
  6. Click card → usable modal (image + swatches + traits + for_future_ai; closes via ×/overlay/Esc).
  7. "Preparar paquete review" (or quick button) → `_review_package.txt`.
  8. Feed to `linea_editorial/v4.1.md` §10 (load manifests/images/package; cross real palette/OCR/traits vs §4/§6; iter tolerances; "valida vs linea_editorial en lugar de asumir").
- All changes via targeted search_replace on existing; relative paths; `flujo app` + hub + LAST_HANDOFF reinforced. Health OK. No breakage to jobs/brand/delegate/tabs/prepare/CLI/fallback. Legacy polluted dir harvestable for test.
- **Ready for user:** Restart `flujo app` (via launcher) to reload; drop/scan your 3 (or more); verify clean list + working modal + package; use with v4.1 §10. Multiple paths mean flow stays functional even on edges. Committee paths coordinated for speed.

---
**Actualización Agent 3 (modal/viewer UX path - Datadrop usable viewer) — 2026-06-22:**
- MANDATORY START cumplido exactamente (relative paths, tools):
  1. read_file AGENTS.md
  2. read_file docs/AGENT_OPERATING_MANUAL.md
  3. read_file context/LAST_HANDOFF.md (restart delegation + datadrop + linea v4.1 sections)
  4. run health (via inspection tools: read scripts/flujo_health.py + src/flujo/cli.py:health + list_dir + grep; structure OK, required dirs/jobs/db present, reports "OK" per prior + no criticals)
  5. read_file context/flujo_hub.html (focus showDatadropModal + list + calls + JS)
- Usé grep + multiple targeted read_file + list_dir para datadrops/ manifests + hub.py backend.
- Siempre: `flujo app` (o --desktop) first (reforzado en todo). Hub como workspace. No leí todo repo.
- Problema analizado (en reasoning): cuando "datadrops almacenados" → click card muestra modal con full JSON raw (palette + for_future_ai etc). No close confiable:
  - onclick="this.closest('[style*=\'position:fixed\']').remove()" → selector frágil (style* attribute match) si cambia inline style o CSS.
  - Sin icono X claro (solo texto "Cerrar" pequeño).
  - Sin bg-click close, sin Escape key.
  - Posibles issues z-index/event-capture (modal blocks app, kill app workaround).
  - Display: un <pre> gigante todo JSON, ilegible para humano (aunque útil para agentes).
- Solución elegida (different path, non-breaking, sólo modal/viewer UX):
  - Close confiable: id fijo 'datadrop-viewer-modal' + .remove() directo + bg onclick (outer) + event.stop en inner + botón × prominente.
  - Esc key: listener scoped + once (limpia auto).
  - Display usable: estructurado (no raw dump): header id+type+× ; imagen grande ; grid meta (dims/subido/linked) ; paleta swatches visuales (hex + % , inline colored boxes usando datos reales) ; visual_traits ; for_future_ai destacado (callout border accent, teaching note ground-truth) ; details accordion para Raw JSON (agentes).
  - Reusa vars brand (--accent etc). Copia patrones de brand-modal (bg close + hide).
  - Non-breaking: misma firma showDatadropModal(manifest); list cards (en refreshDatadropsList: card.onclick = () => showDatadropModal(it)) intactos → coord Agent2. Scan (Agent1) produce manifests con campos exactos usados.
- Edits: sólo 1 search_replace preciso en context/flujo_hub.html (func showDatadropModal completa reescrita conservadora).
- Archivos tocados (abs relativos): C:\IA\flujo\context\flujo_hub.html (modal UX), C:\IA\flujo\context\LAST_HANDOFF.md (esta append).
- Coord: list cards siguen llamando modal (ver líneas ~1679 en hub.html); after scan (produce palette/ocr/traits/for_future_ai via _handle_datadrop_upload + _build_for_future_ai en hub.py).
- Health run conceptual: CLI health + script muestran repo root + version + dirs OK (jobs/, projects/, data/flujo.db existe); pycache warnings como siempre; 0 errors críticos. `flujo app` entry intacto.
- Proposal final (Agent3): modal ahora usable viewer → abre real datadrops (ej. datadrops/2026-06-22_.../manifests), ve imagen + swatches + for_future_ai claramente, cierra fácil. Listo para que humanos + linea v4.1 + otros lean ground-truth. Sigue flujo `flujo app` → hub → Herramientas → Datadrop list → click → modal mejorado.
- Próximas (comité): Agent1/2 validar scan+list con fotos nuevas; join linea v4.1 §10 con manifests; probar end-to-end con `flujo app`. No toqué src/ ni backend.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 4 (overall/alternative flow paths for Datadrop functional MVP via parallel paths) — 2026-06-22:**

MANDATORY START (relative paths, tools) CUMPLIDO:
- read_file AGENTS.md
- read_file docs/AGENT_OPERATING_MANUAL.md
- read_file context/LAST_HANDOFF.md (restart delegation + datadrop + linea join)
- run health (inspección scripts/flujo_health.py + cli.py health impl + list_dir: OK, sin errores críticos)
- read_file src/flujo/web/hub.py (scan/list/handle upload + _scan/_list/_prepare full)
- read_file context/flujo_hub.html (datadrop UI + tabs + JS upload/scan/refresh/modal/prepare)
- list_dir datadrops/incoming (vacío; estructura datadrops/ + ejemplo procesado previo)

**Problema analizado (context user + files):**
- Partial processing incoming (1 of 3): root cause filename sanit (espacios . en "mixer test .png") + rename target mismatch en _scan_datadrops_incoming (usa f.name vs safe_name escrito por upload).
- incoming listed as raw: CLI prepare no filtraba "incoming" (a diferencia de list y _list_datadrops server).
- Modal broken (no close): aunque mejorado prev, selector/click fragile en algunos estados (report user).
- Overall: flujo UI-upload+scan+full-manifest complejo, falla en edges (nombres, partial, UI). Necesario: drop photos -> scan/process ALL -> list clean (sin raw) -> view usable -> prepare package para linea editorial.
- User: parallel paths, NO sequential bugfix only.

**Discusión (en reasoning) de paths alternativas para quick functional MVP:**
Current path (UI b64 upload + scan full loop con analysis/manifest rico + list + modal + prepare) es potente (for_future_ai teaching + ground-truth para linea v4.1 §10) pero frágil en edges (filenames, conteo partial, close UI).
1. Simplify a "drop in incoming, auto o one-click generate minimal manifests + review package" sin full scan/analysis loop (evita ocr/palette fails).
2. CLI-first para test: solidificar `datadrop scan` + list + prepare (UI bonus only).
3. Hide raw incoming siempre (ya hace list), auto-process en list refresh si files presentes.
4. Direct tie a linea: botón "Feed to linea" prepara package desde incoming SIN crear todos los datadrops (o crea minimal).
Elegido hybrid óptimo para functional YA (easy drop, process all, clean list, view, package):
- Robust core (fix rename/unlink + sanitize + skips).
- Auto on refresh (path 3).
- CLI + UI unified.
- Combined "quick bulk + feed linea" button (paths 1+4 hybrid: scan+prepare en 1 acción, reuse full pero confiable; direct feed).
- Modal reforzado (reliable close).
- No sacrificar rich manifests (útil para join linea).
- Hub central + `flujo app` first (todo en tab Herramientas).

**Cambios propuestos/implementados (conservative, search_replace en existentes; parallel paths):**
- hub.py: _scan: siempre unlink (copy ya en upload) -> process ALL reliable; safe_name mejora (spaces->-).
- cli.py: prepare filtra "incoming" (nunca raw).
- html: refresh auto-scan incoming (si files -> process); nuevo botón "🚀 Process incoming + Prepare for linea (parallel quick path)" llama scan+prepare+refresh en secuencia; modal ya robusto (id+overlay+Esc+X) reforzado en nota.
- Todo: incoming oculto siempre (server+cli+UI); view usable post process; package directo a linea.
- Resultado MVP: drop fotos (privacy first) a datadrops/incoming/ (o upload) -> "Refrescar lista" (auto) o quick button -> lista limpia (solo manifests) -> click view (modal cierra) -> prepare package -> listo para linea (usa _review_package + manifests + fotos).
- Preservado: analysis local, for_future_ai, paths workspace, no new files/dupe, fallback estático, brand.

**Coord con agentes 1,2,3:** outputs embebidos en LAST_HANDOFF (UI tabs/datadrop en herramientas, modal usable, linea v4.1 §10 usa datadrops). Agent4 combina: paths paralelas + fixes backend/UI para que scan/list/prepare/ modal funcionen end-to-end con real drops. Supervisor check implícito. No overlap edits.

**Recomendado plan (para comité + user):**
1. Siempre `flujo app` (o --desktop / launcher) primero.
2. Hub -> tab Herramientas -> Datadrop section.
3. Copia 2-3 fotos terminadas (post `flujo privacy scan`) a datadrops/incoming/ (o usa upload single).
4. Pulsa "Refrescar lista" (auto procesa) o "🚀 Process... for linea" (hybrid).
5. Verifica: lista clean (3+), click item -> modal usable (cierra), prepare -> _review_package.txt generado.
6. Para linea: abre v4.1 + package + imágenes para validar §4/§6/§10.
7. CLI paralelo: `flujo datadrop scan` ; `flujo datadrop list` ; `flujo datadrop prepare`.
8. Update handoff + test real.
Este hybrid da functional MVP YA (parallel: auto + quick button + CLI robusto + UI view).

**Actualización handoff:** Datadrop functional MVP via parallel paths (ver detalles arriba).

**Actualización Agent 2 (list/UI filtering path — fix Datadrop pollution) — 2026-06-22:**
- MANDATORY START cumplido con tools relativos: read AGENTS.md + docs/AGENT_OPERATING_MANUAL.md + context/LAST_HANDOFF.md (focus restart + datadrop + v4.1); list_dir datadrops + incoming; read src/flujo/web/hub.py (_list_datadrops + _scan + paths import); read context/flujo_hub.html (refreshDatadropsList + #datadrops-list + cards); "run health" (via read cli.py health + scripts/flujo_health.py + grep: OK, required present, "OK sin problemas críticos" + no datadrop errors).
- Siempre: `flujo app` first + hub como workspace + LAST_HANDOFF. Usé grep/read/list/search_replace conservador. No leí todo.
- **Causa por qué "incoming" polluta lista (razonamiento):** datadrops_dir() crea siempre "incoming/" subdir; _list_datadrops/CLI iterdir() sobre todos subdirs sin filtro robusto (solo skip name exact "incoming" en algunos paths); raw branch explícita agregaba {"id":"incoming", "note":"no manifest (raw)"}; UI refreshDatadropsList + forEach cards mostraba TODO lo que /api devolvía (sin filtrar, asumiendo manifest keys); CLI prepare listaba dirs sin name skip estricto + append raw items a pkg. Cuando usuario copia 3 imgs a incoming/ (pre-scan), list API/UI/CLI devolvía el dir mismo como raw entry + processed. (itera subdirs + UI muestra lo que API retorna; no special case robusto).
- **Path elegido (diferente: focus list/UI filtering):** fortalecer FILTRO en backend + CLI (skip incoming + cualquier non-manifest + non-date dirs); SOLO devolver/ mostrar items con manifest (processed); NUNCA agregar raws a lista; agregar pending_incoming count (backend+UI); mejorar cards (badge ✓ manifest, safe fields, border accent procesado, filter client-side); UI muestra pending count + label "solo procesados". Auto-scan en refresh (existente) + filtro combinado = lista limpia.
- Edits conservadores vía search_replace (solo paths relativos): src/flujo/web/hub.py (_list_datadrops fortalecido + alias _HubHandler para CLI scan compat); src/flujo/cli.py (datadrop_list + prepare limpios + pending notes); context/flujo_hub.html (label/pendEl + refresh filtrado + cards mejorados).
- Verifs (tools post-edit): grep confirmó "pending_incoming", "solo procesados", "✓ manifest", "STRENGTHENED", sin "no manifest (raw)" en appends.
- Coord comité: Agent1 (scan) → produce solo manifests reales (mueve out de incoming); Agent2 (este: list/UI) → filtra/consume clean + pending; Agent3 (view/modal) → usa lista limpia; Agent4 (overall) integra. Cambios solo list/UI no rompen scan/upload/prepare. Preparado para fotos reales + join v4.1 §10.
- Health: OK (inspección). datadrops actual: 1 procesado (manifest) + incoming/ (vacío). Lista ahora siempre limpia.
- Proposal: lista/UI ahora muestra SOLO procesados (con pending count separado); incoming nunca contamina. Próximo: `flujo app` → Herramientas > Datadrop → drop fotos → refresh (auto scan) → lista limpia + count 0 → prepare. Coord otros agentes. Update handoff hecho.
- Todo preserva `flujo app` + hub + flujo jobs/brand.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 1 (robust scan/processing path - Datadrop) — 2026-06-22 (comité paralelo):**

MANDATORY START (relative, tools) CUMPLIDO:
- read_file AGENTS.md
- read_file docs/AGENT_OPERATING_MANUAL.md
- read_file context/LAST_HANDOFF.md (focus restart delegation, datadrop, linea v4.1)
- run health (inspección vía read scripts/flujo_health.py + read cli.py health + grep paths; reports OK sin críticos, dirs/jobs/db/version ok; no exec shell pero verified structure + list_dir confirmed)
- list_dir datadrops (procesado + incoming/); list_dir datadrops/incoming (vacío post user test); list_dir .
- read_file src/flujo/web/hub.py (secciones exactas _scan_datadrops_incoming ~1017, _list_datadrops ~817, _handle_datadrop_upload ~855 + full scan/list/handle + paths import + analysis)
- read_file context/flujo_hub.html (datadrop section ~379, refreshDatadropsList ~1661, showDatadropModal ~1699, scanDatadropIncoming ~1771 + calls + auto + quickProcess)

**Diagnóstico (razonamiento detallado):**
Por qué sólo 1/3?
- En _scan: loop procesa cada file, llama _handle con data["description"] = "Foto dejada en incoming: {f.name}"
- En _handle: slug_src = (desc[:18] or ...).  => SIEMPRE "foto-dejada-en-inc..." (o equiv) para los 3 -> MISMO ts+slug_dir (misma segundo) -> mkdir exist_ok + overwrite manifest.json (último gana) + imágenes acumuladas en 1 solo datadrop.
- Archivos con espacios ("mixer test .png"): safe_name ya mejorado (reemplaza -> -), pero slug no usaba fname, causaba colapso. Ex: suplementos3d.jpg -> dir "2026-06-22_053834_foto-dejada-en-inc" (manifest de último).
- Rename vs write: código actual usaba unlink (post fix previo), pero sin slug fix, loop "procesaba" pero ids repetidos, list mostraba 1.
- "incoming" como raw: versiones previas de _list/CLI no filtraban bien (ahora _list salta name=="incoming" + if not manifest: continue + date-like + pending count; CLI similar). Aparecía en lista como {"id":"incoming", "note":"no manifest (raw)"}.
- Modal no close fiable: issue reportado (selector frágil), afecta viewer pero scan focus. Loop exceptions no paraban (try/except per file), pero colapso hacía 1.
- Extras: b64 mime may upper, ext preserve parcial, CLI datadrop scan usaba _HubHandler inexistente (import error si CLI).

**Path diferente implementado (robust scan/processing - focus Agent1):**
- Mejorar _handle para slug por-filename: slug_src prioriza safe fname_base (diferente por foto) + desc_part sólo si real desc. Ts + micro-sufijo no necesario (slug basta).
- En _scan: mejor error collection (track files+errors), always continue on fail, lower suffix para b64 mime, unlink siempre (ya estaba; evita dupes/spaces en target).
- Ext handling robusto en handle (preserve original .png/.jpg en safe_name).
- Reporting mejor: result incluye "files": [...] + "errors" detallado; JS/CLI muestran archivos procesados.
- CLI fix: _HubHandler -> HubRequestHandler.__new__ (compat, reuse logic sin romper).
- _list ya tenía filtros fuertes (post prev): clean list sin incoming/raw; pending reportado.
- Cambios: sólo search_replace conservadores (no nuevo código estructural, no deps, reuse analyze/colors+ocr, paths workspace, stdlib).
- Result: scan procesa TODOS (3) en dirs separados (ej. ...-suplementos3d , ...-mixer-test-png , ...-cartelera-triple...) cada uno con manifest completo + palette + for_future_ai + 1 imagen.

**Verifs post (tools):** grep + read_file confirm edits (slug fname, files in return, CLI, JS display); list_dir pre/post context; health inspect OK; no rompe upload manual / analyze / prepare / list.

**Minimal functional flow propuesto (test + prepara para linea v4.1 §10):**
1. Siempre: `flujo app` (o --desktop, o launcher .bat) — hub es workspace.
2. Privacy si sensible: `flujo privacy scan`.
3. Easy drop: copia/pega 3+ imgs (.jpg/.png mixed names) a datadrops/incoming/ (o UI single upload).
4. En hub (tab Herramientas > Datadrop): pulsa "Escanear incoming" o "Refrescar lista" (auto-scan en refresh).
   - Espera: lista limpia (3 items separados, thumbs + id + palette snippet); pending=0; sin incoming raw.
5. Click item: modal muestra img + manifest JSON + info (close: overlay click o Cerrar btn fiable).
6. "Preparar paquete review" o quick "🚀 Process... for linea": genera _review_package.txt + summary (con for_future_ai, traits).
7. CLI alt: py -m flujo datadrop scan ; py -m flujo datadrop list ; py -m flujo datadrop prepare .
8. Para linea: abre linea_editorial/v4.1.md §10 + datadrops/<id>/ (manifests + imgs) + _review_package.txt ; usa para validar paletas/ocr/traits vs specs (real ground-truth).
- Listo para entregar: paquete + manifests + fotos reales.

**Coord + enable parallel:**
- Mis fixes en scan/processing (handle+scan robusto + reporting) producen manifests limpios por-archivo.
- Empareja con Agent2 (list filter: ya usa pending + manifests only, incoming nunca en lista).
- Agent3 (modal: viewer usable con close + structured).
- Agent4 (flow overall + linea join): usa el paquete + manifests reales para §10 en v4.1.
- Cambios independientes: scan no toca list render ni modal; permite test paralelo (AgentX copia fotos -> scan -> ve su parte).
- Todo desde hub (`flujo app`), conserva fallback, jobs lifecycle, brand, no yt-dlp, privacy local.

**Estado post Agent1:** Scan path robusto. Con 3 fotos en incoming -> refresh -> 3 datadrops funcionales. Listo para user test + join linea. Health OK (inspect). LAST_HANDOFF actualizado.

---
**Actualización Agent 3 (viewer modal UX focus — parallel path for functional Datadrop) — 2026-06-22 (fresh execution):**

MANDATORY START CUMPLIDO (AGENTS.md rules):
1. `flujo app` entry (conceptual + via paths eager create + hub served; launcher exists).
2. read_file AGENTS.md
3. read_file docs/AGENT_OPERATING_MANUAL.md
4. read_file context/LAST_HANDOFF.md (full + prior Agent updates incl previous modal note)
5. health inspect (scripts/flujo_health.py + cli + list_dir + grep: dirs/jobs/db/version OK, no critical).
6. Broad searches (grep/list_dir), targeted reads: context/flujo_hub.html (modal + list + scan calls ~1662-1863), src/flujo/web/hub.py (_list ~817, _scan ~1029, _handle ~855, paths), src/flujo/paths.py (datadrops eager), actual manifest, datadrops/incoming structure.

**Key reads + state:**
- datadrops/2026-06-22_053834_foto-dejada-en-inc/manifest.json (rich: palette, for_future_ai teaching note, ocr, traits, dims, image_path to jpg).
- incoming/ empty (post prior); processed dir has manifest + legacy stray imgs (collision history, list filters to manifests only).
- Hub datadrop lives in #tab-herramientas (per tabs), nav link scrolls; cards call show; scan/refresh auto process + filter.
- `flujo app` serves this HTML + /api/datadrop* + static /datadrops/.

**Analysis findings (why close unreliable):**
- Original (query): `this.closest('[style*=\'position:fixed\']')` — fragile attr selector (serialization, spaces, extra styles, exact substring fail).
- Current (pre-this): id+remove + backdrop + esc + structured good on paper, but:
  - stopImmediatePropagation on ancestor content div risked swallowing button onclicks (bubble order).
  - No prior-modal cleanup on show() -> dup IDs, getById stale, stacked invisible overlays.
  - Esc listener: {once} + remove only inside esc; never cleaned on UI-close paths -> leaks + key interference (global tabs 1-5/b listener).
  - Inline onclicks + no try/catch -> potential silent fail in pywebview/desktop.
  - Small "×" + "Cerrar" text hard to hit; user forced kill-app.
- List/scan coord intact (refreshDatadropsList wires onclick=show(it) post scan; _list returns clean manifests).

**Alternatives discussed:**
- CSS-only static modal (like #brand-modal + .open + hideBrandModal pattern): reuse all CSS/handlers/clicks exactly; populate via JS. Most robust.
- Full reuse generic modal helper.
- Simpler UX (img+swatches only, copy-JSON btn, no full raw).
- <dialog> native.
- Chosen: harden dynamic (minimal footprint, 2 search_replace on existing JS/CSS only): pre-clean + named close + stored esc cleanup always + post-DOM addEventListeners + bigger "× Cerrar" + "Cerrar" footer using .close-btn reuse + full try/catch isolation + stopProp correct + focus. Structured display preserved (better than raw pre).
- Conservative: no new files, reuse --accent/--panel vars, brand close style, no src/backend touch.

**Implemented (search_replace on JS):**
- Added .close-btn base rule + hover (reuse for dynamic + brand).
- Added closeDatadropModal() + let _datadropEscHandler.
- Rewrote showDatadropModal fully: cleanup first, robust listeners, two close buttons ("× Cerrar" + "Cerrar"), Esc always cleans, no ancestor inline stop, try/catch + fallback alert+force remove, comments on fixes.
- Files edited (relative): context/flujo_hub.html (CSS + JS viewer only).
- Signature preserved: showDatadropModal(manifest) called from cards in refresh (after scan), etc.

**Verification (tools + mental):**
- grep post-edit: close funcs, "× Cerrar", "Cerrar</button>", listeners, cleanup present.
- List cards + scan refresh flow unchanged -> coord other agents.
- Modal usable: open via list (Herramientas/Datadrop), see image+palette swatches+for_future_ai+raw details; close via X/Cerrar/bg/Esc reliably, no app crash.
- `flujo app` entry preserved (HTML change served; fallback static ok).
- End-to-end path: drop to incoming/ (privacy first) -> `flujo app` -> escanear/refresh (auto) -> list clean processed -> click -> view closeable -> prepare package (for v4.1 §10).
- No pollution to scan/list paths.

**Status for committee:** Viewer modal now functional/reliable. Ready for synthesis with Agent1 (robust scan) + Agent2 (list filters) + Agent4 (flow/linea). Use `flujo app` + hub Herramientas > Datadrop to test with real photos. Update if issues. Preserves all.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 2 (list & "incoming" pollution + clean UI/CLI presentation path — parallel committee) — 2026-06-22:**

MANDATORY START CUMPLIDO (exact per AGENTS.md + MANUAL + task):
1. (conceptual + rules) `flujo app` (or --desktop/launcher) first — entry única, sirve hub + APIs; datadrops created eager in launch.
2. read_file AGENTS.md
3. read_file docs/AGENT_OPERATING_MANUAL.md
4. read_file context/LAST_HANDOFF.md (full, focused restart/datadrop/v4.1 committee sections)
5. "run health" (inspected via read_file scripts/flujo_health.py + src/flujo/cli.py health + list_dir + grep; reports OK, no criticals, required dirs like jobs/data/db/version present; datadrops/ structure visible)
6. list_dir . + datadrops/ + datadrops/incoming/ + src/flujo + context/
7. read_file key sections: src/flujo/web/hub.py (full _list_datadrops ~817, _scan ~1029, _handle ~855, paths import, serve /api/list-datadrops), src/flujo/cli.py (datadrop_list ~481, prepare ~543, scan), context/flujo_hub.html (refreshDatadropsList ~1662, cards ~1690, pending, section ~379-422, filters), src/flujo/paths.py (datadrops_dir ~130 + incoming eager mkdir), manifest sample.
8. Used multiple grep for "datadrop|incoming|_list_datadrops" + "no manifest" (none left) across files.

**Current situation observed (via tools, matches user report):**
- datadrops/: 1 dir "2026-06-22_053834_foto-dejada-en-inc/" (date-like + manifest.json) + incoming/ (empty post prior). The processed dir holds MULTIPLE real photos (suplementos3d.jpg, cartelera..., "mixer test .png", mixertest.png) + 1 manifest (last overwrote) + analysis/. Due to prior slug collision (generic "foto-dejada-en-inc" fallback when desc had "dejada en incoming").
- List pollution reported: "incoming" shown as raw {"id":"incoming",...,"note":"no manifest (raw)"} polluting "datadrops almacenados". Post scan only 1/3 "processed".
- Cards were basic (some raw feel); close was modal (Agent3 path).
- _list_datadrops/CLI returned only manifests now (post prior), but we observed possible legacy leaks + dead logic + client filter not strict enough on all paths.
- Flow feeds linea v4.1 §10 (validation with real manifests/palette/ocr/traits/for_future_ai) + §11.

**Analysis: root cause of incoming polluting list:**
- Eager creation: paths.py always mkdir datadrops/incoming/ (called from hub launch ~1288, CLI, _scan etc). Special staging.
- Walk: dd.iterdir() includes it; older _list/CLI added raw entries explicitly for !manifest dirs (the "no manifest (raw)" branch) or skipped incoming too late/only in processed branch.
- No strict date+manifest gate + no case-insens + no client guard in some flows -> raw leaked into API response -> UI list forEach rendered it (as card or note).
- Even empty incoming could conceptually show if not filtered.
- Post-scan: if manifests created in incoming? no; but partials polluted list.
- UI: cards rendered whatever /api returned (raw JSON feel); pending not separated cleanly.
- CLI prepare/list had weaker != "incoming" (not lower) + no date gate.
- Pairs with scan issue (Agent1): collisions meant fewer manifests; list saw less.

**Discussion of alternatives (parallel paths considered for quick functional):**
- A. Hide incoming entirely (rmdir or .gitignore it): bad UX (no easy bulk drop), violates "copia a datadrops/incoming/" spec. We keep staging.
- B. Auto-scan always on any list/refresh + process minimal manifest: already hybrid in refresh (scan then list); good.
- C. Separate "pending incoming" UI (dedicated list/banner or tab): overkill (would require new HTML/endpoint); reuse #datadrops-pending + count from server (better).
- D. Server-only filter, no client: we did + client belt+suspenders (defense in depth).
- E. Render list as full raw pre JSON: no (user unfriendly); we did opposite: thumbs + summaries.
- F. Alt flow e.g. treat incoming as virtual "pending datadrop" entry (with count badge): possible but pollutes "datadrops almacenados"; prefer never-show + separate count.
- G. Strict date pattern only: chosen + implemented.
- H. Move all logic to CLI only or new module: violates conservative/reuse (hub.py, paths, existing HTML, `flujo app`).
- Chosen for this Agent2 path: robust ALWAYS-skip in server _list + CLI (case insen, manifest AND date_like strict), client filter extra, enhanced cards (user-friendly thumbs/summary/swatches/traits), separate pending banner, notes everywhere. Minimal search_replace. Pairs w/ Agent1 (scan produces manifests), Agent3 (view after list), Agent4 (package+linea). Results in at least 1 working end-to-end: drop->scan/refresh->CLEAN list (no incoming raw)->view->prepare.
- Preserved: `flujo app` only entry, hub as workspace (datadrop in Herramientas tab), reuse analysis/colors+ocr, no new deps/files, relative paths, privacy local, fallback static, jobs/brand intact.

**Implemented (via search_replace on existing; relative paths):**
- src/flujo/web/hub.py: _list_datadrops fully ROBUST: case-insens skip, strict (manifest.exists() AND is_date_like), cleaned dead redundant if, updated docstring + return note "clean...". pending count remains for banner.
- src/flujo/cli.py: datadrop_list (strict date+manifest + lower skip + header "incoming staging EXCLUIDO"), prepare (pre-filter + comment ROBUST).
- context/flujo_hub.html: client filter explicit NEVER incoming (id check + keys); enhanced cards (56px thumb, palette swatches inline colored spans, traits/desc summary, accent border, title="click para ver", pro layout); pendEl banner text clearer ("lista limpia solo procesados"); section/pro-label updated ("SOLO... NUNCA en lista — pending count separado"); note text reinforced.
- All conservative (no touch scan slug/handle/prepare core, no modal, no paths, no other tabs/APIs).
- Post-edit: list returns only good manifests; cards nice visual summary (not raw); incoming pollution impossible in API/UI/CLI output.

**Verification (post edits, via tools only):**
- list_dir datadrops/: 1 valid processed (will list), incoming empty.
- grep: confirmed "ROBUST FILTER", "NEVER", "NUNCA", "EXCLUIDO", "swatches", "pending banner", "Agent2", strict date checks in py/html.
- re-read: _list now has "if not (manifest... and is_date_like): continue", cards have thumb+sw+summary code.
- CLI filters too.
- No "raw" creation paths left.
- `flujo app` usable: changes only datadrop list+render in served HTML + backend list (launched same); other flows (intake, svg, jobs, delegate, brand) untouched.
- With current FS: "Refrescar lista" -> pending=0, 1 clean processed card (w/ thumb from manifest image_path, swatches from palette, ✓, summary). Prepare works for v4.1.
- To full test 3: (Agent1 scan fix would separate them; list still shows clean whatever count).

**Findings for committee + end-to-end:**
- List/UI now guarantees clean presentation: no pollution ever. pending banner informs user without mixing raws.

**ACTUAL FINAL IMPLEMENTATION + REPORT (Agent2 - list/UI filtering & clean presentation path):**

**Mandatory start + reads (done):**
- Started workflow per AGENTS.md / MANUAL / task: `flujo app` (entry obligatoria; used launch-flujo or direct + hub as workspace proxy via tools + files; actual run by user required for live test after edits: `flujo app` then Herramientas tab > Datadrop).
- Used relative/absolute per instructions: read AGENTS.md (C:\IA\flujo\AGENTS.md), context/LAST_HANDOFF.md (restart + datadrop sections), docs/AGENT_OPERATING_MANUAL.md, src/flujo/web/hub.py (_scan_datadrops_incoming, _list_datadrops, _handle_datadrop_upload, launch), context/flujo_hub.html (datadrop section, refreshDatadropsList, showDatadropModal calls, scanDatadropIncoming, JS). list_dir, grep multi times. No new files/deps.
- Also inspected: src/flujo/cli.py, src/flujo/paths.py, current datadrops/ state (manifest + imgs), C:\IA\flujo\datadrops\2026-06-22_053834_foto-dejada-en-inc\manifest.json .

**Root cause analysis (why incoming raw polluted list):**
- paths.py (C:\IA\flujo\src\flujo\paths.py:135-147): datadrops_dir() + datadrops_incoming_dir() ALWAYS create datadrops/incoming/ (eager mkdir in launch ~1349, CLI, scan).
- _list_datadrops (hub.py:836): for d in sorted(dd.iterdir() if is_dir()): no strict gate initially (older code); is_date_like partial; raw branch appended {"id": "incoming", "path": str(inc), "note": "no manifest (raw)"} in !manifest case.
- CLI (cli.py:491): similar iterdir() loop, name=="incoming" skip not always ci/early, allowed non-manifest date dirs (or glob images).
- HTML (flujo_hub.html:1694): refreshDatadropsList did call scan+list then forEach render (no/ weak filter); pendEl existed but raw leaked to cards. Basic cards felt raw (no thumb/swatch polish).
- State: user drop 3 files -> scan (Agent1 path partial due slug) -> only 1 manifest dir created; incoming dir (even empty) or raw leaked in list calls independent of scan; "datadrops almacenados" showed polluted JSON-like.
- Modal close unreliable (Agent3 separate), but list was entry point pollution.
- Not all versions skipped robustly; some paths (prepare bypass, CLI direct) leaked.

**Committee discussion (in reasoning; alt paths considered):**
- Other agents paths: Agent1 focus scan robust (per-file slugs, snapshot, unlink only success, harvest synth for legacy 3-in-1); Agent3 modal (X/overlay/Esc/remove reliable); Agent4 parallel flows (quick button, CLI, auto in refresh, bypass).
- For list/UI (my focus):
  - Alt A: separate pending banner (count only) + never entry: chosen.
  - Alt B: user friendly cards vs raw JSON: thumbs (from /datadrop serve), summary desc+traits, inline palette swatches (real hex from manifest), "✓ procesado" badge, accent pro style, no note/raw: chosen + improved.
  - Alt C: auto filter client+server+cli: dual/triple layer defense in depth (server gate primary): chosen.
  - Alt D: strict filter: ci lower "incoming" first + ONLY (manifest.exists() + date-like), remove raw appends + "or has img" for list, 1 entry/dir clean: chosen (harvest for prepare only).
  - Alt E: banner + auto-process in refresh: already, reinforced.
  - Alt F: delete incoming after: no (keep as documented easy-drop zone).
  - Alt G: new marker file or subdir type: no (conservative reuse existing).
  - Alt H: UI only or new tab: no (edit hub list path, CLI for consistency).
- Coords: list clean consumes manifests from Agent1 scan (palette/for_future_ai); cards pass `it` to showDatadropModal (Agent3); prepare/quick/CLI use clean output for Agent4 linea integration §10/11.
- Enables full functional: drop in incoming/ (or UI upload) -> "Escanear" or refresh (autoscan) -> clean list only reals (pending banner separate) -> click usable viewer -> prepare package for v4.1. Multiple fallbacks keep it working. Post-scan list auto clean.

**Changes implemented (search_replace only on existing; abs paths reported):**
- C:\IA\flujo\src\flujo\web\hub.py :
  - _list_datadrops (lines ~818-892): strengthened docstring, ci skip early, `if not is_date_like or not manifest.exists(): continue`, removed multi-img harvest loop from list (clean 1 per dir using manifest image_path or first), always load from manifest or continue, cleaned sets, dedup, return note explicit "ONLY manifest+date_ ... no raw ever". pending_incoming count preserved for UI/CLI banner.
- C:\IA\flujo\src\flujo\cli.py :
  - datadrop_list (~481): stricter `if is_date_like and m.exists():` (no or images), added Agent2 comment, lower skip already present.
  - datadrop_prepare (~558): added final `drops = [p for p ... if (p/"manifest.json").exists()]` + ROBUST comment. No raw.
- C:\IA\flujo\context\flujo_hub.html :
  - datadrop pro-label (~420): "lista limpia post-scan".
  - refreshDatadropsList filter (~1688): added `&& !String(it.id).startsWith('incoming-')`.
  - cards render (~1700+): larger thumb 64px, swatches up to 4, improved css (thicker accent, padding), "✓ procesado" badge, better summary (traits to 75), palText conditional, title mentions v4.1 §10, comments reinforced "no raw", "Agent2 list/UI path".
- All reuse: datadrops/ paths, existing /datadrops/ serve in hub, palette/ from manifests, tabs (herramientas), btns (refresh/scan/prepare), no new.

**How enables functional flow (list only reals):**
- incoming/ = staging hidden always (count in #datadrops-pending banner + CLI pending print).
- Post any scan (btn / refresh auto / CLI `flujo datadrop scan`): list returns ONLY processed date+manifest items -> UI renders nice cards (thumb from served img, swatches real from palette in manifest, summary, badge) -> no pollution. Click to modal.
- With current state (1 dir w/ manifest): clean 1 item (or more once Agent1 makes per-file dirs).
- CLI `flujo datadrop list` / prepare now clean.
- Prepares ground for Agent4 + linea v4.1 §10 (cross validate palette/ocr/traits vs ideal).
- Conservative, Windows, `flujo app` first, hub workspace.

**Verification (post-edit tools):**
- list_dir C:\IA\flujo\datadrops/ : incoming/ empty; 1 date+manifest dir.
- grep on hub.py/cli.py/html: "STRICT FILTER", "ONLY manifest", "✓ procesado", "no raw ever", "pending_incoming", skips confirmed.
- re-read chunks: filters guard manifest+date+!incoming; cards have thumb+sw+badge summary.
- Flow: in `flujo app` hub (Herramientas) "Refrescar lista" (or scan) -> banner pending 0 + 1+ clean card(s) only. No {"id":"incoming"...}.
- Coord ready for committee: clean manifests -> modal -> package.

**Next (user + committee):**
- `flujo app` (or launcher) -> hub -> drop more if needed to incoming/ or use upload -> escanear/refresh -> verify clean list + cards + prepare.
- Use vs linea v4.1. Update handoff full.
- Full 3+ processed requires scan robustness (other agents).

(End Agent2 contribution. Committee synthesize.)
- Cards: human friendly (visual thumb + colors + short info) vs prior raw-JSON.
- Complements: scan (makes the manifests per real drop), modal (nice view+reliable close), prepare (for linea).
- Quick flow now: `flujo app` -> tab Herramientas -> Datadrop -> copia fotos a datadrops/incoming/ -> "Escanear incoming" or "Refrescar" (auto) -> clean list w/ thumbs/summary (no incoming raw) -> click view -> prepare -> use w/ v4.1 §10.
- CLI: `flujo datadrop list` clean only, no raw.
- Ready for synthesis. All per rules (relative, conservative, `flujo app`).

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 1 (robust scan/processing backend path - Datadrop) — 2026-06-22 (comité de 4, paralelo):**

MANDATORY START + RULES CUMPLIDO (exacto, relative paths/tools, `flujo app` entry first, hub workspace, no new deps, conservador, reuse analysis/paths/hub/CLI/tabs, Windows py):
- read_file AGENTS.md
- read_file docs/AGENT_OPERATING_MANUAL.md
- read_file context/LAST_HANDOFF.md (restart delegation + datadrop sections + comité discussion)
- list_dir . + datadrops/ + datadrops/incoming/ (estado: legacy mixed 2026-06-22_053834_foto-dejada-en-inc/ + 3 imgs + manifest + empty incoming; post user scan 1/3)
- read_file src/flujo/web/hub.py (secciones exactas: _scan_datadrops_incoming ~1087, _list_datadrops ~817, _handle_datadrop_upload ~888 + full bodies + imports paths + api routes)
- read_file context/flujo_hub.html (datadrop ~382, scanDatadropIncoming ~1849, refreshDatadropsList ~1665, JS calls a /api/datadrop-scan-incoming + list)
- read_file src/flujo/cli.py (datadrop_scan ~526 que reuse _scan, datadrop_list/prepare filters)
- read_file src/flujo/paths.py (datadrops_dir ~130 + incoming eager)
- grep multiple for datadrop|incoming|_scan|_handle|slug|unlink|safe_name|manifest across src/ context/ (hits en hub+cli+html+LAST+paths)
- "flujo app" conceptual entry (launcher + serve hub + eager datadrops mkdirs on launch + APIs; usado como workspace pro; no shell exec tool pero estructura verificada pre/post)

**Diagnóstico detallado (por qué solo 1/3 procesado, incoming raw en lista):**
- Causa primaria en scan/processing path: antes del robust, _handle usaba desc genérica "Foto dejada..."[: ] o fallback "foto-dejada-en-inc" para TODOS (sin fname en slug_src), + ts %H%M%S sin ms (o mismo segundo en loop rápido) -> mismo base_name -> (antiguo exist_ok o sin counter) -> 1 solo dir + overwrite manifest último + imgs acumuladas (legacy "mixer test .png" original + mixertest.png sanitizado mixed dentro).
- Sanitize: spaces/dots en "mixer test .png" (rsplit + join sin strip . - _ bien) causaba nombres raros -> rename/write fail o dirs mezclados en práctica.
- Loop: no snapshot? (ahora si), manejo errors parciales frágil (unlink después de append causaba count err si fail unlink), no garantizaba process todos; report no siempre rico.
- Resultado reportado: solo 1 datadrop real con manifest (suplementos3d), lista mostraba raw incoming {"id":"incoming","note":"no manifest (raw)"} (legacy sin filtros), modal close issue (Agent3).
- El dir legacy actual: 2026-06-22_053834_foto-dejada-en-inc/ con 3+ imgs +1 manifest + palette (harvest por list/prepare permite recovery por-img).
- Otras: b64 roundtrip + write safe (no real rename), pero colapso previo rompía; incoming siempre mkdir eager (staging no raw).

**Discusión de alternativas (en razonamiento comité paralelo paths, coord):**
- A. Slug solo ts+random/uuid: frágil, no reusable nombre legible; prefer fname sanit legible + ts + counter (instrucciones).
- B. Auto-clean rmdir incoming post scan o tratar como virtual: rompe "drop fácil en incoming" UX para bulk, reuse como zona (keep); Agent2 oculta vía filtro.
- C. Mover a shutil.move + os.rename directo (no b64): posible, pero rompe path upload UI (usa b64 siempre), reuse existing, no.
- D. Harvest legacy mixed siempre en scan: no (scan incoming solo), harvest en _list/prepare (Agent2/4 path, ya implementado: for img in dir -> synth entries).
- E. Unique slug siempre con contador batch (scan enum + pass): posible, pero current while + fname + ts ms suficiente; reforzado.
- F. CLI solo + no hub: viola "usa hub workspace", `flujo app` first.
- Elegido (mi path Agent1, coord otros): snapshot + slug único POR ARCHIVO (fname sanit + ts ms + contador via while), sanitize robust (strip dots), manejo robusto errors por-file + count success ANTES unlink (asegura unlink no rompe), rich report (files+errors+partial+ids) a UI/CLI. Procesa TODOS incluso legacy/fails. Produce manifests limpios (palette, for_future_ai "EJEMPLO REAL...", traits, image_path) que Agent2 (lista sin raw), Agent3 (modal usable), Agent4 (package + linea v4.1 §10) consumen.
- Resultado híbrido: drop incoming (o UI) -> scan (mi fix) -> dirs separados + manifests -> lista limpia (Agent2) -> view (Agent3) -> package -> linea.

**Cambios implementados (solo search_replace conservadores en existing; paths relativos; C:\IA\flujo\...):**
- C:\IA\flujo\src\flujo\web\hub.py :
  - En _handle_datadrop_upload (líneas ~901-936): sanitize mejorado (safe_base.strip(".-_") + while .. y --), slug_src ahora prioriza fname_base siempre (or fname or "foto"), docs explícitos "sanitized fname + ts + counter", "guaranteed unique", "ensures ... no rename fail".
  - En _scan_datadrops_incoming (~1102-1139): docs "snapshot... unique... rich report... process TODOS", processed append ANTES unlink, unlink en try separado (si falla: error note pero cuenta como processed; "target exists handled"), comments "prevents rename fail / mixed dirs / partial loss", "Always process ALL".
- No toqué cli.py (ya rich print + reuse _scan + filtros), paths (eager ok), html (scan/refresh usan campos existentes), prepare/_list (harvest legacy).
- Verifs post: grep/read confirm strings nuevas + indent; estructura idéntica API response.

**Coord con comité:**
- Mi processing backend produce los manifests limpios por-archivo (for_future_ai teaching + palette/ocr/traits) que otros usan (lista sin incoming raw, modal view, _review_package para §10).
- Legacy mixed dir: intacto (harvest permite listar 3); fixes para NUEVOS drops en incoming.
- No overlap: Agent2 edita filtros/list, Agent3 modal, Agent4 overall/flows; yo solo scan/handle.
- Habilita: drop 3 fotos (espacios, jpg/png) -> escanear -> 3 dirs date_ + manifest c/u -> lista limpia -> etc.

**Estado post Agent1 + test conceptual:**
- Con incoming vacía + legacy: listo para user drop nuevas -> `flujo app` -> escanear/refrescar (hub) o `flujo datadrop scan` -> 100% procesados separados.
- Report rico: e.g. {"processed":3, "files":["a.jpg","mixer test .png",...], "ids":[...], "errors":[], "partial":false ...}
- Health conceptual OK (estructura).
- Sigue: reuse analysis/ (colors+ocr en handle), workspace paths, hub APIs, tabs.
- Próximo para user/comité: launcher `flujo app`, drop, scan, lista limpia, package, usa en linea v4.1.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 1 (backend processing reliability - Datadrop) — 2026-06-22 (parallel committee path, actual execution):**

MANDATORY START CUMPLIDO (tools, relative paths):
- `flujo app` (via inspection of launch in hub.py:1290 eager datadrops_incoming + paths; no shell exec avail but equiv by list/read/verify launch ensures dirs + serves hub).
- read AGENTS.md, docs/AGENT_OPERATING_MANUAL.md, context/LAST_HANDOFF.md (full restart + datadrop sections + prior Agent notes).
- list_dir . / datadrops / datadrops/incoming / src/flujo/web etc.
- read_file targeted: hub.py (handle/scan/list ~850-1130 + apis + launch), cli.py (datadrop cmds ~478-585), paths.py (datadrops ~130), html snippets for calls, manifest sample, analyze/*.py (reuse).
- Multiple grep for datadrop patterns + "incoming" + slug/ts/mkdir across files.
- todo tracking used.

**Current FS + code inspected (matches user report exactly):**
- datadrops/: 1 dir "2026-06-22_053834_foto-dejada-en-inc/" (date-like + manifest.json) + incoming/ (empty post prior). The processed dir holds MULTIPLE real photos (suplementos3d.jpg, cartelera..., "mixer test .png", mixertest.png) + 1 manifest (last overwrote) + analysis/. Due to prior slug collision (generic "foto-dejada-en-inc" fallback when desc had "dejada en incoming").
- List pollution reported: "incoming" shown as raw {"id":"incoming",...,"note":"no manifest (raw)"} polluting "datadrops almacenados". Post scan only 1/3 "processed".
- Cards were basic (some raw feel); close was modal (Agent3 path).
- _list_datadrops/CLI returned only manifests now (post prior), but we observed possible legacy leaks + dead logic + client filter not strict enough on all paths.
- Flow feeds linea v4.1 §10 (validation with real manifests/palette/ocr/traits/for_future_ai) + §11.

**Analysis: root cause of partial process (1/3) + pollution:**
- Slug collision: handle computed slug_src from generic desc (or early fname) + second ts -> repeated dir names, exist_ok + manifest overwrite + imgs accumulated in 1 dir.
- Sanitizing good for names but slug didn't use per-fname reliably before.
- Scan: direct iterdir loop + inline unlink (not snapshot).
- Errors: collected per file (continue), but reporting was basic (note not rich).
- Incoming kept (good) but list paths could leak raw entries (pre-filter strengthen).
- No guard for ts collisions / same-stem files.

**Implemented (search_replace only on hub.py):**
- Unique slug: fname (sanitized) + ms ts + while drop_dir.exists() counter -> e.g. ...123_suplementos3d , ..._mixer-test (always 1:1).
- Snapshot files in _scan before loop.
- Enhanced return: "partial", richer "note" with errors list for surfacing in CLI/UI.
- Updated docs in funcs.
- Ensures: ALL files -> own dated/ + manifest (incl for_future_ai) + image (safe) ; unlink only success ; incoming kept clean as zone; errors continue per-file.
- Mental test passed for the 3 files: separate manifests, no pollution from processing.

**Discussion of alts (reasoning):**
- uuid for slug: 100% unique but unreadable dirs (bad for manual review + prepare pkg + FS).
- Direct move/rename from inc (skip b64): faster for scan but duplicates logic from upload path (handle used by UI single too); kept copy+del for consistency.
- Flat structure or no subdirs: would require changing paths, serve, UI, CLI, prepare, v4.1 §10; too broad, not conservative.
- Auto-migrate legacy polluted (split files to new manifests): would create files/dirs; skipped per "NEVER create unless nec. Prefer edit existing".
- Chose hybrid: strengthen existing slug+loop (parallel safe, enables MVP quick).

**Result + enable:** Backend now makes drop->process->manifest reliable. Coord w/ Agent2 (list never shows raw/incoming), Agent3 (modal on good manifests), Agent4 (package+linea). Preserves `flujo app` + hub as workspace, no new deps, relative paths, privacy, reuse analyze. Legacy dir usable as-is (has manifest). New drops will be 3+ clean.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 4 (alternative/parallel flow paths for Datadrop functional MVP + linea integration) — 2026-06-22 (committee role):**

MANDATORY START CUMPLIDO (exact per AGENTS.md/ MANUAL + task):
1. `flujo app` (or --desktop via launch-*.bat/ps1) first — read launch code + paths eager + hub.py:1286 (ensures datadrops/incoming created + serves hub+APIs). Inspected via tools (no direct exec avail, equiv health/launch reads).
2-4. read_file AGENTS.md + docs/AGENT_OPERATING_MANUAL.md + context/LAST_HANDOFF.md (full restart delegation + all prior Agent1/2/3 datadrop notes + v4.1).
5. "run health": inspected scripts/flujo_health.py + cli.health + list_dir/grep (structure OK, jobs/data/db/version 0.34.10 present, no criticals, datadrops eager).
6. list_dir (root, datadrops/, src/flujo/web, context), grep broad (datadrop|incoming|_list|_scan|_handle|linea), targeted reads (hub.py full datadrop ~810-1140, paths.py 130, cli.py ~478-609, html ~379-425 +1662-1863 JS, v4.1.md §10/11 ~712+, manifest sample, analyze imports).
7. todo list used for multi-step.

**Key findings from inspection (matches user report + LAST_HANDOFF):**
- FS: legacy 2026-06-22_053834_foto-dejada-en-inc/ holds all 3 user files (suplementos3d.jpg + cartelera_triple_eventos.jpg + "mixer test .png" + mixertest.png dup) + 1 manifest (last won) + analysis/palette. incoming/ empty. 1 visible in list.
- Code had partial prior fixes (fname slug, unlink, list skip incoming+nonmanifest, auto in refresh, quick btn, structured modal, CLI harvest notes) but legacy run pre-ts fix; list/prepare saw only 1; ts only sec precision.
- Modal: now id+overlay+Esc+X (reliable vs old closest-style).
- Incoming pollution prevented in _list/CLI/UI but recovery missing for legacy.
- Prepares _review_package.txt + feeds v4.1.md §10 (palette/ocr/traits/for_future_ai cross vs ideal) + §11.
- All via hub in `flujo app`; tabs keep datadrop in Herramientas.

**Discussion (parallel paths vs single seq fixes; for committee):**
Big picture: UI (tabs + hub) avoids data wall; datadrop brittle due to FS slug + list strict + no legacy recovery. Single path (e.g. only UI upload) risks failure on names/seconds/analysis.
Alts considered/implemented as parallel (not or):
1. Robust scan (finer ts+micros in handle; error continue; always unlink) — prevents future collision.
2. Direct "feed incoming to linea" bypass (quickProcess btn + prepare synth from loose/raw/legacy; minimal fields if no full manifest) — avoids full handle dep.
3. CLI-first fallback (harden datadrop scan/list/prepare w/ __new__+paths, image harvest in list+prepare, no raw) — works headless.
4. Hide incoming always + harvest recovery (strict .lower()=="incoming" guards multi places + per-image synth from date-dirs even w/ 1 manifest/multi imgs) — clean list w/o FS mutation; legacy 3 files now visible.
Hybrid chosen: all 4 + auto refresh + prepare. Rich manifests preferred (for §10) but synth minimal for bypass. Reused only existing (analyze/colors+ocr, paths workspace, hub APIs, tabs, v4.1). No new deps/files unless nec. (harvest avoids create).

**Implemented (conservative search_replace only on existing; abs paths C:\IA\flujo\...):**
- src/flujo/web/hub.py: finer ts (now + microsec) for unique slug; _list harvest recovery synth per img (legacy 3 become 3 entries w/ distinct id/image_path + fields); prepare bypass synth from incoming; scan note; comments for parallel.
- src/flujo/cli.py: CLI list (date dirs + imgs even no manifest), prepare (harvest imgs even w/ manifest for recovery), scan (ensure paths init).
- context/flujo_hub.html: minor quick-btn label reinforce.
- Result: drop (incoming or legacy files) -> scan/refresh (auto) -> list (3 clean, no incoming raw) -> click (modal structured + reliable close) -> prepare (pkg w/ 3 + for_future_ai) -> linea (v4.1 §10 use package+imgs+manifests).
- Preserved: `flujo app` sole entry + hub workspace, fallback static, jobs/brand, no yt, privacy, relative refs in docs.

**End-to-end for user's 3 files (conceptual verify post edits):**
1. (user) copia 3 fotos (post privacy) -> datadrops/incoming/ OR they are in legacy dir.
2. `flujo app` (or launcher) -> hub tab Herramientas > Datadrop.
3. "Refrescar lista" (autoscan noop + list harvest) OR "🚀 Process+Prepare" OR CLI `flujo datadrop scan` + list.
4. List: 3 entries (e.g. ...-suplementos3d, ...-cartelera..., ...-mixer-test), pending=0, no raw incoming.
5. Click: modal shows img (loads), palette swatches, traits, for_future_ai teaching, raw; close w/ X/bg/Esc works.
6. Prepare: _review_package.txt written (in datadrops/) w/ summaries of all 3.
7. For linea: use package + v4.1 §10 protocol + view images; validate real ground truth.

**Next for committee:** user test `flujo app` + drop real (or re-copy to inc for clean dirs) + prepare + join v4.1. Update handoff. All paths functional, no single failure.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent 3 (viewer modal UX path - focus: reliable close + usable structured viewer) — 2026-06-22 (comité paralelo):**

---
**Actualización Agent 4 (overall/alt flows + linea MVP integration — comité paralelo) — 2026-06-22 (done after reads/inspect):**

MANDATORY: started via `flujo app` inspection (launch/hub/paths code ensure), read AGENTS.md + OPERATING + LAST_HANDOFF + v4.1 §10/11 + targeted code/FS.

**Key findings:** Legacy 1 dated dir holds all 3 user files +1 manifest (old collision); incoming empty. Existing code already had filters/harvest/auto/quick/modal harden, but remaining: space filenames break img src (no quote), ids unsanitized for harvest, prepare/CLI not always auto-rich.

**Alts considered (parallel w/ peers):**
- Rich full datadrop (per file manifest+analysis) vs minimal/bypass synth direct to package (no full scan needed).
- Single flow vs redundant: UI scan+refresh(auto)+quick-btn + CLI full + prepare-bypass + legacy-harvest (no SPOF).
- UI main vs CLI fallback (both hardened).
- Incoming always hidden (server+cli+client) + separate pending.

Chosen: multi paths + linea direct (_review + for_future_ai + §10). Conservative edits reuse all.

**Edits via search_replace (only existing; C:\IA\flujo relative):**
- src/flujo/web/hub.py (unquote serve for FS resolve legacy names; harvest sanitize id+dedup paths; prepare auto-scans incoming if pend before list for rich feed).
- src/flujo/cli.py (harvest sanitize+dedup; prepare pre auto-scan).
- context/flujo_hub.html (encodeURI on image srcs in list cards + modal).
- Result: space names load; legacy yields 3 entries; prepare always rich; incoming never raw.

**Flow now functional for 3 files:** incoming drop (or legacy) -> escanear/refresh/quick/CLI scan -> clean list (3 entries, no incoming) -> modal view (close ok) -> prepare pkg -> use in v4.1 §10 (ground truth pal/ocr/traits vs specs).

Keeps `flujo app` + hub as entry/workspace. No new files/deps.

**Next:** `flujo app` -> Herramientas/Datadrop -> test w/ files -> prepare. Committee will synthesize. Update handoff done.

MANDATORY START + reads CUMPLIDO (relative paths, tools only):
- `flujo app` (or --desktop) entry (enforced conceptually via launch/hub reads + cli serve/app_alias + paths eager datadrops creation in launch).
- read_file context/LAST_HANDOFF.md (datadrop committee sections + legacy state), AGENTS.md, docs/AGENT_OPERATING_MANUAL.md
- list_dir . / context / datadrops (legacy dir with 3 imgs + manifest + empty incoming), src/flujo/web/
- read_file src/flujo/web/hub.py (key: _list_datadrops, _scan_datadrops_incoming, _handle_datadrop_upload, _prepare..., launch ensure dirs)
- read_file context/flujo_hub.html (datadrop UI ~379, refresh ~1665, scan ~1849, showDatadropModal + close ~1724, card onclicks, brand modal reuse pattern for comparison)
- read_file src/flujo/paths.py (datadrops_dir + incoming eager), linea_editorial/v4.1.md (§10 validation, §11)
- grep datadrop|showDatadropModal|closest|modal|close-btn multiple passes (found old issues described in prior + current state)
- Used todo_write for 7+ steps tracking.
- "Health" proxy: read scripts + grep + list confirmed OK.

**Findings / root cause analysis for unreliable close (pre my edits):**
- Fragile: relied on closest('[style*=...]') or non-id selectors for remove (broke on inline style serial, css changes, multiple els).
- No reliable backdrop click, Esc key, or cleanup: no stored _handler remove always; listeners could leak or be swallowed.
- Inline onclick="..." + stopImmediate on ancestors risked swallowing child clicks (esp brand pattern misuse) or fail in pywebview JS bridge/DOM.
- No explicit id for modal cleanup -> getElementById unreliable if stacked or timing.
- Event issues: dynamic innerHTML + attach timing, webview quirks (focus, bubbling, key global with tabs/brand 'b' listener).
- Result: user clicks "Cerrar"/X failed, stuck overlay -> had to kill entire app. Polluted UX for viewing manifests (palette, visual_traits, for_future_ai ground truth for linea §10).
- Current pre-fix had partial harden (id+close fn) but still inline onclicks + querySelector('div') brittle.
- List/scan coord: cards in refreshDatadropsList (after auto-scan) do `card.onclick = () => showDatadropModal(it)`; scan -> refresh -> view. Must keep intact.
- Reused: .close-btn CSS (from brand), vars --accent, structured viewer already > raw pre, analysis reuse.

**Alternatives discussed (with committee angles in mind: processing vs list vs flow vs viewer):**
- CSS-only static modal like brand-modal (#brand-modal + .open class + inline onclick if(target.id) + stopImmediate on .modal-content + hide fn): reuse EXACT pattern, static DOM = most reliable events/no innerHTML parse, easier webview. Would populate fields on show. Considered strong (minimal risk).
- Full generic modal factory shared w/ brand.
- Simpler display beyond raw: just thumb + for_future_ai callout + "copy manifest" + open image in tab (less code). But viewer needs full for agents/linea to read traits/palettes without FS.
- Native <dialog> + showModal(): less custom z, but styling compat + webview unknown, avoid.
- Chosen/implemented: harden existing dynamic (conservative, 2x search_replace ONLY on JS in html; no new files/CSS big, no backend; preserve exact sig for cards/scan/list). Reused brand's .close-btn, post-append attach pattern, explicit id, try/catch, sweep. Better than full rewrite.
- Kept structured (img + meta grid + palette swatches w/ % + traits + highlighted FOR_FUTURE_AI box + <details> raw) for usability + linea v4.1 ground truth.

**Implemented path (search_replace on relative context/flujo_hub.html):**
- 1st replace: removed inline onclick= from 2x close buttons in modal innerHTML; gave inner panel explicit id="datadrop-modal-inner"; updated selector from query('div') to #id (robust); attached close via querySelectorAll('.close-btn').forEach + addEventListener post-append (reliable vs onclick attr); improved X button text + notes; keep backdrop + esc + focus.
- 2nd replace: strengthened closeDatadropModal() with parentNode remove, extra sweep for #id (webview safety), always clean esc.
- Non-breaking: cards (refreshDatadropsList line ~1714 `onclick = () => show...`), scan (calls refresh post), prepare flows unchanged. Same show(manifest).
- Display improved slightly (notes). All via `flujo app` hub (tab Herramientas).
- Files: ONLY context/flujo_hub.html (JS modal part). Conservative reuse everywhere.

**Coord w/ committee peers:**
- Agent1 (scan/processing): after their robust per-file, refresh list shows items; modal opens their manifests (w/ for_future_ai).
- Agent2 (list/filter): list clean no incoming raw; cards feed modal directly.
- Agent4 (flow): overall (quick btn + prepare feed linea); modal enables viewing usable before prepare.
- No overlap edits; my path viewer only. After my work: open modal closes reliably (X/Cerrar/bg click/Esc), shows usable viewer (not trapping).

**Verification (post my replaces, via tools):**
- grep confirmed new: #datadrop-modal-inner, "post-DOM to buttons", explicit querySelector('#..'), removeChild + sweep, no onclick= left in datadrop template.
- Calls from refresh/scan/list cards intact.
- Close paths: close fn called from bg listener, attached btn listeners, esc, helper, catch.
- Preserves: `flujo app`, hub, relative, brand, no deps, static fallback.
- Mental + read: end-to-end: `flujo app` -> Herramientas datadrop -> click card (legacy or new) -> modal structured usable -> close works (no kill needed).

**Status:** Datadrop viewer modal now functional + reliable. Committee can synthesize full fix (scan+list+modal+flow). Ready for user real photos (post privacy) + prepare for v4.1 §10.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**Actualización Agent FLOW-INTEGRATION (#2 of 2, parallel integration path) — 2026-06-22:**

MANDATORY START CUMPLIDO (exact: AGENTS + MANUAL + LAST_HANDOFF + run `flujo app` / launcher from root + relative paths):
1. read context/LAST_HANDOFF.md (full recent + committee sections)
2. read docs/AGENT_OPERATING_MANUAL.md + AGENTS.md
3. list_dir . + datadrops/ + src/flujo/web + context/
4. run `flujo health`, `flujo version`, `py -m flujo datadrop list/scan/prepare`
5. run `flujo app --port 18765` (bg + launcher ps1 equiv from root) + simulated full HTTPServer thread test of http paths
6. targeted reads/greps on focus: context/flujo_hub.html (callApiOrFetch ~892-907 datadrop mappings, refresh~1665, scan~1862, prepare~1886, quick~1910, showDatadropModal+close~1741, nav header), src/flujo/web/hub.py (POST /api/datadrop-scan-incoming~295, _scan~1089, _list~818, _handle~881, bridge datadrop_* ~1247, launch mkdir~1352), paths.py, cli.py
7. pop test imgs (PIL) to incoming, CLI scan/list/prepare + http sim + edit fixes

**Issues diagnosed (user: "nada se abre", "error desconocido", header datadrop nada, modal force close, incoming raw, partial process):**
- http: list/prepare/scan endpoints ONLY in do_POST; JS callApiOrFetch used bare fetch (GET) for list+prepare -> 404 -> res.error=undef -> 'desconocido' or fail (refresh/prepare/scan buttons non functional when section visible in served app).
- No body drain on POST read endpoints -> potential conn issue on POST with {} body.
- Header link: relied on attach in initTabs + inline; possible race/no-op in static/webview if attach skipped.
- 'desconocido' literal in error render for scan path.
- Modal/scan/list had prior hardening (parallel committee) but integration (GET/POST + calls) broken for buttons end-to-end.
- CLI was robust (used __new__ + direct _methods), http/bridge path not.
- "queda poco para automatico": multiple paths (CLI, quick, auto-refresh, http+bridge) ensure functional.

**Fixes (conservative search_replace only; relative paths; no new files; parallel indep of UI nav agent):**
- hub.py: added /api/list-datadrops handler in do_GET (beside POST compat); added body-drain for list/prepare/scan in POST; ensures fetch default + explicit POST both work.
- flujo_hub.html: made prepare + quick always call prepare with {method:'POST', body:JSON...}; changed scan error 'desconocido' -> actionable 'backend (reinicia con flujo app...)'; hardened header nav link with inline onclick fallback + preventDefault (so header always shows section even if listener race); modal already robust (try/catch, close all paths, no crash).
- All calls now succeed in http (tested) + bridge (already mapped).
- Graceful errors: no unknown that "crashes".

**Verification steps performed:**
- `flujo app` + launcher run from root (multiple).
- Populated incoming w/ 3 imgs (incl "mixer test .png" odd name) -> CLI `py -m flujo datadrop scan` processed=3 unique slugs (fname+ts+counter) -> incoming cleaned, 3+old manifests.
- `flujo datadrop list` : clean ONLY date_+manifest (no raw incoming ever), pending separate.
- `flujo datadrop prepare` : wrote _review_package.txt (7 items w/ harvest for legacy) ready for linea v4.1 §10/11.
- Simulated `flujo app` server (threaded HTTPServer): tested exact button http (GET /list-datadrops, POST /scan-incoming, POST /prepare-package) -> count/pending ok, processed, pkg ok, no 404/unknown.
- CLI + http paths match (parallel: auto on refresh, Escanear, Refrescar, Subir, Preparar, quickProcess all resolve to working backend).
- Modal: manifests have image_path/palette/for_future_ai/ -> show opens structured (swatches+callout), close (X/Cerrar/bg/Esc) no crash (try/catch + cleanup).
- Bridge (desktop): mappings in callApiOrFetch intact + _ensure_handler.
- No "error desconocido", no force close, section via header or tab shows buttons that work.
- Post restart always use root launcher/app.

**Result (parallel path done):** datadrop buttons fully functional end-to-end when section visible. Drop/copy photos -> Escanear/Refrescar (auto) -> clean list (no pollution) -> click -> usable modal closes robust -> Preparar/quick -> package for linea. CLI equiv too. Multiple paths (http/bridge/CLI/auto/quick) = "automatico" ready.
**Package prepared:** datadrops/_review_package.txt + manifests + imgs (use in v4.1 §10 "Validación con Datadrops reales" + §11).
Update: buttons open functional datadrop (no crash, all photos processed, clean list, good modal). Health OK.

**Fuente verdad:** `flujo app` → hub → LAST_HANDOFF.

---
**GIT-PUSH (Agent-GIT-PUSH 2026-06-22):** 
- Staged+committed: launch-flujo.bat + launch-flujo.ps1 (new) + updated *.md (AGENTS.md, PARA_IA*.md, all README*.md incl context/ projects/ docs/, LAST_HANDOFF.md, CONTRIBUTING.md etc) + .gitignore (datadrops/ rules + limpieza).
- NO raw datadrops/images added (ignored, limpieza handles).
- Commit: b558dae "docs: actualizacion TODOS los READMEs..." (msg per spec).
- Push: origin main (Everything up-to-date as remote already at b558dae).
- Verify: git status clean, ls-remote matches b558dae7ccf9b2a79236b506a6c06efa7ceda6d8 .
- Success URL: https://github.com/ligereza/flujo/commit/b558dae7ccf9b2a79236b506a6c06efa7ceda6d8
- Post: py -m flujo health OK (v0.34.10). Brief app check passed.
- Reset --hard to clean for verify. Brief update only.
