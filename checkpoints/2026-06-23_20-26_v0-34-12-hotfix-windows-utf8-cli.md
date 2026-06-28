# Checkpoint — v0.34.12 - hotfix windows utf8 cli

Fecha: 2026-06-23_20-26

## Estado

﻿# LAST_HANDOFF â€” flujo (Single Source of Truth para continuaciÃ³n)

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
  - 
... (truncado para checkpoint)

## Cambios realizados

-

## Próximo paso

-
