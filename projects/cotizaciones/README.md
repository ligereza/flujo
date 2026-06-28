# cotizaciones — Presupuestos / Cotizaciones duales (integrado con flujo)

Proyecto para generar cotizaciones que se dividen en 2 audiencias, usando estilos de `flujo` y formatos/infografías consistentes.

## Audiencias

1. **Para productoras** (externo, como diseñador de ONG "Reduciendo Daño"):
   - Archivo pulido, branded con flujo.
   - Enfoque en valor, infografía atractiva, tono profesional pero humano.
   - Formato: infográfico (usa catálogo de formatos + flujo).

2. **Hacia la ONG / trabajador / empresa** (interno):
   - Desglose detallado de costos reales.
   - Tablas, márgenes internos, notas operativas.
   - Formato: texto/ tabla o PDF interno (puede ser A4 rider style).

## Integración

- Consume el mismo `evento.json` que `plano/`.
- Usa `flujo/flujo.json` para paleta y estilos.
- Puede generar infografía usando el sistema de piezas_vectoriales (config + render) o SVG directo.
- Los JSON descriptivos de ejemplos se almacenan en `flujo/json/` para que agentes extraigan reglas estéticas.

## Uso (CLI futura)

```
flujo cotizaciones projects/plano/ejemplos/evento_ejemplo.json --para productora
flujo cotizaciones ... --para interno
```

Salida: archivos en la carpeta del evento o stdout.

## Estructura

```
projects/cotizaciones/
├── README.md
├── engine.py          # lógica dual + integración flujo
├── ejemplos/
└── (futuro) templates/
```

Ver `src/flujo/plano/costs.py` (base de costos) y engine de plano para reutilizar.

## Para agentes

Usa `flujo/ejemplos/` + `json/` para entender la línea estética actual antes de generar cotizaciones.
Mantén consistencia con formatos del catálogo (A4, riders, etc.).

Estado: nuevo (2026-06). Integrar con flujo y mejorar planos.
