# vaso semantico

Sistema generativo que lee un repositorio git y produce un SVG autoanimado
(CSS + SMIL, sin JavaScript). Sesion de trabajo trasladada desde el entorno
de Claude.

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`  (solo numpy)
- `git` en el PATH
- Un clon COMPLETO (no shallow) del repo a leer

Para las capturas, opcionalmente: `npm i playwright && npx playwright install chromium`

## Preparar el repo fuente

    git clone https://github.com/ligereza/vibecodeine /ruta/vibecodeine

Si ya lo tenias en shallow:  `git fetch --unshallow`

## Correr

Todos los scripts viven en `sistema/` y se importan entre si, asi que hay
que ejecutarlos DESDE esa carpeta.

    cd sistema
    python3 union.py --repo /ruta/vibecodeine --salida ../salidas/union.svg

Abrir el `.svg` directo en el navegador. No necesita servidor.

## Los archivos, en orden de construccion

| archivo | que hace |
|---|---|
| `motor.py` | base. Historia del repo, campo semantico (co-ocurrencia -> PPMI -> PCA), contorno radial, SMIL. Todos los demas lo importan. |
| `relieve.py` | trata el campo como mapa de altura. Depth map, normal map, relieve ascii iluminado sin frames (fase = animation-delay negativo). |
| `sombra.py` | raycasting por celda. Horizon mapping. Correcto pero pesa 645 KB. |
| `oclusion.py` | la misma sombra comprimida por rotacion ciclica (k-means con distancia ciclica). 7.8 KB. Es la version que se usa. |
| `cableado.py` | el netlist PPMI ruteado con A* ortogonal sobre la grilla de caracteres. |
| `polos.py` | define el 0 y el 255: error (persistencia) menos placer. `H = max(E - P, 0)`. |
| `sintesis.py` | primera reintegracion. **Tiene tres mentiras conocidas**, ver `projects/cultura/doublecup/svg/doc/auditoria.md`. Se conserva como registro. |
| `union.py` | **la pieza actual.** Las tres mentiras corregidas. |

## Parametros que valen la pena tocar

En `union.py`:

- `CICLO_HIST` (26.0 s) duracion del recorrido por la historia
- `PULSO_MIN` / `PULSO_MAX` (2.6 / 9.0 s) velocidad del pulso: fuerte / debil
- `OP_SUSTRATO`, `OP_TERRENO`, `PISO_PULSO` contraste
- `--estados N` cuantos momentos de la historia se muestrean

En `motor.py` (`Params`): `filas`, `cols`, `sigma`, `u_vidrio`, `u_liquido`.
`u_vidrio` y `u_liquido` son umbrales ABSOLUTOS a proposito: por eso el area
crece con la historia en vez de quedar fija.

## Estado actual y lo que queda abierto

- `union.svg` pesa 620 KB (60 KB gzip). El costo real no es el peso sino el
  DOM: ~8.500 `<tspan>` y ~8.000 animaciones activas.
- Con la altura honesta, el vaso se descentro: la cicatriz del repo esta en
  `context / src / flujo / tests / handoff`, y el circuito de HEAD habla de
  otra cosa. Solo el 3.7% del cobre cae dentro de la forma. Es un hallazgo,
  no un bug.
- Sin construir: `servidor.py`, el modo de regeneracion por visita.

## Regla heredada del repo

`arte-ascii-readme.svg` es obra terminada. No se altera. Cualquier tejido
nuevo va a archivos nuevos.
