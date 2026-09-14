# flujo index — Indexador estructural para agentes/IA

## Índice estructural Python

`flujo code-index` genera un mapa AST del repositorio para que un agente pueda
ubicar módulos, símbolos, consumidores, imports, entradas y efectos sin leer
todos los archivos fuente. El JSON no contiene texto Python ni secretos y no
modifica el árbol escaneado.

```text
flujo code-index --output context/code_structure_index.json
flujo code-index --query "research provider route" --format markdown
```

El esquema estable es `flujo-code-structure-v1`; para consultas compactas usa
`flujo-code-brief-v1`. Las rutas se calculan desde la raíz indicada y `WIN`,
`.agents`, `.codex`, `.claude`, entornos virtuales, caches y artefactos de
build se excluyen por defecto.

Herramienta de **optimización + búsqueda + índice** del repo. Escanea `C:\rd`
(o un inventario `.txt`) y produce `index_rd.json`: un mapa REAL de qué archivos
hay, dónde, cuánto pesan, qué versiones y duplicados existen, y qué se puede
limpiar. **No mueve, no borra, no renombra — solo lee.**

Su propósito: que un agente/IA **lea el índice primero** y entienda con qué lidia,
en vez de escanear 52 GB a ciegas, para tomar el mejor camino.

## Comandos

```
py -m flujo index build                         # escanea C:\rd -> index_rd.json
py -m flujo index build --hash                  # + md5 (detecta duplicados EXACTOS)
py -m flujo index build --from-inventory inv.txt  # construye desde un inventario
py -m flujo index stats                         # resumen por area/pieza/extension
py -m flujo index find "creatina etiqueta"      # buscar (por relevancia + fecha)
py -m flujo index versions "post fiesta"        # historial de versiones de una pieza
py -m flujo index dupes                         # duplicados exactos / casi-duplicados
py -m flujo index cleanup                       # candidatos a liberar espacio
py -m flujo index agent-brief "tu consulta"     # JSON-resumen para un agente
```

## El comando estrella: agent-brief

Devuelve un JSON compacto pensado para que **otra IA lo consuma**:
- peso total, áreas y su peso, espacio recuperable desglosado
- nº de grupos de duplicados
- mejores coincidencias a la consulta del usuario (con ruta real, peso, fecha, área, pieza)
- recomendaciones tácticas (no mover .blend/.psd, AUTOMATIZACION es la cuna, etc.)

Así un agente sabe **dónde está lo que busca y qué NO debe tocar**, antes de actuar.

## Clasificación

- **Área por contenido**: `suplementos` / `eventos` (prioriza carpeta raíz real:
  `\suplementos\ \gotario\ \prep\` => suplementos; `\febrero\ \creamfields\ ...` => eventos).
- **Pieza**: etiqueta, gotario, pendon, flyer, post, render, logo, render3d…
- **Limpieza**: autosave_blender (.blend1), autosave_ae, backup_temporal (~ / [Recuperado]),
  frames_video, build_cache.
- **basekey**: agrupa versiones de una misma pieza (quita v01/copia/final…).

## Archivos

```
src/flujo/index/__init__.py     API: load_index, find, versions, dupes, cleanup, stats
src/flujo/index/indexer.py      lógica + CLI (ASCII-only)
src/flujo/index/index_rd.json   el índice generado (se regenera con build)
```

## Notas

- Para **duplicados exactos** corre `build --hash` (lee el contenido; tarda más pero
  es 100% fiable). Sin hash, usa "casi-duplicados" (mismo nombre + mismo peso).
- El índice es barato de regenerar: corre `build` cuando cambie mucho `C:\rd`.
- Combina con `flujo route`: `index` dice QUÉ hay y DÓNDE; `route` resuelve a qué
  área/pieza pertenece y dónde trabajar/entregar.
