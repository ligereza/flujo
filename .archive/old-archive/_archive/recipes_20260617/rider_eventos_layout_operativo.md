# Receta: rider eventos / layout operativo

Usar cuando el pedido sea un rider técnico, layout de stand o requerimientos para producción de eventos.

## Plantilla recomendada

```txt
tools/piezas_vectoriales/plantillas/rider_eventos_a4_horizontal.config.json
```

## Flujo

```bash
py scripts/project_new_from_template.py "rider nombre" rider_eventos_a4_horizontal.config.json
py scripts/project_render.py projects/piezas_vectoriales/rider-nombre/config.json
```

## Elementos típicos

- Toldo/carpa.
- Mesa informativa.
- Mesa de testeo.
- Sillas equipo.
- Rack/caja almacenamiento.
- Zona descanso público.
- Basurero.
- Iluminación.
- Punto eléctrico.
- Calefacción.
- Circulación público.
- Coordinación con seguridad/equipo médico.
