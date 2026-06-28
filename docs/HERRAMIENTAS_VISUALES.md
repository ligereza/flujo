# Herramientas Visuales — Guardrails para Agentes

**⚠️ ANTES DE MODIFICAR CUALQUIER HERRAMIENTA VISUAL, LEE ESTE DOCUMENTO COMPLETO.**

---

## Tabla de referencia rápida

| **Archivo** | **Propósito** | **Usuarios** | **Referencia base** | **QUÉ MODIFICAR** | **QUÉ NO TOCAR** |
|---|---|---|---|---|---|
| `context/plano_demo.html` | **RIDER RD EVENTOS** profesional (requisitos + plano + checklist operativo) | Productoras de eventos, equipo RD logística | [docs/RIDER_EVENTOS.md](RIDER_EVENTOS.md) + [Propuesta_Reduciendo_Dano.txt](../datadrops/Propuesta_Reduciendo_Dano.txt) | Secciones de requerimientos, plano SVG, checklist, exportación PDF | Estructura base HTML/JS (a menos que haya spec explícita) |
| `context/svg_visualizer.html` | **Visor de Diseños SUPLEMENTOS** (etiquetas, flyers, diseños) | Equipo de diseño, tienda, redes sociales | [docs/BRIEF_SUPLEMENTOS_RD.md](BRIEF_SUPLEMENTOS_RD.md) | Búsqueda, filtros, presentación visual, zoom, exportación | Carga de SVG/índice (usa [svg_index.json](../svg_index.json) si lo cambias) |

---

## 1. RIDER RD EVENTOS (`context/plano_demo.html`)

### Propósito
Documento **profesional para productoras de eventos** que detalla qué necesita Reduciendo Daño para intervenir en terreno.

### Referencia base obligatoria
- [docs/RIDER_EVENTOS.md](RIDER_EVENTOS.md) — Estructura: página 1 (Requerimientos) + página 2 (Layout operativo)
- [docs/RIDER_CHECKLIST.md](RIDER_CHECKLIST.md) — Checklist operativo por área
- [datadrops/Propuesta_Reduciendo_Dano.txt](../datadrops/Propuesta_Reduciendo_Dano.txt) — Contenido RD: quiénes somos, objetivo, modalidades (Stand Informativo, Stand Testeo, Contención), coordinación, beneficios, costos

### Estructura esperada

**Página 1: Requerimientos operativos**
```
- Espacio (medidas int/ext, tipo de terreno)
- Infraestructura (toldo, mesas, sillas, rack, señalética)
- Servicios necesarios (electricidad, agua, luz, calefacción)
- Coordinación con producción (seguridad privada, equipo médico, alimentación)
- Equipo requerido por modalidad (testeo, contención, coordinación)
- Cantidad estimada de voluntarios
```

**Página 2: Layout operativo**
```
- Plano visual del stand (SVG generado o insertado)
- Distribución de mobiliario
- Circulación de público
- Zonas de testeo/contención/coordinación
```

### Estándares visuales (CSS interno)
```
Paleta: ink #1f2a24 | accent #2d5a4a | paper #f8f1e3 | support #675f55 | alert #c2410f
Tipografía: Inter, sans-serif
Escala: h1 1.8rem | h2 1.4rem | body 1rem | small 0.85rem
Layout: márgenes 15%, bloques modulares, altura línea 1.5
```

### QUÉ SE PUEDE MODIFICAR
✅ Agregar secciones de requerimientos  
✅ Mejorar presentación de datos operativos  
✅ Actualizar plano SVG o insertar nuevo  
✅ Agregar exportación (PDF, descarga)  
✅ Mejorar responsividad  

### QUÉ NO SE TOCA
❌ Referencia de Propuesta_Reduciendo_Dano.txt (es fuente de verdad)  
❌ Estructura base de requerimientos operativos  
❌ Colores CSS (mantén consistencia)  
❌ Eliminar secciones sin documentar por qué  

### Regla de oro
**Si no has leído `RIDER_EVENTOS.md` + `RIDER_CHECKLIST.md` + `Propuesta_Reduciendo_Dano.txt`, NO TOQUES ESTE ARCHIVO.**

---

## 2. Visor de Diseños SUPLEMENTOS (`context/svg_visualizer.html`)

### Propósito
**Galería visual profesional** que muestra diseños (SVGs, imágenes) de suplementos: etiquetas, flyers, pendones, logos, stickers.

### Referencia base obligatoria
- [docs/BRIEF_SUPLEMENTOS_RD.md](BRIEF_SUPLEMENTOS_RD.md) — Estructura de pedidos: pieza (etiqueta, flyer, etc) + tipo (nuevo/mod/corrección) + producto + objetivo + texto + imagen + medida
- [docs/CATALOGO_FORMATOS.md](CATALOGO_FORMATOS.md) — Formatos y dimensiones exactas

### Estructura esperada

**Elementos obligatorios**
```
- Búsqueda por nombre/tipo
- Filtros: por categoría (etiqueta, flyer, pendón, etc)
- Gallería con previsualización en tarjetas
- Modal/vista detalle: título, meta (tipo/medida), vista completa, opciones descarga
- Zoom/presets (100%, fit, pantalla completa)
```

**Datos por pieza**
```
- Nombre del SVG/diseño
- Tipo (etiqueta, flyer, pendón, sticker, logo)
- Producto/línea
- Medidas
- Colores dominantes (opcional)
- Última modificación
```

### Estándares visuales (CSS interno)
```
Paleta: ink #1f2a24 | accent #2d5a4a | paper #f8f1e3 | support #675f55 | alert #c2410f
Tipografía: Inter, sans-serif
+ Énfasis en: buena visualización del SVG (sin distorsión), zoom suave, cards claras
```

### QUÉ SE PUEDE MODIFICAR
✅ UI/UX de búsqueda y filtros  
✅ Presentación de tarjetas (cards, grid)  
✅ Opciones de zoom/vista  
✅ Mejorar modal de detalle  
✅ Agregar exportación (descarga SVG, PNG, etc)  
✅ Agregar metadatos (colores, medidas, producto)  

### QUÉ NO SE TOCA
❌ Carga de datos (viene de `svg_index.json` generado por `py scripts/generate_svg_index.py`)  
❌ Si tocas cómo se cargan los SVGs, coordina con el script de indexación  
❌ Colores CSS (mantén consistencia)  
❌ Eliminar secciones sin documentar  

### Regla de oro
**Si no has leído `BRIEF_SUPLEMENTOS_RD.md` + `CATALOGO_FORMATOS.md`, NO TOQUES ESTE ARCHIVO.**

---

## 3. Diferencias clave

| Aspecto | RIDER RD EVENTOS | VISOR SUPLEMENTOS |
|---|---|---|
| **Tipo de contenido** | Documento operativo estructurado (texto + plano) | Galería visual de diseños |
| **Usuarios** | Productoras, equipo logístico RD | Diseñadores, tienda, redes |
| **Énfasis** | Información, coordinación, checklist | Presentación visual, calidad, accesibilidad |
| **Actualización** | Manual (edición de secciones) | Automática (desde índice svg_index.json) |
| **Exportación** | PDF (documento completo) | SVG/PNG (pieza individual) |

---

## 4. Guardails explícitos para agentes

### Antes de tocar `plano_demo.html`:
```
[ ] He leído docs/RIDER_EVENTOS.md
[ ] He leído docs/RIDER_CHECKLIST.md
[ ] He leído datadrops/Propuesta_Reduciendo_Dano.txt (entiendo el contexto RD)
[ ] Entiendo que esto es un documento **operativo**, no un visor
[ ] Sé exactamente qué sección/dato voy a modificar
[ ] He verificado que no rompe estructura de requerimientos
[ ] Testé en navegador (responsividad, lectura, exportación si la hay)
```

### Antes de tocar `svg_visualizer.html`:
```
[ ] He leído docs/BRIEF_SUPLEMENTOS_RD.md
[ ] He leído docs/CATALOGO_FORMATOS.md
[ ] Entiendo que la galería debe verse **bien presentada** (no fea/pixelada)
[ ] He verificado que los SVGs se cargan desde svg_index.json correctamente
[ ] Sé exactamente qué feature UI voy a agregar o mejorar
[ ] Testé: búsqueda, filtros, zoom, modal, descarga
[ ] El diseño mantiene brand flujo.json (colores, tipografía)
```

---

## 5. Decisiones que requieren revisión explícita

❌ **Cambiar estructura/referencia base** (ej: otro documento que no sea Propuesta_Reduciendo_Dano.txt)  
❌ **Eliminar secciones** sin documentar el motivo  
❌ **Cambiar colores CSS** sin justificación (mantén consistencia)  
❌ **Modificar carga de datos** (si el sv_visualizer tira de otro índice, documenta)  
❌ **Cambios mayores de layout** sin spec previa  

**Para cualquiera de estos, requiere aprobación antes.**

---

## 6. Links de referencia rápida

- **RIDER estructura:** [docs/RIDER_EVENTOS.md](RIDER_EVENTOS.md)
- **RIDER checklist:** [docs/RIDER_CHECKLIST.md](RIDER_CHECKLIST.md)
- **Propuesta RD (contenido):** [datadrops/Propuesta_Reduciendo_Dano.txt](../datadrops/Propuesta_Reduciendo_Dano.txt)
- **Suplementos brief:** [docs/BRIEF_SUPLEMENTOS_RD.md](BRIEF_SUPLEMENTOS_RD.md)
- **Formatos:** [docs/CATALOGO_FORMATOS.md](CATALOGO_FORMATOS.md)
- **Índice SVG:** [svg_index.json](../svg_index.json)

---

## 7. Preguntas antes de modificar

**Siempre responde esto antes de tocar:**

1. ¿Cuál es el propósito de mi cambio? (describe en 1-2 líneas)
2. ¿Cuál es la referencia que lo justifica? (línk a doc/spec)
3. ¿A quién le sirve? (productor/diseñador/jefe?)
4. ¿Rompe algo existente? (verifica navegación, carga, exportación)
5. ¿Está alineado con el CSS existente? (colores, tipografía, espaciado)

Si no puedes responder 3+ preguntas, **lee primero, modifica después.**

---

## Status actual (2026-06-28)

- ✅ `plano_demo.html` existe pero necesita contenido RD explícito basado en Propuesta
- ✅ `svg_visualizer.html` existe pero UI/CSS necesita mejora visual profesional
- ⏳ Ambos necesitan pasada de brand flujo.json (colores, tipografía)
- ⏳ Documentación guardail lista (este archivo)

**Próximas modificaciones deben:**
1. Leer este doc completo
2. Responder las 5 preguntas
3. Documentar cambios en HANDOFF

---

**Última actualización:** 2026-06-28  
**Versión:** 1.0 (guardrail inicial)
