# piezas_vectoriales — Proyectos y plantillas vectoriales

Este es el proyecto principal de **entregables vectoriales** listos para Illustrator / Photoshop.

## Contenido

- `etiquetas_ejemplo/`, `flyer_horizontal_minimo/`, `plantillas_rd/` → plantillas base y ejemplos.
- `prueba-rd-intervencion-terreno/`, `rider_rd_intervencion_terreno/`, `suplementos_rd/` → trabajo real con brief + config + reportes.
- `config.json` es el formato canónico que usa `flujo render run`.

## Relación con flujo

Cuando exista una línea editorial consolidada en `projects/flujo/`, las configuraciones aquí deberían heredar paleta, tipografía y reglas de composición desde `flujo.json`.

## Cómo explorar para una IA externa

Si estás extrayendo identidad visual:
- Abre varios `config.json`
- Busca secciones `palette`, `global_elements`, `documents[].elements[]`
- Observa nombres de colores, tamaños de fuente, márgenes y uso de marcos.

Ver `projects/README.md` para contexto general del ecosistema.
