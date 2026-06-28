# Rider eventos / layout operativo

Nuevo tipo de pieza para propuestas de intervención en terreno.

No es flyer ni etiqueta. Es un documento técnico/comercial para producción.

## Formato inicial

- A4 horizontal.
- 2 páginas/documentos:
  1. Requerimientos rider.
  2. Layout operativo sugerido.

## Uso

```bash
py scripts/project_new_from_template.py "rider rd intervencion" rider_eventos_a4_horizontal.config.json
py scripts/project_render.py projects/piezas_vectoriales/rider-rd-intervencion/config.json
```

## Pendiente de diseño

La plantilla es base técnica. El diseño visual final debe ajustarse manualmente/por IA luego.

## Presets

```bash
py scripts/rider_presets.py
py scripts/flujo.py rider-presets
```

## Crear rider rápido

```bash
py scripts/rider_new.py "rider nombre" "Marca"
py scripts/flujo.py rider-new "rider nombre" "Marca"
```

## Componentes específicos

```txt
tools/piezas_vectoriales/components/rider/
```
