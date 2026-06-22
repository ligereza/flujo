# LAST_HANDOFF — flujo (Single Source of Truth para continuación)

**IMPORTANTE PARA AHORRO DE TOKENS:**
Esta es la **única** pieza de estado que una IA nueva (o sesión nueva) **debe** leer después de PARA_IA_CONTEXT.md cuando los tokens son limitados.

Mantener este archivo **corto** (< 120 líneas ideal, < 180 máximo). Actualizar **siempre** antes de terminar una sesión o entregar un airdrop.

---

**Fecha:** 2026-06-22  
**Versión actual:** 0.34.10  
**Última sesión:** hub + aistetic poblado + cotizaciones integrado + intake manual en hub. Push hecho.

## Objetivo actual / tarea en curso
(1-2 frases. Ej: "Mejorar el motor de planos para soportar layouts en grilla + constraints simples, y reducir tokens de handoff para nuevas IAs.")

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
1. Pega email/WhatsApp en hub "Pedidos" → copia estructura a job.
2. Agrega ejemplo real a aistetic/ejemplos/ + `flujo aistetic analyze`.
3. Prueba `flujo cotizaciones --para productora` (Windows: py).
4. Actualiza este archivo con 1 tarea + nota plataforma.
5. Agrega 1 regla a aistetic.json (ej. comunicaciones).
6. Sugiere mejora pequeña en hub para texto→imagen.

## Próximas (prioridad)
1. Integrar aistetic en outputs reales (cotizaciones HTML/ infografía).
2. Mejorar hub con previews reales de renders.
3. (Usuario) Intake manual → estructura (ya en hub).
4. Airdrop más robusto para Windows + auto TODO.
5. Mantener hub + LAST_HANDOFF actualizados.

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