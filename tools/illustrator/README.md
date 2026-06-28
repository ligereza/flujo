# Illustrator tools - Logo Clean Master

Esta carpeta contiene scripts locales para Adobe Illustrator usados por `flujo`.

## Script incluido

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

## Objetivo

Limpiar logos/palabras ya hechas sin redibujarlas:

- alinear nodos casi verticales/horizontales;
- enderezar segmentos casi H/V;
- cerrar solo handles del segmento recto, no del nodo completo;
- preservar curvas vecinas en B/R/P/D;
- corregir tangentes evidentes en letras redondas;
- eliminar puntos extra solo en tramos rectos.

## Uso en Illustrator

1. Convertir texto a contornos si corresponde:

```txt
Type > Create Outlines
```

2. Seleccionar palabra, letra o logo.
3. Ejecutar:

```txt
File > Scripts > Other Script...
```

4. Elegir:

```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

## Modos del script

```txt
A = Audit, no modifica
W = Word, escribir palabra
M = Micro, sin palabra
O = Ortho, tratar seleccion como recta
R = Round, tratar seleccion como curva/redonda
```

## Reglas aprendidas

- No usar baseline global automatico: deforma letras.
- No forzar diagonales a 45 grados.
- No cerrar todos los handles de un nodo en letras mixtas.
- Para un segmento recto p1 -> p2, cerrar solo `p1.rightDirection` y `p2.leftDirection`.
- Para redondas, corregir tangentes solo en extremos evidentes.
- Si el resultado no gusta, usar `Ctrl+Z`.

## Estado

Proyecto experimental. No es herramienta final.
