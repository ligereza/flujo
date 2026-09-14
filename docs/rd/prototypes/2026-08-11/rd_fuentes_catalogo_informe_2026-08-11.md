# Catálogo de fuentes para el grafo RD

Fecha: 11 de agosto de 2026
Estado: catálogo candidato, separado de la afirmación científica

## Propósito

El grafo relacional no debe guardar sólo una lista de URLs. Necesita distinguir qué papel cumple cada fuente:

- ficha de sustancia;
- guía de testeo;
- reactivo o tira específica;
- producto o recurso de testeo;
- research o contenido editorial;
- fuente general.

El catálogo se genera desde el registro universal, el grafo relacional y la biblioteca normalizada de reactivos. Una misma URL puede cumplir más de un papel, y cada relación conserva sus propios límites.

## Regla de interpretación

Que una URL aparezca en el catálogo no significa que todo lo que diga la página esté validado científicamente. La URL es un puntero de trazabilidad. La certeza depende de la relación, el tipo de evidencia y el alcance de la fuente.

Ejemplo:

- una página de tienda puede demostrar que RD ofrece un recurso;
- una guía puede explicar el uso editorial de un reactivo;
- ninguna de las dos, por sí sola, convierte una señal colorimétrica en una identificación completa de la muestra.

## Integración con la futura interfaz

Cada relación debería abrir sus fuentes agrupadas por función:

1. `Ficha de sustancia`;
2. `Guía de testeo`;
3. `Reactivo o tira`;
4. `Producto o recurso`;
5. `Research/post`;
6. `Fuente científica externa`.

La interfaz pública puede mostrar primero la fuente de RD y luego las fuentes externas, pero nunca debe ocultar el tipo de evidencia ni el límite del resultado.

## Próximo paso técnico

Agregar al grafo una matriz de referencias explícitas por relación:

```text
source_refs:
  rd_pages[]
  testing_guides[]
  product_resources[]
  research_posts[]
  scientific_sources[]
```

Esto permitirá que POST, Research y la tabla interactiva consuman la misma relación sin copiar manualmente sus URLs ni mezclarlas con los nombres de las sustancias.
