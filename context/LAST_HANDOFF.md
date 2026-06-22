# LAST_HANDOFF â€” flujo (Single Source of Truth para continuaciÃ³n)

**IMPORTANTE PARA AHORRO DE TOKENS:**
Esta es la **Ãºnica** pieza de estado que una IA nueva (o sesiÃ³n nueva) **debe** leer despuÃ©s de PARA_IA_CONTEXT.md cuando los tokens son limitados.

Mantener este archivo **corto** (< 120 lÃ­neas ideal, < 180 mÃ¡ximo). Actualizar **siempre** antes de terminar una sesiÃ³n o entregar un airdrop.

---

**Fecha:** 2026-06-22
**VersiÃ³n actual:** 0.34.10
**Ãšltima sesiÃ³n (HTML â†’ App real + delegaciÃ³n multi-agente, preservando workflow):**
- **Estado actual (crÃ­tico para reanudaciÃ³n):** `flujo app` (o `flujo app --desktop`) es la **Ãºnica entrada diaria obligatoria**. Lanza servidor + backend real + sirve los tres HTMLs como UI de la app:
  - `context/flujo_hub.html` = workspace principal pro (intake con parse real, live jobs/SVG/brand, Brand Validator, secciÃ³n de delegaciÃ³n, export, comandos).
  - `context/svg_visualizer.html` + `context/plano_demo.html` = visualizadores embebidos (grupos exactos de /svg, "Vista grande", brand enforced).
- Cuando `flujo app` estÃ¡ activo: APIs reales (/api/parse-real-pedido, /api/create-job-draft, /api/list-jobs, /api/list-svg-works, /api/delegate, /api/export-tokens, SSE live, brand desde projects/flujo/flujo.json).
- HTML directo (sin server): fallback 100% funcional con parsers locales y datos estÃ¡ticos.
- Packaging: `flujo package` genera .exe standalone (PyInstaller + pywebview) que lanza directo en modo desktop con tÃ­tulo "flujo â€¢ Workspace", icono pro, assets embebidos, workspace persistente junto al .exe.
- Brand enforcement: todo visual deriva de projects/flujo/flujo.json (ink/accent/paper exactos). Hub tiene "Brand Validator" + "FORZAR GUARD" + recordatorios obligatorios antes de export. Tapiz ahora usa "flujo" por defecto y se ve premium (no experimental).
- DelegaciÃ³n multi-agente paralela: 5 roles (Visual Polish, Pipeline & Integration, Brand Guardian, Future/Modern, **Packaging & Distribution**).
  - GuÃ­a prÃ¡ctica + multi-select + "Copiar prompt completo" + "Delegar seleccionados (live /api)" dentro del hub.
  - Prompts listos (centralizados en hub.py + AGENT_OPERATING_MANUAL) incluyen siempre: `flujo app` primero + LAST_HANDOFF + coordinaciÃ³n.
  - Sub-agentes corren en clones separados â†’ airdrops independientes â†’ principal integra y actualiza LAST_HANDOFF.

**Fuente de verdad para reanudaciÃ³n:** ejecuta `flujo app` â†’ abre hub â†’ lee esta secciÃ³n + usa el hub. No leas todo el repo. Workflow intacto: pedido â†’ hub (intake real + job draft) â†’ visualizadores â†’ export. DelegaciÃ³n desde el hub mismo.

**Preservado para otra IA:**
- `flujo app` como entrada Ãºnica.
- Estructura clara: HTMLs = UI, backend en hub.py = APIs reales, todo usa herramientas existentes (intake, jobs, brand, render, etc.).
- DelegaciÃ³n explÃ­cita y accionable.
- Todo gratis (pywebview, PyInstaller, stdlib server).

## Objetivo actual / tarea en curso
Fortalecer los dos flujos de agentes:
1. Pedido reciente + repo â†’ procesar con herramientas y decidir si usar formato existente o proponer nuevo.
2. Repo completo â†’ continuar mejoras (priorizando integraciÃ³n con AI/PS/Blender y soporte a agentes).

## Estado del mundo (crÃ­tico)
- **Activo:** `flujo app` lanza app real. UI = tres HTMLs servidos (flujo_hub.html = main workspace pro; svg_visualizer.html y plano_demo.html = visualizadores embebidos por grupos reales). Backend: APIs reales + SSE + delegate.
- **App transition:** HTMLs + backend = app completa. Fallback directo HTMLs = usable. Packaging (`flujo package`) produce .exe desktop standalone.
- **Salud:** OK.
- **Clave:** Ejecuta **siempre** `flujo app` primero (Ãºnica entrada diaria). Usa hub como workspace (intake + delegar + visual + live). Para continuar: LAST_HANDOFF + hub. Windows `py`. DelegaciÃ³n paralela a 5 roles (incl. Packaging) con prompts listos y live API en el hub. Ver docs/AGENT_OPERATING_MANUAL.md. Brand enforcement obligatorio.

## QuÃ© NO estÃ¡ hecho / bloqueos / riesgos
- `flujo intake json` sigue pendiente (schema existe, implementaciÃ³n completa no).
- Motor de planos mejorado pero aÃºn limitado (grid bÃ¡sico; falta integrar primitives schema a fondo).
- LAST_HANDOFF es manual + auto-append bÃ¡sico; se puede hacer mÃ¡s inteligente (diff summary).
- RecepciÃ³n automÃ¡tica (IMAP/webhook) no implementada.

## Tareas simples para agentes (low token - una por vez)
**Recientes / Estado App + DelegaciÃ³n (prioridad alta, para reanudaciÃ³n fÃ¡cil):**
- Ejecuta **siempre primero** `flujo app` (o --desktop). Esto es la entrada diaria Ãºnica.
- En el hub: prueba Intake (pega pedido real â†’ usa backend real para parse + "Crear job draft real").
- Prueba visualizadores (desde el hub) + Brand Validator ("VALIDAR BRAND AHORA" antes de cualquier cosa).
- Prueba secciÃ³n Delegar: usa los prompts listos para 2+ roles en paralelo (incl. Packaging). Los prompts ya incluyen "ejecuta `flujo app` + LAST_HANDOFF".
- Corre `flujo package` si quieres probar el .exe.
- Al terminar: actualiza **solo** esta secciÃ³n + cualquier doc relevante. MantÃ©n el flujo intacto para la prÃ³xima IA.

**Regla de oro para reanudaciÃ³n:** `flujo app` â†’ hub â†’ LAST_HANDOFF. No leas todo. El hub + esta secciÃ³n contienen todo lo necesario.

**Para Flujo Pedido:**
- Intake real + match formatos + comando.
- Si no calza: propone secciÃ³n o tarea en LAST_HANDOFF.

**Para Flujo Mejoras:**
- Lanza delegaciÃ³n real (desde hub) a 1-2 roles paralelos (usa clones o simula).
- Actualiza prompts si desincronizados (central en hub.py).
- Prueba `flujo package` / desktop (si deps).
- Actualiza siempre este LAST_HANDOFF al final.

**General:**
- Prueba export tokens + SSE live + Brand Validator desde hub.
- Agrega ejemplo en projects/flujo/.
- MantÃ©n docs alineadas al estado: HTMLs=UI, `flujo app` = entrada, 5 roles de delegaciÃ³n.

## PrÃ³ximas (prioridad para agentes)
1. Usar hub para delegaciÃ³n paralela real: e.g. delegar "pulir..." a Visual + "mejorar packaging..." a Packaging + integrar airdrops.
2. Verificar que la guÃ­a "CÃ³mo delegar desde el hub" + prompts (5 roles) son claros y usables por humano y futuras IAs.
3. Mejorar matching intake o parser (si aplica).
4. Probar `flujo app --desktop` + `flujo package` end-to-end (si deps).
5. Mantener sincronizados los templates de prompts (hub.py fuente).
6. Actualizar LAST_HANDOFF + docs siempre.

## CÃ³mo verificar rÃ¡pido el estado
```bash

## Resumen sesión actual (max agents paralelo - 2026-06-22)

**Avances recientes:**
- Datadrop (airdrop inverso) MVP completo y funcional en hub + CLI: drop a `datadrops/incoming/`, "Escanear incoming" o `flujo datadrop scan` procesa todos los archivos, genera dated dirs + rich manifests (palette, OCR, visual_traits, for_future_ai).
- Botones Datadrop: header link ahora abre Herramientas tab + scrollea a sección de forma robusta (showTab + rAF scroll + listeners + preventDefault). Modal cierra bien.
- Delegación paralela maximizada: usamos 8-10+ subagentes en paralelo para esta tarea (editores de READMEs por área, advances-prep, limpieza, git-push, verify, coordinator/supervisor, etc.).
- `flujo app` + launchers root como entrada única. Hub tabs + Brand + LAST_HANDOFF.
- Limpieza rápida por agente dedicado: pruned ~140+ pyc/__pycache__, incoming vacio, .pytest_cache, stale ig; actualizado .gitignore con reglas selectivas (ignora incoming + imágenes; conserva manifests json y _review_package.txt).

**Hacia dónde vamos:**
- Auto-compact de sesiones (preparado con parallel delegation + LAST_HANDOFF como fuente única de verdad).
- Integración linea_editorial/v4.1 usando datadrops reales como ground-truth (paletas, traits, OCR de entregas).
- Daily workflow 100% vía `flujo app` → hub (intake + datadrop + delegate + jobs + prepare).
- Packaging .exe + más paths robustos.

**Acciones en esta sesión:**
- Max parallel agents para actualizar TODOS los READMEs explicando avances + dirección.
- Commit + push verificado (b558dae en remote).
- Quick limpieza + .gitignore limpio.
- AVANCES_BLOCK.txt generado y referenciado.
- LAST_HANDOFF compactado (solo esencial + resumen reciente).

**Regla:** Siempre `flujo app` primero. Lee este LAST_HANDOFF + hub. Actualiza solo esta sección al final. Mantén <150 líneas.

**Fuente de verdad:** `flujo app` → hub → LAST_HANDOFF.md
