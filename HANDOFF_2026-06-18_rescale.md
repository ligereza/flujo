# 🤝 Handoff 2026-06-18 — flujo v0.26.0 — Render rescale + bloque `modificacion`

## Por qué este airdrop

El dueño preguntó: *"¿si me piden cambiar una proporción o pixelado?"*. Este
airdrop entrega la herramienta para responder a eso de forma reproducible, y
extiende el contrato de intake JSON para recibir pedidos de **modificación**
(no solo pedidos nuevos).

## Qué incluye

| Archivo | Cambio |
|---|---|
| `src/flujo/render/rescale.py` | **NUEVO.** Motor de reescalado: `set_dpi()` (resolución, anti-pixelado), `set_real_size()` (proporción/medida), `rescale_file()`. Funciones puras + envoltura de archivo. |
| `src/flujo/cli.py` | **NUEVO comando** `flujo render rescale` con `--dpi`, `-w/-h`, `--out`, `--dry-run`, `--scale-elements`. |
| `tests/test_render_rescale.py` | **NUEVO.** 17 tests (conversiones, dpi, proporción, no-mutación del input, archivos). |
| `schemas/intake.schema.json` | Bloque opcional `pedido.modificacion` (pieza_existente, tipo_cambio, proporcion, resolucion, detalle). |
| `schemas/ejemplos/modificacion_etiqueta.json` | **NUEVO** ejemplo de pedido de cambio. |
| `docs/INTAKE_JSON.md` | Nueva sección 3.7 (modificación) + cómo se resuelve cada `tipo_cambio` + comando rescale. |
| `docs/BLENDER_FLYERS.md` | **NUEVO.** Captura del flujo real de flyers/Blender del dueño (ver abajo). |
| `README.md`, `version.py`, `pyproject.toml` | Versión 0.26.0 + referencia al comando. |

## Concepto clave: pixelado ≠ proporción

- **Pixelado** = falta de **resolución** → `flujo render rescale c.json --dpi 300`.
  Mantiene la medida física (cm), sube los px, y reescala los elementos para que
  el diseño se vea idéntico. (Ojo: como el render es SVG vectorial, el pixelado
  real solo ocurre con imágenes raster incrustadas de baja resolución.)
- **Otra medida/aspecto** = **proporción** → `flujo render rescale c.json -w 14 -h 10`.
  Recalcula el canvas pero **NO reposiciona los elementos** (deformaría el
  encuadre); avisa que hay que reacomodar en Illustrator o regenerar.

Relación: `px = cm / 2.54 × dpi`. Imprenta ≥ 300 DPI.

## Contexto que dio el dueño sobre Blender (registrado en docs/BLENDER_FLYERS.md)

> Hay 2 tipos de flyer: (1) impresión 14×10 cm, y (2) cartelera para historias
> de IG que usa la foto descargada de Instagram y la enmarca en Blender. La
> cartelera puede ser **individual** o **triple**, ambas digitales pero en
> proyectos de Photoshop distintos, donde un **droplet** reemplaza y exporta.
> Hoy el droplet existe solo para la **individual**; la **triple** está pendiente.

No se implementó nada de Blender aún — solo se documentó para el futuro.

## Verificación hecha

```
✅ python -m compileall src/            → OK
✅ pytest tests/                        → 86 passed, 1 skipped (eran 69; +17)
✅ flujo render rescale --help          → OK
✅ rescale --dpi 300 sobre etiqueta real → 3300x1300 → 1949x768, valida OK
✅ rescale -w 14 -h 10 sobre etiqueta    → 3300x1300 → 2800x2000, avisa reposicionar
✅ JSON Schema válido + ejemplo modificacion pasa + negativo falla
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.26.0 - render rescale + modificacion"
# o:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.26.0 - render rescale + modificacion"

py -m pip install -e .
flujo version            # 0.26.0
py -m pytest tests/ -q   # 86 passed, 1 skipped
flujo render rescale projects/.../config.json --dpi 300 --dry-run
```

## Próximos pasos (para la siguiente IA)

1. **Editor Gradio** (Fase 3 del plan): cargar formato → ajustar datos/proporción
   → preview SVG → exportar. El `rescale` ya está listo para ser el backend del
   slider de proporción/DPI.
2. **`flujo intake json`** que enrute `modificacion.tipo_cambio` a `render rescale`.
3. **Motor de layout tipo CSS + auto-fit de texto** ("misma medida, distinto
   texto") y elemento `image` en el generador SVG (hoy no existe tipo image).
4. **Blender/droplet triple** (ver `docs/BLENDER_FLYERS.md`).
