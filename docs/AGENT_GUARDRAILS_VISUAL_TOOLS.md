# AGENT GUARDRAILS — Herramientas Visuales

**⚠️ OBLIGATORIO LEER ANTES DE TOCAR `plano_demo.html` O `svg_visualizer.html`**

## The 5-Question Rule

**No modificas nada hasta responder esto:**

```
[ ] 1. ¿Qué propósito tiene esta herramienta? (RIDER operativo / VISOR de diseños)
[ ] 2. ¿De qué documento base saca contenido? (Propuesta RD / BRIEF_SUPLEMENTOS_RD.md)
[ ] 3. ¿Quién la usa? (productores / diseñadores)
[ ] 4. ¿Qué ROM? (Lee: docs/HERRAMIENTAS_VISUALES.md)
[ ] 5. ¿Pasé pruebas? (navegación, zoom, descarga, responsividad)
```

Si NO puedes responder ≥3, **STOP. Lee primero.**

---

## Quick Reference

| Archivo | Propósito | Referencia | NO TOQUES |
|---|---|---|---|
| `plano_demo.html` | RIDER profesional RD EVENTOS | `Propuesta_Reduciendo_Dano.txt` | Estructura base HTML/JS |
| `svg_visualizer.html` | Visor SUPLEMENTOS diseños | `BRIEF_SUPLEMENTOS_RD.md` | Carga svg_index.json |

---

## Red Flags = STOP IMMEDIATELY

❌ Tocar HTML sin leer `docs/HERRAMIENTAS_VISUALES.md`  
❌ Cambiar referencias base sin documenting por qué  
❌ Eliminar secciones sin entender que rompe flujo  
❌ Commitear sin pasar navegador (zoom, búsqueda, modal, export)  
❌ Mergear a main sin pasar tests visuales locales  

---

## Before Commit Checklist

```bash
# 1. Abre en navegador (Ctrl+O → file:///path/to/context/xxx.html)
[ ] Navegación funciona (tabs, botones, links)
[ ] SVG/imágenes se ven sin distorsión
[ ] Responsive (achica ventana a 600px)
[ ] Zoom/búsqueda/filtros responden
[ ] Modal abre/cierra sin errores
[ ] Descarga funciona (no solo UI)

# 2. Code review
[ ] No hay console.error() (abre DevTools → Console)
[ ] CSS no entra en conflicto
[ ] No borraste referencias
[ ] Documentaste cambios en comentario commit

# 3. Commit message
git commit -m "improve: [HERRAMIENTA] [qué cambió]. Ref: docs/HERRAMIENTAS_VISUALES.md"

# 4. Si NO pasas este checklist = NO commitees
```

---

## Key URLs (Don't Change Without Permission)

```
plano_demo.html references:
  - Propuesta_Reduciendo_Dano.txt (contenido RD)
  - docs/RIDER_EVENTOS.md (estructura)
  - docs/RIDER_CHECKLIST.md (operativo)

svg_visualizer.html references:
  - BRIEF_SUPLEMENTOS_RD.md (estructura pedidos)
  - svg_index.json (datos, generado por scripts)
  - CATALOGO_FORMATOS.md (medidas)
```

Change = Read HERRAMIENTAS_VISUALES.md section 5 "Decisiones que requieren revisión explícita"

---

## Golden Rule

**RIDER es documento. VISUALIZER es galería.**

Si no entiendas la diferencia, relée esto 3 veces antes de tocar.

---

**Last Updated:** 2026-06-28  
**Version:** 1.0 (no negociable)
