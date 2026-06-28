# context/ — Workspace diario de flujo

Este es el **centro del repo** (pro workspace servido por la app).

**Entrada diaria obligatoria (ÚNICA y recomendada #1 — la única):** `flujo app` (o `flujo app --desktop`).

Lanza **la app real**: servidor + APIs reales (brand, parse, jobs, delegate, SSE, tokens, datadrop...) + sirve los tres HTMLs como UI de la app (hub pro + visualizadores).
- `flujo app` abre/sirve http://... el `context/flujo_hub.html` (workspace central) con datos live.
- Fallback: abre cualquiera de los .html directos (flujo_hub.html, svg_visualizer.html, plano_demo.html) — funciona 100% estático con mocks.
- `flujo app --desktop`: ventana nativa pywebview + tray (sin browser chrome).

**`flujo app` = única entrada diaria. Hub + LAST_HANDOFF.md = fuente de verdad principal.**

**Avances (2026-06-22):** Datadrop MVP listo (incoming bulk scan → manifests ricos con for_future_ai; botones header y sección funcionales post-fix con showTab robusto; lista limpia solo procesados; modal + prepare). Delegación paralela (2+sup + 5 roles). Launchers + hub tabs. Ver context/AVANCES_BLOCK.txt. Dirección: auto-compact + linea v4.1 usando datadrops como ground truth real.

HTMLs = la UI real de la app. Siempre empieza por aquí + lee LAST_HANDOFF.

## Archivos clave (UI de la app — siempre accede vía `flujo app`)

1. **flujo_hub.html** — El workspace principal pro (intake de pedidos, visual teaser, comandos, **delegación multi-agente 5 roles paralelos**, live, tokens, brand validator, **Datadrop MVP en pestaña Herramientas**). **El centro diario.**
2. **svg_visualizer.html** — Visualizador embebido real de piezas SVG (grupos exactos de /svg).
3. **plano_demo.html** — Plano interactivo + rider + costos + export.
4. **LAST_HANDOFF.md** — Estado actual + tareas (low token para IA y continuidad). **Fuente junto al hub.**

Los tres HTMLs **son la UI completa de la app** cuando los sirve el backend de `flujo app`.

## Otros archivos

- `DAILY.md` / `ESTADO.md` / `dashboard.html` — Notas rápidas / report legacy (gitignored; se regeneran vía `flujo daily`). Limpieza conservadora (solo generados) mantiene context/ ágil.
- Caches limpiados completamente (2026-06-22): 16 __pycache__ + 123 *.pyc + .pytest_cache (solo generados, ver LAST_HANDOFF para rutas exactas).
  **Siempre empieza por `flujo app` → usa el hub (`flujo_hub.html`) + LAST_HANDOFF.md** para el uso diario de la app y reanudación.

Ver también: `LAST_HANDOFF.md`, `../README.md`, `../docs/REPO_MAP.md` y `../docs/HIGIENE_REPO.md`.

## Flujo recomendado (diario — práctico para diseñador)

- **Siempre empieza aquí (obligatorio — única entrada):** ejecuta `flujo app` (o `flujo app --desktop`).
- Usa el **hub** (servido) como centro pro: intake (pedidos → brief + match + crear job real), visual teaser, comandos, sección "Delegar a Agentes Especializados" con guía práctica + prompts listos + live /api/delegate (5 roles paralelos).
- Abre visualizadores embebidos **desde el hub**: `svg_visualizer.html` (SVG por grupos reales), `plano_demo.html` (interactivo).
- **Datadrop (MVP funcional):** en pestaña "Herramientas" (o link header "Datadrop (en Herramientas)"): click header abre confiablemente (showTab + scrollToSectionRobust con rAF/retry), scan incoming procesa múltiples fotos, lista limpia (solo procesados con manifest, incoming separado), upload + prepare package for linea v4.1.
- Para agentes IA: ejecuta `flujo app` → lee LAST_HANDOFF.md + AGENT_OPERATING_MANUAL.md (dentro del hub). Delega paralelo vía hub (o CLI).
- Todo: HTMLs + backend = app real. Fallback directo HTML = ok. **Hub + LAST_HANDOFF = fuente de verdad.**

**Integraciones modernas y futuro:**
- `projects/flujo/flujo.json` = fuente única de tokens/brand (export vía /api/export-tokens a CSS/JSON/SCSS para Figma/Framer).
- Delegación multi-agente paralela (5 roles: Visual Polish, Pipeline, Brand, Future, Packaging) formalizada.
- Live: SSE real-time (/api/events), jobs/SVG auto-refresh, notifs, PWA servida on-the-fly.
- Todo gratis, local-first. Export limpio a AI/PS/Blender.

Todo alineado a `projects/flujo/` y listo para Illustrator / Photoshop / Blender.

## App real (backend + HTMLs = UI completa)
**Entrada diaria obligatoria (única):** `flujo app` (o `flujo app --desktop`).

Lanza servidor HTTP stdlib + APIs reales + sirve los **tres HTMLs como UI de la app real** (hub principal + visualizadores) + bridge pywebview desktop/tray.

**Los tres HTMLs son la UI:**
- flujo_hub.html (intake + delegación + live + comandos)
- svg_visualizer.html
- plano_demo.html

**APIs reales (activas sólo con `flujo app`):**
- GET `/api/ping`, `/api/load-flujo-brand`, `/api/list-svg-works`, `/api/list-jobs`, `/api/export-tokens`
- POST `/api/parse-real-pedido`, `/api/run-safe-command`, `/api/create-job-draft`, `/api/delegate` (5 roles paralelos)
- GET `/api/events` (SSE)
- PWA on-the-fly.

**Hub (flujo_hub.html cuando app corre):**
- Detecta "CONECTADO (APIs reales + delegate)" vs fallback estático.
- Carga datos live (brand, SVG works, jobs).
- Tabs funcionando (Intake & Jobs / Visuales / Planos / Agentes / Herramientas).
- Delegación: tarea + 5 roles (Visual Polish / Pipeline & Integration / Brand Guardian / Future/Modern / Packaging & Distribution) + "Copiar prompt" o "Delegar seleccionados (live API)".
- Datadrop en Herramientas: header click confiable, scan múltiple, lista limpia, package para linea.
- Todo apunta a usar hub + LAST_HANDOFF.

Paths usan asset_root/workspace para packaged (`flujo package`). Ver src/flujo/web/hub.py + cli.py.

Privacidad: solo comandos whitelist + siempre `flujo privacy scan` antes de IAs externas.

## Arquitectura limpia de la App (local-first, Python core, web pro UI, gratis)
- **Core (Python):** src/flujo/ — CLI (Typer), intake/jobs/render/plano/brand/privacy/airdrop. Cero UI deps en runtime.
- **Bridge/API local:** src/flujo/web/hub.py — stdlib HTTPServer + REST/SSE + pywebview js_api bridge. Lógica real (parse, jobs, brand, delegate) + subprocess seguro. Sirve context/ como UI pro.
- **UI (Frontend):** los tres HTMLs (flujo_hub.html + svg_visualizer.html + plano_demo.html) servidos por backend = la UI completa de la app. Dark-pro brand-enforced desde projects/flujo/flujo.json. JS: live, delegate paralelo, PWA, validator, SSE.
- **Desktop:** pywebview (--desktop) + pystray (opcional) + auto-port + tray + icono procedural.
- **Packaging gratis (completo y listo):** `flujo package` (PyInstaller en extras) genera .exe onefile/onedir profesional: icono embebido (Pillow), --noconsole, sin terminal, título "flujo • Workspace", tray, bridge directo. Bundled: context/, svg/, projects/flujo (brand), templates internos. Jobs y datos en `flujo_workspace/` sibling al exe (manejo frozen paths + workspace persistente). Equivale a lanzar `flujo app --desktop` de forma standalone. + Inno Setup (gratis) recomendado para installer con menú inicio. Ver CLI help y abajo.
- **Datos:** Todo FS local (jobs/, projects/, svg/, data/, flujo_workspace en packaged).

Todo 100% gratis, Windows-first (`py`), high visual. `flujo app` = entrada diaria que sirve el hub + APIs + delegación. HTMLs = la UI. Brand = 'flujo'. App = free / local-first.

## Integraciones modernas implementadas
- Real-time: /api/events (SSE nativo stdlib + loop persistente) + initRealtimeSSE + UI reactiva en hub (auto refresh jobs/SVG cards, toasts, browser Notifications, live pulse indicator, change detection).
- Mejor bridge: /api/run-safe-command, /api/parse-real-pedido, `flujo delegate` + POST /api/delegate (5 roles paralelos).
- Packaging real desktop gratis completo: `flujo package` (PyInstaller + Pillow icon gen + launcher que fuerza desktop nativo + bundling assets + workspace writable separado). Listo para diseñador: doble clic abre app premium sin Python visible. Actualizado paths/jobs para writes seguros.
- PWA (manifest + sw.js on-the-fly) + "Instalar app".
- Delegation system first-class: 5 roles (incl. Packaging & Distribution Agent) centralizados en hub.py. /api/agents-roles + /api/delegate paralelo. Hub UI: tarea + multi + copiar prompts completos + "Delegar seleccionados (live)". CLI `flujo delegate`. Prompts listos alta calidad. Lanza siempre en clones paralelos. Guía "Cómo delegar desde el hub" en el propio HTML.
- Design Tokens: /api/export-tokens (CSS/JSON/SCSS directo de flujo.json). Botones en hub.
- Brand enforcement integrado + STRENGTHENED (Brand Enforcement sección prominente + VALIDAR BRAND AHORA grande/actionable + validatePreviewsOnly + forceGuard + auto hints + "BRAND ENFORCED" comentarios duros en todos los HTMLs principales + tapiz default flujo pro). Gatekeeper para confianza del diseñador.

**Avances recientes (datadrop + hub + delegation):**
- Datadrop MVP completamente funcional en pestaña Herramientas del hub: header "Datadrop (en Herramientas)" click abre confiablemente (previene default, showTab robusto + requestAnimationFrame + retry en scrollToSectionRobust), scan procesa múltiples (unique slugs + counter para bulk incoming), lista limpia (solo date+manifest procesados; pending separado), upload directo, prepare package para linea v4.1 (genera _review_package.txt + for_future_ai + manifests + traits).
- Delegación en hub operativa para 2+ roles/sup paralelos + live API.
- Launchers (launch-flujo.bat / .ps1) + `flujo app --desktop` alineados.
- Linea v4.1 ground truth lista vía datadrops reales.
- Brand fully enforced desde projects/flujo/flujo.json en todo.

## Packaging y Distribución Desktop (Windows .exe standalone gratis - PyInstaller)

**Solución completa lista para usar (todo gratis):**

1. Prepara build env (una vez):
   ```
   py -m pip install -e .[web,desktop-extras,build]
   ```
   (pywebview, pystray, Pillow, PyInstaller)

2. Genera el .exe (onefile recomendado, limpio):
   ```
   flujo package
   # o
   flujo package --onedir -o mi-dist
   ```

3. Resultado en `dist/` :
   - `flujo-hub.exe` (o carpeta)
   - Icono profesional generado (dark + accent #2d5a4a + marca F geométrica limpia con draw)
   - Doble clic: lanza directamente ventana nativa "flujo • Workspace" (pywebview, noconsole, tray si disponible)
   - Assets embebidos: hub HTML/JS completo, visualizers, brand flujo.json, svgs (cargan), templates de export, jobs/_template.
   - Escribe jobs/ briefs / data / inbox / piezas en `flujo_workspace/` (hermano del exe) → persistente, no toca archivos del programa.
   - Servidor soporta /svg/* /projects/* etc para que visualizers funcionen full en el .exe empaquetado.

**Pruebas mentales / issues comunes resueltos:**
- onefile: assets en _MEIPASS temp (solo lectura); workspace en exe.parent/flujo_workspace (writable).
- onedir: similar, al lado.
- Paths: `is_packaged()`, `asset_root()`, `workspace_root()`, `jobs_dir()` etc redirigen correctamente.
- Jobs/create/list: usan workspace en frozen (ver src/flujo/jobs/job.py + paths.py).
- Export (blender jsx): templates internos bundled bajo flujo/templates.
- Visualizers: /svg/* servidos desde bundled assets (fix en hub server para packaged).
- No "python" feel: windowed + título + icono embebido en exe + taskbar.
- Actualizar app: vuelve a correr `flujo package` tras cambios (rebuild).
- Instalador pro (gratis extra): usa Inno Setup (jrsoftware.org) con .iss simple apuntando al .exe + .ico (ver ejemplo en `flujo package` output).

El comando `flujo package` está integrado en CLI (ver `flujo package --help`). El launcher es entry point directo a desktop mode.

Todo alineado a marca flujo, profesional para diseñador Windows.

## Future Roadmap
- Live extendido (watcher opcional, previews reales en viz).
- Más tokens roundtrip (Figma plugin bridge gratis).
- Desktop enhancements (notifs nativas, file assoc via Inno gratis).
- Intake auto (webhook/IMAP stub, sin deps).
- Delegación avanzada + sidecars (git clones automáticos, coordination rules ya en AGENT_OPERATING).
- PWA offline caching mejorado.
- Prioridad: local-first, gratis, Python core, HTMLs pro = UI.

Visión: un solo `flujo app` = shell diario del diseñador (UI = los tres HTMLs + backend real). Delegación multi-agente paralela (5 roles) permite escalar vía clones.

**Fuente de verdad:** siempre ejecuta `flujo app` → usa hub como workspace. Para reanudar trabajo: `context/LAST_HANDOFF.md` + hub + AGENT_OPERATING_MANUAL.md.

## Dirección actual (paralelo + datadrops reales)
Trabajo paralelo (delegación 2+ roles/sup + clones): auto-compact prep, paths/launchers, brand. Datadrops reales (datadrops/incoming/ + scan + manifests + for_future_ai + _review_package) alimentan linea v4.1 (ground truth para paletas, OCR, traits de entregados reales). Usa `flujo app` + hub para todo (subir/scan/prepare + delegar).

Ver: context/flujo_hub.html (UI + delegación práctica), src/flujo/web/hub.py (backend/APIs/delegate + datadrop), cli.py, docs/AGENT_OPERATING_MANUAL.md, projects/flujo/flujo.json, context/LAST_HANDOFF.md.
