# Base de datos RD

SQLite consultable con los datos de Reduciendo Dano. Es una **proyeccion
regenerable**, no una fuente de verdad: se construye desde los archivos
canonicos y se puede reconstruir cuando quieras sin desincronizarse.

`data/rd.db` esta gitignored (patron `*.db`): se genera, no se versiona.

## Tablas y sus fuentes

| Tabla | Fuente canonica |
|---|---|
| `reactivos` + `meta` | `projects/cultura/identidad/reactivos.json` |
| `packs` + `inclusiones` | `src/flujo/plano/packs.py` (PACKS) |
| `suplementos` | `projects/piezas_vectoriales/suplementos_rd/01_contenido/contenido_suplementos_rd.json` |
| `productoras` (+ `productora_tipos`/`productora_venues`/`productora_logos`) | `data/productoras/*.json` |
| `venues` | `knowledge/venues/*.yaml` |
| `eventos` | `jobs/**/evento*.json` + `projects/plano/ejemplos/evento*.json` |
| `testeo_*` | `data/rd_fuentes/testeo_eventos_2025_evidence.json` (evidence pending review) |

The 2025 evidence is imported into separate tables
(`testeo_eventos_fuente`, `testeo_filas_fuente`,
`testeo_observaciones_fuente`, and mapping/link queues). It preserves repeated
sheets, unresolved labels, and the workbook hash. It is not mixed with
`registros_testeo` in the accumulative database and does not enable automatic
public claims: a color is a presumptive presence signal, not identity, purity,
dose, or safety.

**Perfil de productora** (`data/productoras/<slug>.json`): ademas de
name/aliases/instagram, cada productora puede traer:
- `tipos_fecha`: lista del vocabulario controlado (`src/flujo/rd/vocab.py`):
  FESTIVAL, HEADLINERS, RAVE, OPEN_AIR, CLUB, AFTER, UNDERGROUND, INFORMATIVO,
  PRIVADO, OTRO. Alias se normalizan; lo que no matchea cae a OTRO.
- `venues`: lista de `{nombre, venue_id?, preferido, estado, notas}`. `preferido`
  marca el reiterado; `venue_id` enlaza a un venue canonico de `knowledge/venues`;
  `estado` = confirmado | inferido | ejemplo.
- `logos`: lista de `{id, knowledge, estado}` enlazando a `knowledge/logos/*.yaml`.

`eventos.pack_sugerido` es una pista DERIVADA (match del numero de voluntarios
contra los packs), por eso vive en la DB y no en la fuente.

Nota: la tabla `eventos` incluye jsons de `jobs/` que son gitignored (jobs
reales locales). En un checkout limpio/CI solo aparece el ejemplo TRACKED de
`projects/plano/ejemplos/`, asi que el contenido de esa tabla depende de la
maquina -- es una DB de operador, no un dato versionado.

## Uso

CLI:
```bash
py -m flujo rd-db build                  # (re)construye data/rd.db
py -m flujo rd-db reactivo --familia MDMA
py -m flujo rd-db reactivo --reactivo Marquis
py -m flujo rd-db packs
py -m flujo rd-db eventos
py -m flujo rd-db testeos              # resumen interno de evidencia importada
py -m flujo rd-db lookup MDMA         # operador en terreno: reactivos + packs con testeo
py -m flujo rd-db productora thegrid  # perfil: tipos de fecha, venues, logos
py -m flujo rd-db venues              # venues canonicos (preset, vol_min)
py -m flujo rd-db por-tipo RAVE       # que productoras hacen ese tipo de fecha
```

`lookup` es el JOIN que justifica la DB sobre JSON planos: cruza la colorimetria
(reactivos) con el servicio (packs que incluyen testeo) en una sola vista.

Python:
```python
from flujo.rd import build_rd_db, reactivos_por_familia, packs, eventos, productoras, disclaimer
build_rd_db()
reactivos_por_familia("MDMA")   # las reacciones cruzadas de cada reactivo
```

Para inspeccion interna de la evidencia importada:

```python
from flujo.rd import testing_evidence_summary, testing_observations
testing_evidence_summary()
testing_observations(reagent_id="marquis")
```

The original workbook remains outside the repository. The versioned record
contains normalized evidence and the source SHA-256 hash; any venue/producer
link and any public interpretation require explicit human review.

## Seguridad del dominio

El test de reactivo es **PRESUNTIVO**: indica una familia de sustancias posible,
no la identifica con certeza ni mide pureza. Un color no vuelve segura una
sustancia. El disclaimer canonico viaja en la tabla `meta`
(`reactivos_disclaimer`) y `disclaimer()` lo devuelve: toda salida que muestre un
color deberia poder citarlo.
