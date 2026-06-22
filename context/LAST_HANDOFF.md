# LAST_HANDOFF — flujo (Single Source of Truth para continuación)

**IMPORTANTE PARA AHORRO DE TOKENS:**
Esta es la **única** pieza de estado que una IA nueva (o sesión nueva) **debe** leer después de PARA_IA_CONTEXT.md cuando los tokens son limitados.

Mantener este archivo **corto** (< 120 líneas ideal, < 180 máximo). Actualizar **siempre** antes de terminar una sesión o entregar un airdrop.

---

**Fecha:** 2026-06-22  
**Versión actual:** 0.34.10  
**Última sesión:** Mejora completa del flujo. Hub parser ahora hace matching real + "nueva sección o tarea". Cotizaciones genera archivos reales (txt + html con aistetic). Render aplica aistetic por defecto. AGENT_OPERATING_MANUAL.md + hub = única fuente para agentes.

## Objetivo actual / tarea en curso
Fortalecer los dos flujos de agentes:
1. Pedido reciente + repo → procesar con herramientas y decidir si usar formato existente o proponer nuevo.
2. Repo completo → continuar mejoras (priorizando integración con AI/PS/Blender y soporte a agentes).

## Estado del mundo (crítico)
- **Activo:** Hub diario (flujo_hub.html) como entrada. aistetic con paleta real. cotizaciones dual integrado a planos.
- **Último:** Intake manual vía hub (pegar email → brief). Airdrop mejorado (Windows + español + TODOs).
- **Salud:** OK (ver hub).
- **Clave:** Usa hub para pedidos. Agentes: haz tareas simples del LAST_HANDOFF. Todo alineado a aistetic.

## Qué NO está hecho / bloqueos / riesgos
- `flujo intake json` sigue pendiente (schema existe, implementación completa no).
- Motor de planos mejorado pero aún limitado (grid básico; falta integrar primitives schema a fondo).
- LAST_HANDOFF es manual + auto-append básico; se puede hacer más inteligente (diff summary).
- Recepción automática (IMAP/webhook) no implementada.

## Tareas simples para agentes (low token - una por vez)
**Para Flujo Pedido:**
- Pega un correo real en el hub y genera la estructura + comando correcto.
- Revisa si el pedido calza en INDEX_FORMATOS o aistetic. Si no, propone nueva sección mínima.

**Para Flujo Mejoras:**
- Implementa una pequeña mejora al hub (mejor matching de formatos o preview de export).
- Actualiza FOR_EXTERNAL_AI.md o este archivo con instrucciones más claras para los dos flujos.

**General:**
- Agrega 1 ejemplo a aistetic/ejemplos/ + genera su json.
- Prueba render + export con --for illustrator o blender.
- Actualiza este LAST_HANDOFF con estado actual + tareas pendientes.

## Próximas (prioridad para agentes)
1. Hacer que el hub detecte mejor si un pedido calza en formatos existentes (aistetic + INDEX).
2. Mejorar el parser del hub para generar output más estructurado (brief.yaml listo).
3. Agregar soporte claro en hub para "crear nueva sección" cuando no hay match.
4. Fortalecer integración de export con AI/PS/Blender (ya iniciado con --for).
5. Mantener documentación de los dos flujos actualizada (FOR_EXTERNAL_AI + este archivo).

## Cómo verificar rápido el estado
```bash
flujo health
flujo version
flujo daily
flujo job next
py -m pytest tests/ -q --tb=no
```

## Cambios clave de esta sesión (para el siguiente)
- Sistema Low-Token Continuation implementado:
  - `context/LAST_HANDOFF.md` como fuente única para continuar con pocos tokens.
  - `flujo handoff last|create`
  - Integración en `airdrop apply` (auto-append).
  - Docs actualizados para priorizarlo (ahorro de tokens).
- Estructuras mejoradas:
  - Nuevo schema `schemas/layout_primitives.schema.json`.
  - Plano soporta `layout_mode` (row + grid_2x).
  - Ejemplo actualizado.

## Notas para la próxima IA (ahorra tokens)
Lee solo: PARA_IA_CONTEXT.md + este LAST_HANDOFF.md + corre `flujo daily` + abre context/flujo_hub.html

**Regla de oro:** Actualiza este archivo al final (agrega 1-2 lineas de "Tareas simples"). Usa español primero, nota Windows (`py`) vs Linux.

El repo sirve para: "mira como trabajo (hub + ejemplos), ahora ayúdame (tareas claras arriba)". El desafío es ordenar pedidos (WhatsApp/Gmail) en estructuras claras.

---
*Este archivo se actualiza manualmente o vía helper al final de cada airdrop/sesión. Mantenerlo conciso es responsabilidad de quien entrega.*

---

**Actualización 2026-06-22 01:05**

Mejora significativa: LAST_HANDOFF + flujo handoff + layout_primitives schema + soporte grid_2x en planos. Integrado en airdrop flow para continuidad de IAs con bajo consumo de tokens.

Actualiza la sección 'Próximas acciones' manualmente si es necesario.