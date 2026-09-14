# Catalogo RD -- Packs y Cotizaciones

Version flujo: 0.56.1

## Fuente de verdad

- Fuente canonica de precios: `data/rd_packs.json`, editable a mano (desde 2026-07-26; antes vivia cableada en dos copias que podian desincronizarse, `packs.py` y `web/src/rdBrand.ts`).
- `src/flujo/plano/packs.py` LEE ese archivo; `costs.py` y `engine.py` consumen SOLO ese modulo, nunca un precio propio.
- `precio` es el unico valor absoluto editable por pack; cualquier monto de desglose se recalcula siempre como `precio*pct/100` (nunca se guarda aparte).

## Packs

| Pack | Nombre | Precio | Voluntarios | Stands | m2 | Desglose por proporciones |
|---|---|---|---|---|---|---|
| INFO | Informativo | $250,000 | 6 | 1 | 9 | no (precio plano) |
| TESTEO | Testeo y Informativo (ambos) | $300,000 | 6 | 2 | 18 | no (precio plano) |
| COMPLETO | Servicio Completo (masivo) | $500,000 | 15 | 2 | 27 | si |

### Pack 1 · Informativo -- Informativo

6 voluntarios · 1 stand 3×3 (9 m²)

Precio: $250,000 (valor absoluto, unico editable en packs.py)

Incluye:
- Stand informativo atendido
- Material educativo + insumos preventivos
- Protectores auditivos, abanicos, suplementos
- Tests de un solo uso (opcional)

Sin desglose por proporciones: precio plano, ver inclusiones arriba.

### Pack 2 · Testeo y Informativo -- Testeo y Informativo (ambos)

6 voluntarios · 2 stands 3×3 (18 m²)

Precio: $300,000 (valor absoluto, unico editable en packs.py)

Incluye:
- Stand informativo y stand de testeo, ambos atendidos
- Módulo de testeo de sustancias
- Análisis colorimétrico gratuito
- Reactivos incluidos

Sin desglose por proporciones: precio plano, ver inclusiones arriba.

### Pack 3 · Servicio Completo -- Servicio Completo (masivo)

15 voluntarios · 2 stands + zona (~27 m²)

Precio: $500,000 (valor absoluto, unico editable en packs.py)

Incluye:
- Informativo + testeo
- Intervención y contención psicológica
- Zona de descanso baja estimulación
- Coordinación operativa en terreno

Desglose (proporcion del precio, derivado siempre como precio*pct/100):

| Item | % | Monto |
|---|---|---|
| Equipo en terreno | 60% | $300,000 |
| Módulo de testeo | 14% | $70,000 |
| Stand informativo | 10% | $50,000 |
| Intervención y contención | 9% | $45,000 |
| Coordinación operativa | 7% | $35,000 |

Suma del desglose: $500,000 (debe igualar el precio del pack).

## Cotizaciones (dual-audiencia)

El comando `py -m flujo cotizaciones <evento.json> --para productora|interno` genera 2 versiones desde el mismo costeo (`flujo.plano.costs.resumen_costos`, derivado del pack del evento):

- `productora`: version externa branded/infografica (para productoras).
- `interno` (tambien acepta `empresa`): desglose detallado interno, para ONG/empresa/trabajador.

Nota sobre el motor real: engine.py funciono: los ejemplos abajo son la salida real de generar_cotizacion().

### Ejemplo -- audiencia productora

```
Reduciendo Daño

COTIZACIÓN — Festival Ejemplo 2026
========================================

Pack 2 · Testeo y Informativo:                         $300,000
Voluntarios: 6 · Stands: 2 · 18 m²

Inclusiones:
  • Stand informativo y stand de testeo, ambos atendidos
  • Módulo de testeo de sustancias
  • Análisis colorimétrico gratuito
  • Reactivos incluidos

TOTAL: $300,000

Nota: precio plano por pack de servicio RD (no por hora/voluntario).

Demo de layout_mode grid_2x + reglas de rider. Cambia a 'row' para el layout clásico en fila.
```

### Ejemplo -- audiencia interno (ONG/empresa)

```
COTIZACIÓN INTERNA — Festival Ejemplo 2026
Para: equipo Reduciendo Daño

COTIZACIÓN — Festival Ejemplo 2026
========================================

Pack 2 · Testeo y Informativo:                         $300,000
Voluntarios: 6 · Stands: 2 · 18 m²

Inclusiones:
  • Stand informativo y stand de testeo, ambos atendidos
  • Módulo de testeo de sustancias
  • Análisis colorimétrico gratuito
  • Reactivos incluidos

TOTAL: $300,000

Nota: precio plano por pack de servicio RD (no por hora/voluntario).

Tarifa vigente: data/rd_packs.json (misma fuente que el rider).
```

## Regenerar

Este archivo es generado por `scripts/generar_catalogo_rd.py` -- NO editar a mano, regenerar con: `py scripts/generar_catalogo_rd.py`
