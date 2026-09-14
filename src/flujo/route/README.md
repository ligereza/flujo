# flujo hub route — Router de rutas de RD (no mueve archivos)

Herramienta del repo que resuelve **donde esta / donde trabajar / donde entregar**
cada pieza dentro de `C:\rd`, **sin mover ni renombrar nada** (para no romper
enlaces de Blender/Photoshop). Lee un indice (`rutas_rd.json`) que mapea la
estructura real existente.

## Idea

- Division por **contenido**: `EVENTOS` o `SUPLEMENTOS` (igual que el intake de flujo).
- `AUTOMATIZACION` es la **cuna**: donde se produce/trabaja antes de entregar.
- El **tipo de pieza** (flyer, pendon, etiqueta, post, render, logo) define la subruta.
- Piezas transversales (logo, paleta, textura, propuesta) no necesitan area.

## Comandos

```
py -m flujo hub route where --area eventos --pieza flyer
py -m flujo hub route where --area suplementos --pieza etiqueta --que entregar
py -m flujo hub route where --pieza logo            # transversal (sin area)
py -m flujo hub route where --area eventos --pieza flyer --json
py -m flujo hub route cuna                           # pipeline AUTOMATIZACION
py -m flujo hub route doctor                         # verifica rutas (solo lectura)
```

`--que` puede ser `buscar` | `trabajar` | `entregar`.

En Linux, define `FLUJO_RD_ROOT=/home/mak/RD` o pasa `--base-dir /home/mak/RD`
para adaptar la raiz historica `C:\rd` al arbol local. El indice no se modifica.

## Que NO hace

- No mueve, no copia, no borra, no renombra. Solo devuelve rutas.
- No adivina EVENTOS vs SUPLEMENTOS: lo decides tu (igual que el asunto del correo),
  porque un mismo pendon/flyer puede ser de cualquiera segun su contenido.

## Archivos

```
src/flujo/route/__init__.py     expone resolver_ruta, cargar_indice
src/flujo/route/resolver.py     logica + CLI
src/flujo/route/rutas_rd.json   indice de rutas reales de C:\rd (editable)
```

## Mantener el indice

Si agregas una carpeta nueva en `C:\rd`, editas `rutas_rd.json` (es la unica
fuente de verdad). Corre `doctor` para verificar que todo exista.
