# Integración de testeos en eventos — base 2025

Generado: 2026-08-12

## Resultado

Se preservó la fuente `Testeo 2025.xlsx` y se construyó una integración separada con 42 pestañas, 42 eventos-fuente, 1761 filas no vacías de fuente (de ellas, 1646 quedan clasificadas como datos y 115 como datos con anomalías) y 5394 observaciones de reactivo/resultado.

La fuente no se interpretó como una tabla de composición. Cada registro conserva su pestaña y fila original; las normalizaciones son candidatas para revisión humana.

La proyección separa automáticamente cuatro errores de columna evidentes: encabezados repetidos, nombres de formato escritos en la columna de sustancia, resultados escritos en la columna de reactivo y pruebas que no son colorimétricas. No convierte una etiqueta incompleta en una identidad.

## Regla sanitaria y semántica

> Los testeos colorimétricos registran una señal de presencia compatible con ciertos compuestos o familias. No demuestran identidad definitiva, pureza, potencia, cantidad ni seguridad.

Por eso la integración usa `contains_signal_only` y conserva el texto original de cada resultado.

## Puente futuro

La conexión queda preparada sin inventar vínculos:

`test_id -> event_id -> venue_id / producer_id`

- `event_id` identifica la pestaña-fuente, no una venue ni una productora.
- `venue_id` y `producer_id` quedan vacíos hasta contar con evidencia explícita.
- `Link Queue` contiene dos enlaces pendientes por evento: evento-venue y evento-productora.
- Se conserva `evidence_ref`, `confidence`, `status` y `review_status` para una futura vinculación humana.

## Hallazgos de calidad

- Filas de datos incluyendo anomalías: 1831
- Filas no vacías sin encabezados repetidos: 1761
- Filas clasificadas como datos: 1646
- Grupos de pestañas con contenido idéntico: 3
- Filas con sustancia ausente o no resuelta: 115
- Etiquetas de sustancia todavía no resolubles: 2 (`polvo blanco` usado como sustancia y `Desconocido`)
- Etiquetas de reactivo todavía no resolubles: 1 (`Mireia`)
- Etiquetas reclasificadas: `Ketamina+M` queda como mezcla candidata; `Cannabis` como prueba de catálogo `cbd_thc`; `Fentanilo` como tira no colorimétrica; `Sin reaccion` como resultado desplazado.

El nombre del archivo dice 2025. La mayoría de los tokens compactos se proyectan como fechas candidatas de 2025 con confianza baja; cuatro pestañas conservan fechas explícitas de 2026 y dos no contienen fecha interpretable. Nada de esto se publica como hecho sin evidencia del evento.

## Archivos

- Fuente preservada: `Testeo 2025.source.xlsx`
- Evidencia machine-readable: `rd_testeos_eventos_2025_evidence_2026-08-12.json`
- Libro integrado: `rd_testeos_eventos_2025_integrated_2026-08-12.xlsx`
- Esta síntesis: `rd_testeos_eventos_2025_informe_2026-08-12.md`

## Próxima revisión humana

1. Revisar solo las dos sustancias y el reactivo que siguen sin identidad resoluble.
2. Marcar duplicados exactos como no acumulables en agregados, manteniendo sus filas originales.
3. Confirmar las cuatro fechas 2026 y las dos pestañas sin fecha.
4. Vincular evento, venue y productora con evidencia externa; el nombre de la pestaña solo genera un candidato, no una relación pública.
5. Aprobar el lenguaje público de cada resultado antes de llevarlo a la matriz o a un POST.
