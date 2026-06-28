# Checkpoint — fase 7: pipeline correo a job a proyecto

Fecha: 2026-06-16_17-12

## Estado

# Estado del proyecto

Última actualización: 2026-06-16

## Objetivo actual

Mantener un repo limpio que organice proyectos creativos, automatizaciones y flujos con IA. No reemplaza el trabajo manual; acelera el inicio y evita perder contexto entre sesiones.

## Herramientas activas

1. `flyer_eventos` — importar proyectos desde correos/Instagram, mantener estructura y manifest.
2. `piezas_vectoriales` — generar etiquetas, flyers y riders en SVG editable + vectorizado desde JSON.
3. `jobs` — flujo de pedidos: brief → privacidad → preparación → proyecto → render.

## Herramientas en cola

- `slowmo_blender_ae` — todavía no activa.
- `asistente_pedido` — todavía no activa.
- `canva_data` — todavía no activa.
- `privacidad_datos` — MVP disponible, en evolución.

## Regla

No importar scripts viejos automáticamente. Usar `reference_old` solo como referencia manual.

## Próximos pasos completados (fase 1)

- [x] Limpiar historial de git.
- [x] Agregar tests mínimos de smoke.
- [x] Mejorar portabilidad de scripts entre Windows, macOS y Linux.
- [x] Dependencias documentadas en `requirements.txt`.

## Próximos pasos (fase 2 completada)

- [x] Crear helpers comunes en `scripts/_common.py`.
- [x] Unificar creación de proyectos flyer con `scripts/flyer_create_project.py`.
- [x] Mejorar `scripts/flujo.py` como comando unificado robusto.

## Próximos pasos (fase 3 completada)

- [x] Pre-commit hooks.
- [x] Health check mejorado.
- [x] Más tests de smoke.

## Próximos pasos (fase 4 completada)

- [x] `.gitattributes` para controlar finales de línea y marcar documentación.
- [x] Limpiar `projects/tapiz` de `egg-info`.
- [x] Agregar licencia MIT.
- [x] Agregar `CONTRIBUTING.md`.
- [x] Script para archivar checkpoints antiguos.

## Próximos pasos (fase 5 completada)

- [x] Mejorar documentación de agentes (`AGENTS.md`, `PARA_IA.md`).
- [x] Workflows de CI/health/tests.
- [ ] Considerar si mover/eliminar `reference_old`.
- [ ] Mejorar README con badge de CI.

## Próximos pasos (fase 6 en progreso)

- [x] Asistente de próximas acciones diarias (`scripts/flujo_daily.py`).
- [x] Integrar `flujo_daily` con `flujo.py`.
- [ ] Agregar test para `flujo_daily.py`.
- [ ] Considerar si mover/eliminar `reference_old`.

## Cambios realizados

-

## Próximo paso

-
