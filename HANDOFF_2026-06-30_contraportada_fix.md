# HANDOFF 2026-06-30 - Contraportada SVG fix

## Problema

Los tests de contraportadas fallaban porque:
1. El validador esperaba dimensiones 1181x1654 px (incorrecto)
2. La contraportada base fue eliminada (dimensiones wrong)
3. Los defaults en illustrator/bridge usaban dimensiones obsoletas

## Fixes aplicados

### 1. svg_validator.py
- Cambiado EXPECTED_CONTRAPORTADA_SIZE de (1181, 1654) a (2000, 2800)

### 2. illustrator.py
- height de 1654 a 2800
- document_size default de (2362, 1654) a (2000, 2800)

### 3. cli.py
- Help text actualizado de "1181x1654 px" a "2000x2800 px"

### 4. illustrator_bridge.py
- Defaults width/height de 1181/1654 a 2000/2800

### 5. Contraportada base regenerada
- svg/suplementos_rd/04_contraportadas/01_contraportada_base_10x14cm.svg
- Dimensiones: 2000x2800 px (10x14 cm)
- Placeholders correctos para generacion dinamica

## Archivos modificados

- src/flujo/comercial/svg_validator.py
- src/flujo/export/illustrator.py
- src/flujo/cli.py
- src/flujo/export/illustrator_bridge.py
- svg/suplementos_rd/04_contraportadas/01_contraportada_base_10x14cm.svg

## Verificacion

py -m pytest tests/test_svg_illustrator_integration.py -q
py -m compileall src/flujo
