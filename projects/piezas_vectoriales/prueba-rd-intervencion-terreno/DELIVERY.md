# Delivery — Propuesta de Servicio – Intervención en Terreno

## Proyecto

- Carpeta: `projects/piezas_vectoriales/prueba-rd-intervencion-terreno`
- Config: `projects/piezas_vectoriales/prueba-rd-intervencion-terreno/config.json`
- Preview: `projects/piezas_vectoriales/prueba-rd-intervencion-terreno/salida_generada/03_preview/preview.html`

## Entregables ZIP

- `projects/piezas_vectoriales/prueba-rd-intervencion-terreno/salida_generada/04_exports/prueba-rd-intervencion-terreno_editables_svg.zip`
- `projects/piezas_vectoriales/prueba-rd-intervencion-terreno/salida_generada/04_exports/prueba-rd-intervencion-terreno_flujo_completo.zip`
- `projects/piezas_vectoriales/prueba-rd-intervencion-terreno/salida_generada/04_exports/prueba-rd-intervencion-terreno_vectorizados_svg.zip`


## Validación sugerida

```bash
py scripts/project_render.py "projects/piezas_vectoriales/prueba-rd-intervencion-terreno/config.json"
py scripts/piezas_check_outputs.py
```


> **Nota 2026-08-28.** Las rutas `salida_generada/**` que este documento
> cita no existen en disco: `scripts/limpiar_basura.sh`, que corre con
> `make clean`, borra todo directorio `salida_generada` de
> `projects/piezas_vectoriales/`. Es salida regenerable, no perdida:
> volver a correr `scripts/piezas_generar.py` sobre este proyecto la
> reconstruye. Se anota porque un lector encuentra la ruta rota y no
> tiene forma de saber que fue deliberado.
