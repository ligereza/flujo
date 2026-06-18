# Intake por JSON — Especificación para colegas y agentes

**Versión del esquema:** `1.0`
**Estado:** estructura definida y validable. El comando que la consume
(`flujo intake json`) es el siguiente paso de implementación (ver
[Roadmap](#roadmap-de-implementación)).

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

---

## 5. Acuse de recibo automático

Cuando el intake JSON se procese (por el comando o por el poller de correo), el
sistema debe:
1. Validar el JSON contra el esquema.
2. Asignar un **folio** (`id` del job, ej. `2026-06-18_miel-organica`).
3. Ejecutar **privacy scan**.
4. Crear el **brief** + **job** en estado `brief_extraido_pendiente_revision`.
5. **Responder al solicitante** confirmando: folio, qué se entendió (tipo,
   formato, medidas) y qué falta (pendientes). → Esto es lo que independiza al
   dueño de responder mensajes.

---

## 6. Roadmap de implementación

Para la siguiente IA que retome esto. Pasos sugeridos, de menor a mayor esfuerzo:

1. **`flujo intake json <archivo.json>`** (módulo `src/flujo/intake/json_intake.py`):
   - Valida contra `schemas/intake.schema.json`.
   - Mapea a `Brief` (reusar `brief_from_text` como fallback para campos libres).
   - Crea job vía `create_job` + `prepare_job`. Añadir tests.
2. **Selección de plantilla por `formato_sugerido`/medidas** reusando
   `render/formats.py::suggest_format` y `find_format_by_id`.
3. **Acuse de recibo:** generar un `resultado.md`/respuesta con folio + resumen.
4. **Poller de correo (IMAP):** script o módulo que lee un buzón, extrae JSON
   (adjunto o cuerpo), llama a `intake json`, y responde por SMTP. Correr por
   cron/Task Scheduler. (Decisión del dueño sobre el canal — ver README.)
5. **Formulario web** (opcional) que genere el JSON válido para evitar errores
   del colega.

> Mantener el contrato: **todo canal produce el mismo JSON `intake_version 1.0`**.
> Si el esquema cambia, subir `intake_version` y versionar este documento.
