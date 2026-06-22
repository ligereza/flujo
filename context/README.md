# context/ — Workspace diario de flujo

Este es el **centro del repo** para trabajo diario.

## Archivos clave (abrir en este orden)

1. **flujo_hub.html** — El main.
   - Intake de pedidos (pega email/pedido)
   - Visualizadores embebidos (SVG + Plano)
   - Comandos listos para copiar
   - Sección raw para agentes

2. **svg_visualizer.html** — Visualizador real de todas las piezas en `/svg`
   - Agrupado exactamente como las carpetas (Eventos/Flyers vs Suplementos)
   - `<object>` embebidos + "Vista grande" modal
   - Botones "Usar como base", editar, vectorizado

3. **plano_demo.html** — Demo interactivo del motor de planos
   - Controles paramétricos
   - SVG generado en vivo + rider + costos
   - Integración aistetic + export Blender

4. **LAST_HANDOFF.md** — Estado actual + tareas para agentes (bajo token)

## Otros archivos

- `DAILY.md` — Notas del día (puede estar desactualizado, usar el hub)
- `ESTADO.md` — Estado rápido (preferir el hub)
- `dashboard.html` — Redirige al hub

Ver también: `LAST_HANDOFF.md`, `../README.md`, `../docs/REPO_MAP.md` y `../docs/HIGIENE_REPO.md`.

## Flujo recomendado

- Al empezar el día → abrir `flujo_hub.html`
- Para ver trabajos SVG ya hechos → `svg_visualizer.html`
- Para planos y riders → `plano_demo.html`
- Para continuar como agente IA → leer primero LAST_HANDOFF + hub

Todo alineado a `projects/aistetic/` y listo para Illustrator / Photoshop / Blender.
