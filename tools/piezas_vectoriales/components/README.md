# Componentes piezas_vectoriales

Componentes JSON reutilizables para copiar dentro de `global_elements` o `documents[].elements` en un `config.json`.

## Componentes disponibles

- `logo_marca.json`
- `footer_web.json`
- `qr_placeholder.json`
- `lote_vencimiento.json`
- `tabla_info_basica.json`

## Uso

Copiar el array del componente y pegar sus objetos dentro de:

```json
"global_elements": []
```

o dentro de:

```json
"documents": [ { "elements": [] } ]
```

Los componentes usan variables como:

```txt
{brand}
{website}
```

que el generador reemplaza desde `project`.

## Nota

Son placeholders editables. Ajustar `x`, `y`, `w`, `h` según formato.

## Insertar automáticamente

```bash
py scripts/piezas_add_component.py "projects/piezas_vectoriales/MI_PROYECTO/config.json" qr_placeholder.json doc
py scripts/piezas_add_component.py "projects/piezas_vectoriales/MI_PROYECTO/config.json" footer_web.json global
```
