# Intake por JSON — Especificación para colegas y agentes

**Versión del esquema:** `1.0`
**Estado:** estructura definida, validable y consumible por CLI. El comando
activo es `flujo intake json <archivo.json>`: valida contra el schema, crea job,
`brief.yaml`, `estado.md` y acuse `resultado.md`.

---

## 1. Por qué JSON

Hoy los pedidos llegan como texto libre (correo/WhatsApp) y el sistema **adivina**
tipo, medidas y contenido con heurísticas. Eso falla cuando el colega olvida la
medida o describe ambiguo.

Con un **JSON estructurado**, el colega entrega exactamente lo que el sistema
necesita: tipo de pieza, formato, medidas, contenido por campos, y entrega
esperada. Beneficios:

- **Cero ambigüedad** → menos idas y vueltas.
- **Acuse de recibo automático** → el dueño no tiene que responder "lo vi".
- **Validación inmediata** → si falta algo crítico, se rechaza con un mensaje
  claro antes de llegar al dueño.
- **Independiente del canal** → da igual si el JSON llega por correo, formulario
  o WhatsApp; el sistema solo consume el JSON.

---

## 2. Estructura base (común a todos los formatos)

```json
{
  "intake_version": "1.0",
  "pedido": {
    "id_externo": "string (folio del colega, opcional)",
    "solicitante": {
      "nombre": "string",
      "canal": "correo | whatsapp | instagram | formulario | otro",
      "contacto": "string (email/teléfono, opcional)"
    },
    "tipo_pieza": "etiqueta | flyer | one_page | carrusel | rider | sticker | tarjeta | pendon",
    "formato_sugerido": "id del catálogo (opcional; si falta se infiere por medidas/tipo)",
    "medidas": {
      "ancho_cm": 0,
      "alto_cm": 0,
      "orientacion": "horizontal | vertical | cuadrado",
      "sangrado_mm": 0,
      "area_segura_mm": 0
    },
    "productos": ["string"],
    "contenido": {
      "titulo": "string",
      "subtitulo": "string",
      "cuerpo": "string",
      "llamado_accion": "string (opcional)",
      "extras": { "clave": "valor" }
    },
    "marca": {
      "nombre": "string",
      "web": "string (opcional)",
      "paleta_preferida": ["#RRGGBB"],
      "logo_adjunto": "string (nombre de archivo, opcional)"
    },
    "entrega": {
      "formatos": ["editable_svg", "vectorizado_svg", "pdf_impresion", "zip"],
      "fecha_limite": "YYYY-MM-DD (opcional)",
      "destino": "imprenta | digital | ambos"
    },
    "restricciones": {
      "no_inventar_claims": true,
      "texto_vectorizado": true,
      "editable_para_illustrator": true
    },
    "notas": "string libre (opcional)"
  }
}
```

### Campos mínimos obligatorios
- `intake_version`
- `pedido.tipo_pieza`
- `pedido.contenido.titulo`
- **Medidas O formato:** al menos uno de `pedido.formato_sugerido` **o**
  (`pedido.medidas.ancho_cm` + `pedido.medidas.alto_cm`).

Todo lo demás es opcional pero recomendado. Cuanto más completo, menos preguntas.

### Mapeo al modelo interno
El JSON se traduce directamente al `Brief` (`src/flujo/jobs/brief.py`):

| JSON | Brief |
|---|---|
| `pedido.tipo_pieza` | `tipo_pieza` |
| `pedido.formato_sugerido` | `posibles_formatos[]` |
| `pedido.medidas.*` | `medidas.*` |
| `pedido.productos` | `productos[]` |
| `pedido.contenido.*` | `contenido.notas` + elementos del `config.json` |
| `pedido.entrega.formatos` | `entrega.{editable_svg, vectorizado_svg, pdf_impresion, zip}` |
| `pedido.restricciones.*` | `restricciones.*` |

---

## 3. Estructura específica por formato

Cada tipo de pieza tiene campos de `contenido` propios. Esto es lo que cambia
entre un flyer y una etiqueta. El `formato_sugerido` debe ser un `id` válido del
catálogo (ver tabla en README o `flujo render formats`).

### 3.1 Etiqueta (`tipo_pieza: "etiqueta"`)
Formato típico: `etiqueta_horizontal_165x65` (16.5 × 6.5 cm) o
`etiqueta_horizontal_140x100` (14 × 10 cm).

```json
"contenido": {
  "titulo": "NOMBRE DEL PRODUCTO",
  "subtitulo": "Descripción corta / variedad",
  "cuerpo": "Información principal (ingredientes, uso, etc.)",
  "extras": {
    "lote": "L-2026-06",
    "vencimiento": "2027-06",
    "contenido_neto": "500g",
    "qr": "https://...",
    "codigo_barras": "7800000000000",
    "registro_sanitario": "RS-12345 (si aplica)"
  }
}
```
> ⚠️ Si `notas` o `cuerpo` mencionan salud, la pieza activa
> `restricciones.no_inventar_claims` y privacy puede marcar riesgo. No inventar
> propiedades medicinales.

### 3.2 Flyer (`tipo_pieza: "flyer"`)
Formato típico: `flyer_horizontal_minimo` (14 × 10 cm).

```json
"contenido": {
  "titulo": "NOMBRE DEL EVENTO",
  "subtitulo": "Bajada / lema",
  "cuerpo": "Descripción del evento",
  "llamado_accion": "Compra tus entradas en...",
  "extras": {
    "fecha": "2026-07-12",
    "hora": "21:00",
    "lugar": "Teatro X",
    "direccion": "Calle 123",
    "precio": "$10.000",
    "redes": "@cuenta",
    "auspiciadores": ["Marca A", "Marca B"]
  }
}
```

### 3.3 One-page / Dossier (`tipo_pieza: "one_page"`)
Formato típico: `one_page_propuesta_a4` (21 × 29.7 cm, A4 vertical).

```json
"contenido": {
  "titulo": "Propuesta de servicio",
  "subtitulo": "Para [Cliente]",
  "cuerpo": "Resumen ejecutivo",
  "extras": {
    "secciones": [
      { "encabezado": "Qué ofrecemos", "texto": "..." },
      { "encabezado": "Cómo trabajamos", "texto": "..." },
      { "encabezado": "Inversión", "texto": "..." }
    ],
    "contacto": "nombre / email / teléfono"
  }
}
```

### 3.4 Carrusel Instagram (`tipo_pieza: "carrusel"`)
Formato típico: `carrusel_cuadrado_1080` (1080 × 1080 px). Es **multi-slide**.

```json
"contenido": {
  "titulo": "Tema del carrusel",
  "extras": {
    "slides": [
      { "n": 1, "titulo": "Gancho", "texto": "..." },
      { "n": 2, "titulo": "Punto 1", "texto": "..." },
      { "n": 3, "titulo": "Cierre", "texto": "...", "cta": "Sígueme" }
    ]
  }
}
```
> Cada slide se mapea a un `document` dentro del `config.json`.

### 3.5 Rider de evento (`tipo_pieza: "rider"`)
Formato típico: `rider_eventos_a4_horizontal` (29.7 × 21 cm, A4 horizontal).

```json
"contenido": {
  "titulo": "Rider técnico — [Evento]",
  "extras": {
    "evento": "Nombre",
    "fecha": "2026-08-01",
    "lugar": "Locación",
    "requerimientos": ["Toldo 3x3", "Mesa", "Conexión 220v"],
    "plano_operativo": "Descripción o referencia del layout",
    "responsable": "nombre / contacto"
  }
}
```

### 3.6 Otros (`sticker`, `tarjeta`, `pendon`)
Aún no tienen plantilla dedicada en el catálogo. Se aceptan en el intake con
`medidas` explícitas; el sistema genera una base proporcional universal.
Medidas de referencia (heurística en `intake/pipeline.py`):
- `sticker`: 10 × 10 cm · `tarjeta`: 9 × 5 cm · `pendon`: medida explícita.

---

## 3.7 Pedidos de MODIFICACIÓN (bloque `modificacion`)

Cuando el pedido no es nuevo sino un **cambio sobre una pieza existente**
(la queja típica: *"cámbiame la proporción"* o *"se ve pixelado"*), se incluye
el bloque opcional `pedido.modificacion`. Su presencia hace que `tipo_pieza` y
`contenido.titulo` basten como mínimos (no hace falta repetir medidas/formato).

```json
"modificacion": {
  "pieza_existente": "projects/piezas_vectoriales/<slug>/config.json",
  "tipo_cambio": ["proporcion", "resolucion"],
  "proporcion": { "ancho_cm": 14, "alto_cm": 10 },
  "resolucion": { "dpi": 300, "motivo": "se veía pixelado en la imprenta" },
  "detalle": "Texto libre con la instrucción."
}
```

`tipo_cambio` admite: `proporcion | resolucion | texto | color | imagen | otro`.

### Cómo se resuelve cada cambio (importante)

| tipo_cambio | Qué es | Cómo lo resuelve flujo |
|---|---|---|
| `proporcion` | Cambiar la medida/aspecto (ej. 16.5×6.5 → 14×10) | `flujo render rescale <config> -w 14 -h 10`. Recalcula el canvas px. **No reposiciona los elementos** (cambiar proporción deforma el encuadre): hay que reacomodar en Illustrator o regenerar desde plantilla. |
| `resolucion` | "Se ve pixelado", subir DPI | `flujo render rescale <config> --dpi 300`. Mantiene la medida física y sube los px. Reescala los elementos para que el diseño se vea idéntico. |
| `texto` / `color` / `imagen` | Cambiar contenido | Se edita el `config.json` (texto vivo) y se re-renderiza. |

> **Proporción vs. resolución — la distinción clave:**
> - *Pixelado* = problema de **resolución** → más px, misma medida (`--dpi`).
>   Como las piezas se renderizan en **SVG (vectorial)**, el pixelado real solo
>   aparece si hay una **imagen raster** incrustada de baja resolución; ahí la
>   solución es reemplazar/vectorizar ese recurso, no tocar el canvas.
> - *Otra medida/aspecto* = cambio de **proporción** → `-w/-h` (es un cambio de
>   formato, no de calidad).

### Comando `flujo render rescale`

```bash
# Subir resolución (anti-pixelado), mantiene 16.5x6.5 cm:
flujo render rescale projects/.../config.json --dpi 300

# Cambiar proporción a 14x10 cm (avisa que hay que reposicionar):
flujo render rescale projects/.../config.json -w 14 -h 10

# Opciones útiles:
#   --out otro.json          guardar en otro archivo (no sobrescribir)
#   --dry-run                solo mostrar el cálculo
#   --scale-elements/--no-scale-elements   forzar o no el reescalado de elementos
```

La relación px ↔ cm es `px = cm / 2.54 × dpi`. Para imprenta, apuntar a **≥300 DPI**.

---

## 4. Validación

El esquema JSON formal está en
[`schemas/intake.schema.json`](../schemas/intake.schema.json) (JSON Schema
draft-07). Sirve para validar antes de procesar y para que un formulario web
genere JSON correcto.

Reglas de validación además del esquema:
1. `tipo_pieza` debe estar en la lista permitida.
2. Debe venir `formato_sugerido` válido **o** `medidas.ancho_cm` + `alto_cm`.
3. `entrega.formatos[]` solo acepta:
   `editable_svg | vectorizado_svg | pdf_impresion | zip`.
4. Si `formato_sugerido` no existe en el catálogo → warning + se infiere por
   medidas.

Ejemplos completos y válidos en `schemas/ejemplos/`:
- `etiqueta_miel.json`
- `flyer_evento.json`
- `carrusel_ig.json`
- `modificacion_etiqueta.json` (pedido de cambio: proporción + resolución)
- `cartelera_evento.json` (cartelera IG individual; infiere datos del post)
- `pendon_suplemento.json` (gran formato paramétrico, vía Illustrator)

> El catálogo completo de formatos de la ONG (área, medio, herramienta) está en
> [`CATALOGO_FORMATOS.md`](CATALOGO_FORMATOS.md). El campo `pedido.area`
> (`eventos`/`suplementos`) ayuda a enrutar por canal (correo/whatsapp).

---

## 5. Acuse de recibo automático

`flujo intake json <archivo.json>` ya genera un acuse local en
`jobs/<folio>/resultado.md` con:
1. validación del JSON contra el esquema;
2. folio/job asignado;
3. brief + estado inicial;
4. resumen de tipo, formato, medidas y entrega;
5. pendientes/warnings claros para responder al solicitante.

Pendiente para automatización total: conectar ese acuse a IMAP/SMTP o al canal
que use el equipo para responder automáticamente.

---

## 6. Roadmap de implementación

### ✅ Ya implementado
- **`flujo intake json <archivo.json>`** (módulo `src/flujo/intake/json_parser.py`):
  valida contra `schemas/intake.schema.json`, crea job, mapea a `brief.yaml`,
  sugiere formatos por catálogo/medidas, escribe `estado.md` y genera acuse
  `resultado.md`.
- **Selección base de formato** por `formato_sugerido`/medidas usando
  `render/formats.py::suggest_format` y `find_format_by_id`.
- **Acuse de recibo local** con folio + resumen + pendientes/warnings.
- **`flujo render rescale`** (módulo `src/flujo/render/rescale.py`): resuelve los
  cambios de `proporcion` y `resolucion` del bloque `modificacion`; el acuse del
  intake JSON deja comandos sugeridos cuando corresponde.

### Próximos pasos
1. **Poller de correo (IMAP):** leer buzón, extraer JSON adjunto/cuerpo, llamar a
   `flujo intake json` y responder por SMTP con `resultado.md`.
2. **Formulario web** (opcional) que genere el JSON válido para evitar errores
   del colega.
3. **Activación más profunda por tipo**: mapear `contenido.extras` a documentos/
   componentes concretos del `config.json` según cada plantilla.

> Mantener el contrato: **todo canal produce el mismo JSON `intake_version 1.0`**.
> Si el esquema cambia, subir `intake_version` y versionar este documento.
