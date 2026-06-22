# Checkpoint — jobs + checklist impresión

Fecha: 2026-06-14

## Cambio

Se agregó una primera capa de control para pedidos nuevos:

- `jobs/_template/` para crear trabajos desde correos/briefs.
- `scripts/job_new.sh` para crear jobs rápidamente.
- `docs/CHECKLIST_IMPRESION.md` para validar entregas.
- `recipes/` con recetas para etiquetas y Suplementos RD.
- `.github/ISSUE_TEMPLATE/pedido_impresion.yml` para pedidos desde GitHub Issues.

## Objetivo

Que una IA vía web/chat pueda convertir un correo en un job controlado antes de generar archivos.
