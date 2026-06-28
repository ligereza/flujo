# Catálogo oficial de formatos — ONG

**Fuente de verdad:** `tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json`
(schema v2.0). Consultar con `flujo render formats`.

Cada formato declara, además de medida/canvas:
- **area** — `eventos` | `suplementos` | `comun`
- **medio** — `impresion` | `digital`
- **herramienta** — `illustrator` | `photoshop` | `blender` | `svg` (o pipeline `a+b`)
- **parametrico** — `true` si la medida la define cada pedido (pendones/banderas)
- **inferir** — datos a deducir desde la imagen de IG (productora, fecha, venue, logo)

> **Regla de oro del dueño:**
> **Illustrator = impresión real · Photoshop = digital · Blender = recursos
> (frasco de suplementos) y export de carteleras.**

---

## 🗂️ Por área y canal de entrada

| Área | Canal de info | Formatos |
|---|---|---|
| **Eventos** | 📧 correo | flyer físico, carteleras (individual/triple), post IG, brief productoras, historias flexibles, rider |
| **Suplementos** | 💬 whatsapp | etiquetas, flyers informativos, pendones, banderas |

---

## 🎉 Área EVENTOS (entra por correo)

| id | medida | px | medio · herramienta | notas |
|---|---|---|---|---|
| `evt_flyer_fisico_10x14` | 10×14 cm vert. | 2000×2800 | impresión · SVG+Illustrator | flyer físico de evento |
| `evt_cartelera_individual_1080x1920` | 9:16 | 1080×1920 | digital · Photoshop+Blender | 1 evento (stand). Foto IG enmarcada en Blender + droplet PS. Infiere productora/fecha/venue |
| `evt_cartelera_triple_1080x1920` | 9:16 | 1080×1920 | digital · Photoshop+Blender | 3 eventos del mes. **Aquí sí se ven logos.** Droplet triple **pendiente** |
| `evt_post_ig_1080x1350` | 4:5 | 1080×1350 | digital · Photoshop | suele venir en 3: portada / info / intención |
| `evt_brief_productora_pdf_universal` | A4 (univ.) | 2100×2970 | impresión · SVG+Illustrator | brief con layouts, PDF, tamaño universal |
| `evt_historia_flexible_1080x1920` | 9:16 flexible | 1080×1920 | digital · Photoshop | historias varias, formato mixto según tema |
| `rider_eventos_a4_horizontal` | 29.7×21 cm | 2970×2100 | impresión · SVG+Illustrator | rider técnico/operativo de stand |

### Inferencia desde Instagram (carteleras)
Las carteleras usan la foto descargada de IG. El sistema debe inferir:
- **productora** → normalmente el @usuario de la imagen.
- **fecha** → del texto/caption del post.
- **venue (ubicación)** → del caption.
- **logo (foto de perfil)** → **solo en la triple** (en la individual no se ve).

> Hoy esa inferencia **no está implementada**, pero es **menos urgente** porque
> las productoras se repiten y la cartelera triple (donde se ven logos) es poco
> frecuente. Los avisos de IG (1ª del carrusel es video / perfil privado) **sí**
> existen ya en `src/flujo/intake/email_parser.py`.

---

## 💊 Área SUPLEMENTOS (entra por whatsapp)

| id | medida | px | medio · herramienta | notas |
|---|---|---|---|---|
| `sup_etiqueta_165x65` | 16.5×6.5 cm | 3300×1300 | impresión · SVG+Illustrator | etiqueta (ref. RELIEVE/COMROESS) |
| `sup_etiqueta_140x100` | 14×10 cm | 2800×2000 | impresión · SVG+Illustrator | etiqueta/flyer |
| `sup_flyer_informativo_a5` | 14.8×21 cm | 1748×2480 | impresión · SVG+Illustrator | flyer por suplemento/proteína |
| `sup_pendon_rectangular` | **paramétrico** (def. 80×200 cm) | — | impresión · **Illustrator** | gran formato; medida en metros por pedido |
| `sup_bandera_poligonal` | **paramétrico** (def. 60×180 cm) | — | impresión · **Illustrator** | bandera/stand, forma poligonal |

### Gran formato (pendones y banderas)
- Son **paramétricos**: la medida real (metros) la define cada pedido. En el
  intake JSON van con `medidas.ancho_cm` / `alto_cm` explícitos.
- **SÍ O SÍ pasan por Illustrator** (impresión real). El flujo SVG sirve de base
  pero el acabado/sangrado/marcas y el PDF final se hacen en AI.
- `dpi_objetivo: 150` (suficiente por distancia de lectura del gran formato).
- La **bandera** es poligonal (`forma: poligono`), no rectangular.

---

## 🧰 Herramienta por medio (la regla clave, operacionalizada)

```bash
# Todo lo que va a IMPRENTA (Illustrator):
flujo render formats -m impresion

# Todo lo DIGITAL (Photoshop / Blender):
flujo render formats -m digital

# Lo que toca Blender (carteleras):
flujo render formats --herramienta blender

# Por área:
flujo render formats -a eventos
flujo render formats -a suplementos
```

---

## 🧊 Blender (recursos y export)

Blender se usa en **ambas** áreas:
- **Suplementos:** modelo del **frasco** (ya existe con texturas) para mockups.
- **Eventos:** **enmarcado/export de carteleras** (foto IG → escena → render).

Detalle del flujo de carteleras y el pendiente del droplet triple en
`docs/BLENDER_FLYERS.md`.

---

## ➕ Cómo agregar/editar un formato

1. Edita `tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json` (añade un
   objeto al array `formatos` con: `id`, `tipo`, `area`, `medio`, `herramienta`,
   `real_size_cm`, `canvas`, y opcionalmente `template`, `parametrico`, `inferir`).
2. Si tiene plantilla, crea su `*.config.json` en `plantillas/`.
3. Verifica: `flujo render formats` y `py -m pytest tests/test_formats_catalogo.py`.
4. Entrega como airdrop (no edites el repo directo).

> `formats.py` ignora los campos que no entiende, así que el catálogo puede
> crecer sin romper compatibilidad.
