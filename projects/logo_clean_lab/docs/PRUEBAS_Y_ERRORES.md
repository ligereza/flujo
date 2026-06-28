# Pruebas y errores - Logo Clean Master

Este documento resume lo aprendido durante la exploracion de scripts para limpiar logos en Illustrator.

## Intento 1 - alinear nodos seleccionados

Funciono parcialmente.

Ventaja:
- alineaba nodos seleccionados por X/Y.

Problema:
- dependia demasiado de seleccionar manualmente;
- no entendia palabra completa;
- no eliminaba puntos extra.

## Intento 2 - optimizador geometrico

Se intento limpiar grilla, segmentos y puntos redundantes.

Ventaja:
- util para vectores sucios.

Problema:
- demasiado generico;
- podia tocar curvas que no debia.

## Intento 3 - autoclean por palabra

Se intento calcular tolerancias y alinear palabra completa.

Error importante:
- alinear baseline/cap-height global deformo letras;
- las redondas pueden tener overshoot optico;
- mover extremos globalmente puede aplastar O/C/S.

Conclusion:
- no usar baseline global automatico por ahora.

## Intento 4 - letter logic

Se intento clasificar letras como ORTHO, ROUND, ANGLED, MIXED.

Ventaja:
- escribir la palabra da informacion util;
- una E debe tratarse distinto a una O.

Problema:
- clasificacion automatica por geometria no siempre basta;
- letras compuestas dependen de como Illustrator agrupe contornos.

Conclusion:
- modo Word sirve, pero debe ser conservador.

## Intento 5 - cerrar handles en letras rectas

Se detecto que una linea podia quedar alineada, pero el handle seguia curvando hacia afuera.

Solucion inicial:
- cerrar handles del nodo.

Error:
- en B/R/P/D, un nodo puede pertenecer a un segmento recto y a una curva;
- cerrar todos los handles del nodo mata la curva vecina.

Conclusion:
- nunca cerrar ambos handles del nodo por defecto.

## Decision actual correcta

Para un segmento recto `p1 -> p2`, cerrar solo:

```txt
p1.rightDirection
p2.leftDirection
```

No tocar:

```txt
p1.leftDirection
p2.rightDirection
```

Esto preserva curvas vecinas.

## Reglas actuales del script consolidado

- No redibujar.
- No forzar diagonales.
- No alinear palabra completa globalmente.
- No cerrar todos los handles de nodos mixtos.
- Si se detecta segmento recto, cerrar solo handles del segmento.
- En ROUND, corregir tangentes solo en extremos evidentes.
- Eliminar puntos solo si estan en tramo recto y sin handles reales.

## Como reportar una prueba

Ejemplo:

```txt
modo: W
palabra: BRAND
resultado: B perdio curva / R bien / A bien / D mal
nota: no cerrar handles en nodos mixtos
aprobado: no
```

O en JSONL:

```json
{"sample":"brand_001","mode":"W","word":"BRAND","approved":false,"note":"B perdio curva; evitar colapsar handles completos"}
```
