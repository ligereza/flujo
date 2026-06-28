# TODO - Contraportadas Suplementos RD

**Fecha:** 2026-06-28  
**Estado:** En progreso → Listo para continuar  
**Prioridad:** ALTA

---

## ✅ Completado esta sesión

1. **Base SVG contraportada 10x14cm**
   - Archivo: `svg/suplementos_rd/04_contraportadas/01_contraportada_base_10x14cm.svg`
   - Estilo: Adaptado a referencia Canva + datadrop flyer real
   - Estructura: Bloque descripción + información nutricional + CTA/WhatsApp/QR

2. **Bridge Illustrator con mesas de trabajo**
   - Archivo: `src/flujo/export/illustrator_bridge.py`
   - Nueva función: `build_illustrator_artboards_payload()` + `write_illustrator_artboards()`
   - Tests pasando: `test_illustrator_bridge.py` (2/2 ✓)

3. **Script JSX con todos los suplementos**
   - Spec: `svg/suplementos_rd/04_contraportadas/suplementos_rd_illustrator_spec.json` (7 suplementos)
   - Script: `svg/suplementos_rd/04_contraportadas/suplementos_rd_illustrator_artboards.jsx`
   - Estructura: Mesas de trabajo automáticas por suplemento

---

## 🚀 Tareas pendientes (Prioridad)

### CRÍTICO (Cierra el flujo app-driven)

**1. Automatizar job → contraportada en hub**
   - Ubicación: `src/flujo/web/hub.py` 
   - Qué hacer: 
     - Cuando se crea un job area=suplementos, generar automáticamente la contraportada SVG
     - Basarse en el brief/pedido del job para llenar texto
     - Guardar en `jobs/{job_id}/flows/contraportada.svg`
   - Tiempo estimado: 30 min
   - Impacto: Usuario crea pedido en hub → contraportada lista, sin tocar CLI

**2. CLI simple para suplementos contraportada**
   - Ubicación: `src/flujo/cli.py`, nuevo comando bajo `@app.command()`
   - Comando: `flujo suplementos contraportada "Impulso" --brief "texto" --output salida.svg`
   - Qué hace: lee spec JSON, reemplaza placeholders, genera SVG
   - Tiempo estimado: 20 min
   - Fallback si hub no está disponible

---

### IMPORTANTE (Operativo + docs)

**3. README contraportadas operativo**
   - Archivo nuevo: `docs/CONTRAPORTADAS_SUPLEMENTOS_OPERATIVO.md`
   - Contenido:
     - Cómo modificar en Illustrator (quick guide)
     - Cómo exportar a PDF/PNG
     - Checklist pre-impresión (resolución, colores, márgenes)
     - Dónde guardar versión final (jobs/[id]/exports/)
   - Tiempo estimado: 20 min
   - Para: Cualquiera pueda hacer el resto sin contexto

**4. Integración linea_editorial v4.1**
   - Ubicación: `linea_editorial/v4.1.md`, sección § Contraportadas
   - Qué agregar:
     - Pautas de aire/márgenes validadas en contraportadas reales
     - Checklist de validación (contraste, legibilidad, paleta)
     - Notas de tolerancia vs ideal
   - Tiempo estimado: 15 min
   - Para: QA automático cuando se generan

---

### OPCIONAL (Polish)

**5. Comando de validación contraportadas**
   - `flujo validate contraportadas svg/suplementos_rd/04_contraportadas/`
   - Valida contra linea_editorial v4.1
   - Genera reporte: colores OK, air OK, tipografía OK

**6. Exportar contraportadas a PDF multi-página**
   - Script: `scripts/export_contraportadas_pdf.py`
   - Entrada: spec JSON
   - Salida: PDF con una página por suplemento

---

## 📝 Arquivos clave

| Ruta | Descripción |
|------|-------------|
| `svg/suplementos_rd/04_contraportadas/` | Folder central contraportadas |
| `svg/suplementos_rd/04_contraportadas/01_contraportada_base_10x14cm.svg` | Base editable |
| `svg/suplementos_rd/04_contraportadas/suplementos_rd_illustrator_spec.json` | Spec JSON con todos los suplementos |
| `svg/suplementos_rd/04_contraportadas/suplementos_rd_illustrator_artboards.jsx` | Script JSX listo para Illustrator |
| `src/flujo/export/illustrator_bridge.py` | Bridge core (actualizado) |
| `src/flujo/export/__init__.py` | Exports (actualizado) |
| `tests/test_illustrator_bridge.py` | Tests (2/2 passing) |

---

## 🔧 Cómo continuar (Para next agent)

1. **Haz las tareas CRÍTICAS primero** (1 y 2)
   ```bash
   # Test que todo siga OK
   pytest -q tests/test_illustrator_bridge.py
   ```

2. **Luego IMPORTANTE** (3 y 4)

3. **Commit y push:**
   ```bash
   git add svg/suplementos_rd/04_contraportadas/ src/flujo/export/ docs/ tests/
   git commit -m "feat: contraportadas suplementos con bridge Illustrator multidestino"
   git push
   ```

4. **Update LAST_HANDOFF.md** con sección nueva:
   ```
   ### v0.35.X - Contraportadas Suplementos RD
   - Implemented SVG back covers for flyer 10x14cm format.
   - Added Illustrator bridge with artboard-per-supplement script.
   - Base style adapted from real datadrop reference.
   - Automation pending: job→contraportada generation in hub.
   ```

---

## 💡 Notas para next session

- El spec JSON es source of truth → cualquier cambio de texto/beneficio, editalo ahí
- El bridge JSX es generado → no editarlo directo, cambiar spec JSON y regenerar
- La base SVG es editable en cualquier app → guardar versión si hay customización
- El flujo debería quedar: pedido en hub → contraportada auto-generada → usuario edita en Illustrator si quiere → exporta a PDF
- Integración con datadrops: cuando suban una contraportada realizada, guardarla en manifest con OCR/paleta (para validación futura)

---

## ⚠️ Bloqueadores

Ninguno actualmente. Todo está listo para continuación sin dependencies externas.

---

**Próxima sesión:** Start with Tarea CRÍTICO #1 (hub automation).
