# AGENT OPERATING MANUAL — flujo (token-efficient)

**Leer esto primero. Solo esto + el hub (vía `flujo app`).**

**Punto de entrada diario OBLIGATORIO (ÚNICO):** ejecuta `flujo app` (o `flujo app --desktop`).

Lanza **la app real** (servidor + APIs reales + sirve los tres HTMLs como UI de la app):
- `context/flujo_hub.html` = workspace principal pro (intake, delegación, comandos, live).
- `context/svg_visualizer.html` + `context/plano_demo.html` = visualizadores embebidos.

Cuando `flujo app` corre: backend real (APIs para parse/jobs/delegate/SSE/brand). Abrir HTMLs directos = fallback estático perfecto.

El hub (dentro de la app) = UI + centro de delegación. Brand = 'flujo' (projects/flujo/flujo.json). App = gratis/local-first/Python core.

**Fuente de verdad:** `flujo app` → hub + `context/LAST_HANDOFF.md`.

## Flujo 1: Pedido Reciente (operativo)
Recibes: link del repo + correo o mensaje.

**Proceso exacto (usa el hub):**
1. Ejecuta `flujo app` (entrada única).
2. Pega el texto en Intake del hub.
3. "Generar brief ordenado + match" (usa API real si disponible).
4. Revisa match + brief.
5. Si match → usa formato + comando listo + flujo.
6. Si no → propone sección o agrega tarea en LAST_HANDOFF.

**Salida mínima:**
- Brief + comandos exactos
- Decisión (MATCH o NUEVO) + nota herramienta.
- Siempre desde hub servido por app.

## Flujo 2: Mejoras al Repo
Recibes: repo + "continúa con las mejoras".

**Proceso:**
1. Ejecuta `flujo app` (obligatorio) + lee `context/LAST_HANDOFF.md`.
2. Lee este manual.
3. Elige 1-2 tareas (o usa sección "Delegar..." en hub para split paralelo a múltiples roles especializados).
4. Trabaja en clon (usa hub + CLI). Lanza sub-agentes en clones paralelos.
5. Entrega airdrop + actualiza LAST_HANDOFF al final.

**Siempre:** referencia hub + LAST_HANDOFF como fuente. No leas todo el repo.

## Delegating to Specialized Agents

**Modelo formal de delegación multi-agente (paralelo real en clones git separados):**

El principal decide el split y lanza sub-agentes especializados **en clones git separados** (nunca mismo árbol).

**Cada sub-agente sigue exactamente:**
1. `flujo app` (o `flujo app --desktop`) — **entrada diaria obligatoria**.
2. Lee `context/LAST_HANDOFF.md` + este manual (bajo token).
3. Usa el **hub** (dentro de `flujo app`) como workspace principal.
4. Entrega **su propio airdrop** (con handoff propio en _airdrop/).

Principal integra airdrops en orden + actualiza LAST_HANDOFF central.

**Coordinación estricta (cumple siempre):**
- Visual Polish revisa **todos** outputs visuales al final.
- Brand Guardian valida **antes** de cualquier toque a `projects/flujo/flujo.json`, linea_editorial.md o paletas.
- Packaging & Distribution **coordina** con Pipeline en paths, assets, launchers, bundling.
- Future/Modern **nunca** toca core (cli, jobs, hub.py, render, paths) sin aprobación explícita Pipeline + Brand en su handoff.
- Respeta: privacy, airdrop, `py` Windows, tests + compileall.

**Ventajas:** trabajo paralelo real, ownership claro, escalable.

**Cómo delegar desde el hub (práctica diaria recomendada):**

Abre **`flujo app`** (entrada obligatoria). Baja a **"Delegar a Agentes Especializados"** (guía práctica incluida en el hub) + usa sección Datadrop (botones working: upload/scan/list/prepare; header "Datadrop (en Herramientas)" abre tab+sección):

1. Escribe **tarea específica** (usa ejemplos o edita).
2. Selecciona 1 o varios roles (múltiples = delegación paralela real).
3. Pulsa:
   - "Copiar prompt completo" por rol (templates formales listos).
   - O "Delegar seleccionados (live API)" — llama /api/delegate en paralelo, resultados visibles + auto-copia prompt.
4. Pega **cada prompt completo** en otro clon/terminal/IA.
5. Cada sub-agente: `flujo app` + LAST_HANDOFF + su prompt + sigue reglas → airdrop.

**Datadrop en protocolo agente:** usa hub Datadrop section (o `flujo datadrop scan/list/prepare`) para fotos terminadas → manifests + for_future_ai. Prepara auto-compact para parallel work; linea v4.1 usa datadrops como real examples.

El hub genera prompts que **siempre incluyen** `flujo app` + LAST_HANDOFF + modelo de delegación. CLI equivalente: `flujo delegate <role> "tarea..."` (usa mismos templates centralizados).

**Roles especializados (nombres EXACTOS — para /api y prompts):**

- **Visual Polish Agent**: Enforce 'flujo' brand en **todos** outputs (HTMLs/SVGs/previews/tapiz/docs). Paleta exacta projects/flujo/flujo.json. Dark pro, spacing generoso. Revisa salidas de otros. Prioridad: credibilidad premium diseñador.
- **Pipeline & Integration Agent**: Dueño solidez `flujo app`. CLI, jobs, intake, render, airdrop, hub backend (SSE/delegate/tokens), tests, pyproject. Pruebas obligatorias.
- **Brand Guardian**: Custodio identidad. Fuente verdad: projects/flujo/flujo.json + linea_editorial.md. Valida todo. Edita solo brand.
- **Future/Modern Agent**: Explora integraciones nuevas (webhooks, tokens, intake auto, SSE extendido...). **Nunca toca producción sin revisión**. Entrega prototipo + riesgos + nota coordinación.
- **Packaging & Distribution Agent**: `flujo package` (PyInstaller gratis), desktop launcher forzado, paths frozen (asset_root vs workspace), bundling context/svg/projects/flujo + templates, icono, tray, onefile/onedir, hints Inno Setup. Coordina con Pipeline + Brand. Windows-first, cero deps.

**Prompts listos para usar (copia COMPLETA desde aquí o —mejor— genera/copia desde el hub en `flujo app`. Reemplaza solo la [Tarea específica]):**

**Visual Polish Agent (copia esto entero):**
```
Tu rol: Visual Polish Agent.

Sigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.

Punto de entrada OBLIGATORIO: ejecuta `flujo app` (o `flujo app --desktop`). Abre el hub pro. Lee context/LAST_HANDOFF.md + este manual primero (bajo token).

[Tarea específica: e.g. "Pulir todas las secciones de contexto/flujo_hub.html, svg_visualizer.html y plano_demo.html para que cumplan exactamente la paleta y reglas de projects/flujo/flujo.json. Asegura dark pro total (sin partes claras), márgenes generosos ≥14-24px, botones consistentes, previews SVG alineados a brand. Revisa cualquier output reciente de otros agentes y corre Brand Validator antes de entregar."]

Trabaja en tu clon separado. Entrega SOLO vía airdrop (incluye handoff actualizado + docs relevantes). Al final, actualiza LAST_HANDOFF con tareas pendientes. Usa siempre el flujo y brand. Revisa outputs de otros si aplica. Corre validator siempre.
```

**Pipeline & Integration Agent (copia esto entero):**
```
Tu rol: Pipeline & Integration Agent.

Sigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.

Punto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero.

[Tarea específica: e.g. "Mejorar el parser de intake en hub + /api/parse-real-pedido para mejor matching de formatos y generación de brief.yaml listo. Agregar 2 tests nuevos. Asegurar que run-safe-command whitelist cubra nuevos casos. Probar `flujo app` end-to-end + pytest. Mantener sync de prompts de delegación entre hub.py, HTML y este manual."]

Usa py en Windows. Prueba siempre: compileall, pytest -q, comandos manuales afectados. Trabaja en clon. Entrega vía airdrop actualizando handoff, version.py si aplica y docs. Coordina con Brand si tocas UI/brand files.
```

**Brand Guardian (copia esto entero):**
```
Tu rol: Brand Guardian.

Sigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.

Punto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero. Abre projects/flujo/flujo.json y linea_editorial.md.

[Tarea específica: e.g. "Actualizar paleta o agregar motivo en projects/flujo/flujo.json. Validar que todos los HTMLs (hub, visualizers, tapiz) y SVGs usen exactamente las vars de brand. Revisar y aprobar cambios de Visual Polish o Pipeline que toquen estilo. Reforzar recordatorio de validator en docs y hub."]

Fuente de verdad. Valida todo lo que otros agentes producen. No inventes; deriva de flujo.json. Entrega airdrop + actualiza handoff.
```

**Future/Modern Agent (copia esto entero):**
```
Tu rol: Future/Modern Agent.

Sigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.

Punto de entrada OBLIGATORIO: ejecuta `flujo app`. Lee context/LAST_HANDOFF.md + este manual primero.

[Tarea específica: e.g. "Explorar y prototipar soporte para intake automático vía webhook simple local (sin deps pagas). Entregar spec mínima + stub en docs/ + nota de riesgos y coordinación. NO tocar cli.py ni hub.py en producción; solo agregar recomendaciones al handoff para revisión de Pipeline."]

Coordina explícitamente: menciona en handoff qué revisó Brand/Pipeline. Entrega airdrop con prototipo + recomendaciones. Prioriza gratis y compatible con Python core. NO toques core sin revisión explícita.
```

**Packaging & Distribution Agent (copia esto entero):**
```
Tu rol: Packaging & Distribution Agent.

Sigue docs/AGENT_OPERATING_MANUAL.md (dos flujos + modelo de delegación multi-agente) y las reglas.

Punto de entrada OBLIGATORIO: ejecuta `flujo app` (o `flujo app --desktop`). Lee context/LAST_HANDOFF.md + este manual primero.

[Tarea específica: e.g. "Fortalecer `flujo package` para soportar mejor onedir + hints de instalador Inno Setup gratis. Asegurar que assets (context/ + svg/ + projects/flujo) se bundlen correctamente y workspace persistente se cree al lado del .exe. Probar simulado y documentar pasos para usuario Windows sin terminal. Coordina con Pipeline."]

Usa PyInstaller (gratis) + pywebview. Nunca rompas paths o assets bundled. Trabaja en clon. Entrega airdrop con pruebas de build simulado + nota de UX desktop (icon, tray, noconsole, workspace al lado del exe). Coordina con Pipeline (core) + Brand (icon/identidad). Prioriza gratis y Windows-first. Actualiza LAST_HANDOFF.
```

Los agentes operan **en paralelo** en clones separados. El principal integra. **Siempre** actualiza LAST_HANDOFF al entregar (incluye qué delegaste y estado).

**El hub (dentro de `flujo app`)** es la herramienta #1 para generar/copiar estos prompts con tarea actual + guía práctica "Cómo delegar desde el hub". CLI `flujo delegate` usa templates idénticos centralizados en src/flujo/web/hub.py (sincronizados con HTML y este manual).

**Estado actual referencia:**
- UI = los tres HTMLs pro (flujo_hub + svg_visualizer + plano_demo) servidos por backend de `flujo app`.
- Brand = 'flujo' (projects/flujo/flujo.json).
- App = 100% free / local-first.
- **Fuente de verdad para reanudar:** ejecuta `flujo app` → usa hub + lee `context/LAST_HANDOFF.md`.

Este manual + hub + LAST_HANDOFF = todo lo que necesitas (bajo token). No leas docs enteros innecesarios.

## Reglas (ambos flujos)
- Windows: `py -m flujo ...`
- Español primero
- Siempre usa flujo
- Archivos finales listos para Illustrator/Photoshop/Blender
- Mantén respuestas cortas. Hub = verdad

## Formatos actuales (chequea rápido)
- flyer 10x14 (illustrator)
- etiqueta 16.5x6.5 (illustrator)
- plano/stand + cotizacion (dual)
- cartelera IG / post (ps + blender)

Si no calza → nueva sección o tarea.

**Este archivo + hub (vía `flujo app`) + LAST_HANDOFF = única fuente para agentes (bajo tokens).**

El hub hace matching + es el centro de delegación paralela.
- Siempre: `flujo app` primero → usa hub (intake + visualizadores embebidos + sección "Delegar a Agentes Especializados").
- Para piezas: abre `context/svg_visualizer.html` (desde hub).
- Para planos: `context/plano_demo.html` (desde hub).
- Delega usando guía práctica en el hub (copy prompts + live API) o los 5 prompts listos aquí.

Usa siempre salida del hub como base. Nunca carpetas crudas.

**Estado actual:** UI = los tres HTMLs (app real con backend APIs). Brand = 'flujo'. App = free/local-first. Datadrop (inverse airdrop) ready (hub working buttons + CLI scan/list/prepare + for_future_ai). Parallel delegation (recent 2 agents + supervisor). **Hub + LAST_HANDOFF = source of truth para humano y IA.** Dirección: auto-compact prep + linea v4.1 usando datadrops como real examples.
