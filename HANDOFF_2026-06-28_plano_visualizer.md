# HANDOFF 2026-06-28 — Plano & Visualizer RD v0.36

**Completado hoy:**
- ✅ Reescritura `plano_demo.html` (15.6 KB) — Intervención RD, no evento interno
  - Layout 2-columnas mantiene original
  - Checkboxes simples: testeo químico, zona contención
  - SVG: Stand Informativo + Testeo + Contención (opcional)
  - Tabs: Plano / Rider operativo / Costos
  
- ✅ Reescritura `svg_visualizer.html` (15.2 KB) — Material RD, no planificación
  - Grid responsive + modal + filtros
  - Categorías: Flyers educativos, Riders operativos, Señalización, Suplementos
  - 14 items de ejemplo (RD materials para intervenciones en eventos)
  
- ✅ Skill documentada: `verify-user-intent-first`
  - Error: Interpretación errada (ONG vs event planner)
  - Lección: Verificar intención antes de implementar
  - Ratio costo: 17:1 (redo vs. prevención)

**PENDIENTE / TODO:**
- [ ] **Contenido SVG real**: Archivos de ejemplo en `../svg/` están vacíos. Necesita:
  - `svg/rd/flyer/*.svg` — Flyers educativos reales (diseño RD 2023)
  - `svg/rd/rider/*.pdf` o `.svg` — Riders operativos
  - `svg/rd/signage/*.svg` — Afiches/señalización
  - `svg/rd/suplemento/*.svg` — Fichas por droga
  
- [ ] **Backend de Material**: `svg_visualizer.html` usa data local (hardcoded). Necesita:
  - Servicio que escanee `../svg/rd/` y exporte JSON
  - Endpoint `/api/materials` → Listar dinámicamente
  - Soporte descarga real (ahora es mock `alert()`)

- [ ] **Testing plano_demo.html**:
  - Verificar SVG genera correctamente con diferentes valores
  - Probar checkboxes: incluye_testeo, incluye_contension
  - Validar rider/costos generan texto correcto

- [ ] **Integración hub**: Asegurar links en `flujo_hub.html` apunten a archivos correctos
  - plano_demo.html disponible
  - svg_visualizer.html disponible
  - Breadcrumb "← Hub" funcional

- [ ] **Limpieza técnica**:
  - Remover backups: `plano_demo_old.html`, `plano_demo_backup*.html`, `svg_visualizer_old.html`, etc.
  - Mantener solo archivos actuales en `context/`

**ESTADO CORRECTO:**
- Ambos archivos interpretan RD correctamente (ONG interventora, no organizadora)
- UI simplificada: checkboxes, sin detalles roles
- Estructura mantiene original (2-col layout, tabs, grid+modal)
- Listo para ser refinado con contenido real

**PRÓXIMO AGENTE:**
- [ ] Llenar `svg/rd/` con material RD actual (scan creativo/operativo)
- [ ] Conectar backend JSON para material dinámico
- [ ] Testing UI: plano_demo con valores variados
- [ ] Limpiar backups, confirmar hub links
- [ ] Deploy a staging si existe

**BRANCH**: main | **COMMIT**: Plano & Visualizer RD reescritura (v0.36)
