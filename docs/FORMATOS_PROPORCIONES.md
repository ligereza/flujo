# Formatos y proporciones

El sistema mantiene universalidad mediante `canvas.width`, `canvas.height` y `real_size_cm` en cada `config.json`.

## Listar formatos

```bash
py scripts/piezas_formatos.py
```

## Sugerir plantilla por medida

```bash
py scripts/piezas_formatos.py 16.5 6.5 etiqueta
```

## Crear proyecto desde brief usando auto-sugerencia

```bash
py scripts/brief_to_project.py "jobs/.../brief.yaml"
```

Si la medida coincide con una plantilla conocida, la usa. Si no, crea una base proporcional universal.

## Forzar plantilla

```bash
py scripts/brief_to_project.py "jobs/.../brief.yaml" nombre_proyecto tools/piezas_vectoriales/plantillas/etiqueta_horizontal_165x65.config.json
```

## Nuevas plantillas

- `one_page_propuesta_a4`: propuesta/dossier A4 vertical.
- `carrusel_cuadrado_1080`: slide cuadrado digital.

`brief_to_project.py` usa `tipo_pieza` y `posibles_formatos` como pistas para elegir plantilla.
