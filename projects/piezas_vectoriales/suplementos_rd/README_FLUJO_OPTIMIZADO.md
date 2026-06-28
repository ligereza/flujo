# Flujo optimizado · Suplementos RD

Formato de trabajo: **2800 × 2000 px**, proporción equivalente a **14 × 10 cm**.

## Carpetas

- `01_contenido/`: texto maestro aprobado en JSON.
- `02_editables_svg/`: SVG con texto vivo/editable para Illustrator.
- `03_final_vectorizado_svg/`: SVG con texto convertido a trazados/path. Ideal para entrega final o imprenta.
- `04_preview/`: HTML para revisar visualmente todos los flyers.
- `05_exports/`: ZIPs listos para compartir.
- `scripts/`: generador automático.

## Cómo editar el flujo

1. Cambia textos, títulos o colores en:
   `01_contenido/contenido_suplementos_rd.json`
2. Regenera todo ejecutando:
   `python3 scripts/generar_flyers.py`
3. Abre en Illustrator los archivos de:
   `02_editables_svg/`
4. Cuando el diseño esté aprobado, usa los archivos de:
   `03_final_vectorizado_svg/`

## Illustrator

- Para cambiar fondos o colores: edita los grupos `fondo_editable`, `marco_y_decoracion_editable` y `cajas_editables`.
- Para editar textos: usa los SVG de `02_editables_svg`.
- Para evitar problemas de fuentes en la entrega: usa los SVG de `03_final_vectorizado_svg`.

## Nota

Post Fiesta está incluido en el flyer general, pero todavía no existe ficha individual porque falta su texto completo.
