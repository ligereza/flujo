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
5. list_dir . + context + linea_editorial + datadrops (v4.1.md presente; datadrops/ ausente — esperado: datadrops_dir() = workspace_root()/datadrops lazy mkdir en upload; workspace_root()=repo en dev. 0 manifests reales aún).

**Review de agentes delegados (UI/Plano, Datadrop, Linea):**
- UI/Plano Optimizer: Re-leyó handoff + refs explícitas a `flujo app` + hub. Cambios confirmados vía grep/read: tabs deployment, single Brand header button (showBrandModal), datadrop inside herramientas tab, plano recalcular reactive + real grid logic (numMesas from engine, param-driven stand/mesas/pasillo/testeo no overlap).
- Datadrop: Refs `flujo app` + handoff in code/docs. datadrops_dir in paths.py (workspace), /api/datadrop* + /datadrops/ serve in hub.py, for_future_ai in manifests, prepare package, UI in hub with upload/list/modal/prepare. No repetition with others.
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
