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
| `testeo_*` | `data/rd_fuentes/testeo_eventos_*_evidence.json` (evidencia pendiente de revision) |

## Los testeos historicos

**Son TRES periodos, no uno.** El loader hace glob sobre
`testeo_eventos_*_evidence.json` y fusiona: hoy 2024 (25 jornadas), 2025 (38) y
las jornadas 2026 que se siguen anotando en el mismo archivo (4). Cualquier
cosa que diga «la evidencia 2025» esta desactualizada.

Cada JSON lo produce `tools/importar_testeo_xlsx.py` desde el libro de Drive.

### Por que la planilla necesita un importador y no un `read_excel`

La planilla se hereda de un evento al siguiente: cada voluntario copia la hoja
de la jornada anterior y sobrescribe filas. Lo que no alcanza a sobrescribirse
queda como muestra que nadie testeo. Por eso cada fila trae:

- `row_duplicate_status`: `first_occurrence` | `repeat_within_sheet` |
  `copied_from_other_sheet`
- `copied_from_sheet`: de que jornada vino el tramo

**Nada se descarta: se marca.** De 2.762 filas fuente, 1.726 son anotaciones
propias. Quien consuma estas tablas tiene que filtrar por `first_occurrence` o
declarar que no lo hace; un `COUNT(*)` a secas cuenta la planilla, no el
terreno.

### Vocabularios cerrados, y lo que NO hacen

- `colorimetria.py` -- color observado. Separa el color de la MUESTRA del color
  del TEST (`Cupra morada` en la columna de resultado es la pastilla, no una
  reaccion) y marca aparte la identidad y el veredicto escritos donde va una
  observacion.
- `ensayos.py` -- reactivo y sustancia declarada. **Solo ortografia**: une
  `simon`/`simons`/`simon's`, une `tusi`/`tussi`/`tu si`. No dice que significa
  un color ni que sustancia hay.

Un ensayo es: *el reactivo X dio el color C sobre una muestra que alguien
declaro como S*. El veredicto lo da la persona a cargo de la mesa, verbalmente,
y no queda registrado. Ninguna capa de codigo debe inventarlo.

### Trampa conocida: la tabla `reactivos` tiene filas retractadas

`reactivos` (7 reactivos curados) trae la linea
`Liebermann / cocaina cortada (levamisol o lidocaina) / rojo oxido`.
**DanceSafe ya no recomienda usar Liebermann para eso**, y la auditoria interna
de `docs/rd/prototypes/2026-08-11/rd_reactivos_auditoria_internacional_*.md`
lo retracta explicitamente, junto con reglas rigidas de Marquis sobre cocaina y
de Zimmermann sobre benzodiacepinas.

Esa auditoria **no esta cargada en la base**: `rd_fuentes_registro` tiene cuatro
fuentes y ninguna es ella. Hay ademas 12 reactivos en
`rd_reactivos_candidatos` (Morris, Zimmermann, Robadope, Simon's, CBD:THC,
Hofmann) que nunca se promovieron a `reactivos`, con sus reacciones en
`rd_reacciones_candidatas` pero sin color. No trates `reactivos` como el
catalogo completo ni como el vigente.

Las tablas `testeo_*` no se mezclan con `registros_testeo` de la base
acumulativa y no habilitan afirmaciones publicas automaticas: un color es una
senal presuntiva de presencia, no identidad, pureza, dosis ni seguridad.

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
