# Receta: ficha/flyer producto Suplementos RD

Usar para agregar o modificar fichas dentro del proyecto Suplementos RD.

## Fuente

```txt
projects/piezas_vectoriales/suplementos_rd/01_contenido/contenido_suplementos_rd.json
```

## Generar

```bash
cd projects/piezas_vectoriales/suplementos_rd
py scripts/generar_flyers.py
cd ../../..
py scripts/piezas_check_outputs.py
```

## Reglas

- No inventar descripción, nutrientes ni modo de uso.
- Si falta texto, dejar placeholder o preguntar.
- Mantener versión editable y vectorizada.
