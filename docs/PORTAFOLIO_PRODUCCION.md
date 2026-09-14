# Producción de portafolio en MAK

Estado: **doctrina de un dominio — cómo se produce un portafolio. Fechada
2026-08-28. No está en el orden de lectura** (`agents.md` →
`docs/MAK_CURRENT_STATE.md` → `context/LAST_HANDOFF.md`). No gobierna el resto
de MAK. Ver `docs/AUTORIDAD.md`.

Reemplaza la práctica anterior de certificar incapacidad sobre el archivo antes
de producir cualquier cosa. Si la sesión se corta, un agente siguiente debe
poder continuar sólo con esto más `context/LAST_HANDOFF.md`.

## Dónde vive la evidencia que este documento usa

Las rutas completas, porque citarlas por nombre pelado fue el defecto que se
corrigió el 2026-08-28 en todo el repo:

| Evidencia | Ruta real |
|---|---|
| Decisiones humanas (5 archivos) | `/home/mak/plataforma/director_runs/portfolio-editor-20260808/` — `selections.jsonl`, `classifications.jsonl`, `connections.jsonl`, `copilot_feedback.jsonl`, `copilot_external.jsonl` |
| Rasgos de máquina | `/home/mak/plataforma/director_runs/portfolio-editor-20260808/vision_features.jsonl` |
| ScreenSetups de Resolume | `/media/mak/PortableSSD/*.xml` (9 documentos, incluido `CHILLAN.xml`) |
| Formatos declarados | `data/portfolio_formats/*.json` |
| Contenedores de práctica | `data/portfolio_practices.json` |
| Atestaciones | `data/portfolio_attestations.json` |
| Productos compilados | `out/portfolio/` |

Están **fuera del repo** y por eso no las alcanza ningún test de higiene. Su
procedencia se conserva de otra forma: `out/portfolio/human_decisions.json`
registra ruta, `sha256` y número de eventos de cada una. Verificado el
2026-08-28: los cinco archivos existen y **los cinco hashes coinciden** con lo
registrado (84, 99, 32, 20 y 32 eventos). Esa es la única razón por la que las
14 relaciones de `out/portfolio/F7-lectura-curatorial.md` son auditables.

---

## 1. Diagnóstico: qué estaba mal

El sistema trataba los archivos como el sustrato del que están hechas las
entidades, cuando son **evidencia sobre entidades que existen
independientemente**. Una canción existió, un show ocurrió, un cliente pagó.
Nada de eso deja de ser cierto porque no se pueda hashear un mp4.

De esa inversión salieron tres fallas encadenadas:

1. **Una sola relación como join universal.** Identidad de bytes usada para
   responder preguntas de obra, comisión, autoría, rol y presentación, que son
   cinco preguntas distintas.
2. **`unknown` global en vez de local.** Cualquier incertidumbre abajo apagaba
   todo arriba, y su único canal de resolución era una pregunta al usuario.
3. **Ninguna noción de suficiencia relativa al propósito.** La barra se puso en
   la afirmación más fuerte posible (autoría defendible ante un jurado) y se
   aplicó a la más débil (mostrar una imagen en una grilla).

Consecuencia medida: ocho ciclos de trabajo, 3.769 tests, dos episodios, cero
productos. El loop de aprendizaje quedó cerrado sobre metadata propia.

Y una falla de proceso: **no se leyó `/home/mak/.codex/memories/MEMORY.md`**, de
modo que se redescubrieron hechos ya documentados
(`path_token_context_only` para HARRY, los contact-sheets como derivados no
duplicados, la separación título/portada/filename de xPedrito).

---

## 2. Las ocho capas

Una afirmación pertenece a exactamente una capa. Nunca se promueve entre capas.

| # | Capa | Qué afirma | Qué NO afirma |
|---|---|---|---|
| 1 | `physical` | qué bytes existen, dónde, y cómo cambian | nada semántico |
| 2 | `content` | qué archivos son copias, versiones o derivados | que sean la misma obra |
| 3 | `process` | qué archivos se usaron, editaron, exportaron | quién los hizo |
| 4 | `work` | qué producto artístico existe con independencia de sus fuentes | de quién es |
| 5 | `context` | canción, álbum, show, fiesta, marca, cliente, encargo, publicación | que la persona participara |
| 6 | `role` | autor, diseñador, VJ, editor, productor, colaborador, proveedor, tercero | calidad ni valor |
| 7 | `presentation` | cómo aparece una obra en un portafolio concreto | identidad de la obra |
| 8 | `curatorial` | por qué conviene mostrar dos elementos juntos para un propósito | verdad artística |

**Regla central:** la ausencia de relación entre dos archivos no implica ausencia
de relación entre sus contextos.

> No atribuir un archivo ≠ eliminar el contexto.

Caso que fija la regla: la visual de *Escarlata* la hizo un tercero y estaba en
el archivo por contexto profesional. Se excluye la autoría de esa visual y se
**conserva** la red Dref–Harry–BAH, que es verdadera.

Segundo caso: `pantalla antesala.psd` de ARICA es un documento nativo enviado
sólo para extraer un logo. Por lo tanto **`archivo nativo ⇏ proceso propio`**.

---

## 3. Los cinco verbos

Toda afirmación utilizable en un portafolio es una de cinco. Son universales al
rubro: aplican igual a un VJ, un barbero, un fotógrafo o un investigador.

| Verbo | Capa dominante | Ejemplo |
|---|---|---|
| `puedo` | process + role | «puedo producir visuales de show a esta escala y en estos plazos» |
| `hice_esta_parte` | role | «hice el compositing, no el 3D» |
| `ocurrio` | context | «atendí en este local entre 2019 y 2023» |
| `significa` | curatorial | «mi trabajo va por acá» |
| `es_mio` | work + role | «este diseño es mío» |

---

## 4. Estados de una afirmación

Un estado es el **resultado de una prueba nombrada**, nunca confianza
autoasignada. Estado y fuerza de evidencia son dimensiones distintas:
`candidate` no es evidencia débil, es una proposición todavía abierta.

| Estado | Condición externa al inferidor | Cómo se refuta |
|---|---|---|
| `observed` | medición reproducible sobre una fuente identificada | otro lector demuestra que el contenido, metadata o referencia no existe |
| `candidate` | una regla explícita produjo una hipótesis | contradicción, evidencia negativa, o desaparición de la condición que la generó |
| `supported_candidate` | una segunda ruta **independiente** apoya la misma proposición | fuente independiente contradictoria, o invalidación de una de las rutas |
| `externally_attested` | persona, contrato, crédito o fuente oficial **nombrada** afirma algo | retractación, contrato contrario, fuente más autorizada |
| `certified` | sólo para estados técnicos verificables por procedimiento definido | fallo de hash, firma, replay, schema o autoridad certificadora |

**Invariante anti-autocertificación:**

> Ninguna ruta puede promocionar la afirmación que ella misma generó.

Techos duros por verbo:

- `es_mio` y `hice_esta_parte` **no pasan de `candidate`** sin recibo de tercero
  (contrato, crédito, factura, carta, testimonio nombrado). El archivo no puede
  probarlos solo.
- `process` satura en `uses=supported` con `output_role=unknown`. Prueba uso, no
  autoría. Ya medido en la cadena C04–C06.

---

## 5. Permiso de presentación

Capa independiente de autoría y de evidencia. Es la única donde equivocarse
lastima a un tercero, y por lo tanto la única donde la abstención es correcta.

| Permiso | Significado |
|---|---|
| `public` | mostrable con nombre |
| `unnamed` | mostrable sin nombrar cliente, marca o persona |
| `aggregate_only` | mostrable sólo agregado, nunca por caso |
| `prohibited` | no mostrable |

RD (Reduciendo Daño) opera con datos de campo **agregados y anónimos por
diseño**; su store privado `data/rd_datos.db` está declarado
`rd_private_runtime_boundary` con la regla *«RD privacy data is not copied into
MAK learning memory»*.

---

## 6. Alcance y reversibilidad

La incertidumbre se paga en **alcance**, no en una pregunta al usuario ni en un
default silencioso masivo.

Una decisión es reversible sólo si su propagación también lo es:

```
R(d) = alcance conocido
     + dependencias enumeradas
     + invalidación ejecutable
     + recomputación acotada
```

Una decisión provisional automática puede actuar sólo si:

1. está limitada a un producto o vista;
2. no modifica identidad ni evidencia;
3. su procedencia se puede reconstruir;
4. sus consumidores quedan registrados;
5. puede invalidarse y regenerar esos consumidores;
6. no se usa como etiqueta de entrenamiento;
7. una contradicción posterior crea memoria negativa.

**Mapa de riesgo correcto:**

- Reversible e interno (qué sección, qué orden, qué epígrafe, qué variante):
  se decide siempre y no se pregunta.
- Irreversible o hacia afuera (reclamar autoría en una postulación firmada,
  publicar a un tercero, nombrar bajo NDA, enviar): se abstiene.

La instrucción del usuario es explícita y repetida: *«MI ARCHIVO YA SON AÑOS DE
TRABAJO y OBRAS terminadas, no hace falta mas input ni revision»*,
*«AUTOMATIZADOOOO»*, *«do not wait for continúa»*. La revisión humana es
supervisión opcional, no la compuerta de rutina.

---

## 7. Formato de portafolio: la planta declarada

Un formato es el objeto que hace autónomo a MAK: declara la meta, permite el
autochequeo, y responde factibilidad **antes** de producir.

Contrato: `mak-portfolio-format-v1`. Los formatos viven en
`data/portfolio_formats/*.json` como datos, nunca en código.

Cada ranura declara:

```
slot_id            identificador estable
title              encabezado visible
count              mínimo y máximo de ítems
claim              uno de los cinco verbos
min_state          estado mínimo aceptable
permission         permiso mínimo aceptable
caption_grammar    plantilla con los campos permitidos
required           si el documento es inválido sin ella
```

Y el documento declara: consumidor, propósito, idioma, límites de tamaño y
cantidad, ranuras obligatorias, y **qué lo invalida**.

Corrección importante: **la rúbrica de una convocatoria no es la planta.** Es el
terreno y parte del clima.

```
P* = argmax  U_curatorial(P)
       sujeto a  H_administrativo(P) = 1
```

Las condiciones duras (elegibilidad, fechas, presupuesto, documentos) definen el
espacio factible. Las preferencias evaluativas (claridad, impacto, coherencia)
**no sustituyen la posición curatorial**. La convocatoria produce un dossier
adaptado; no se convierte en la ontología del archivo.

Ejemplo que fija el límite: una lógica administrativa pediría que título de
plataforma, texto de portada y canción coincidan para maximizar legibilidad. La
propuesta de xPedrito es precisamente separar esas capas. Se llena el campo
obligatorio del formulario sin permitir que la base reescriba la obra.

---

## 8. El catálogo de formatos

Cinco afirmaciones ⇒ cinco familias. Un formato es (familia × práctica ×
consumidor).

| # | Formato | Verbo | Estado mín. | Consumidor | ¿Empates SSD? |
|---|---|---|---|---|---|
| F1 | Registro de trayectoria | `ocurrio` | `observed` | alimenta F3, F4, F5 | ninguno |
| F2 | Capacidad · visual para música y eventos | `puedo` | `observed` | mánager, sello, productora | ninguno |
| F3 | Rol técnico | `hice_esta_parte` | `candidate` | estudio, agencia, colaborador | ninguno |
| F4 | Fondo público chileno | mixto | `supported_candidate` | jurado | 2–3, sólo de lo incluido |
| F5 | Beca o residencia internacional | `es_mio` | `externally_attested` | comité extranjero | sí, más cartas |
| F6 | Registro institucional RD | `ocurrio` | `observed` | la ONG, rendición | ninguno; **permiso manda** |
| F7 | Lectura curatorial | `significa` | `candidate` | curador, festival | ninguno; requiere posición del autor |

**F1, F2 y F3 no necesitan resolver un solo empate del SSD.** Los 50 empates
bloqueaban sólo porque se asumió que todo portafolio es el autoral.

El formato adversarial de generalización es **F2-barbero**: mismas cinco ranuras,
mismos cinco campos, evidencia completamente distinta y permiso dominante. Si el
mecanismo lo aguanta sin tocar código, generaliza.

---

## 9. Núcleo general y gramáticas verticales

```
núcleo general de evidencia  +  gramáticas verticales de demostración
```

El núcleo es general y ya está probado como tal: `archive_reconstruction` con
`Evidence` / `Decision` / `UnitRelation` corrió sobre DREF, HARRY y MYRA sin
reglas específicas de caso, sin fusiones falsas y con pérdida cero. Eso es
transferencia medida.

Las gramáticas de demostración son verticales y **no** deben unificarse:
`transformacion` (barbería, restauración), `practica_o_corpus` (fotografía,
ilustración), `experiencia` (VJ, escena, evento), `resolucion` (dev, consultoría,
derecho), `ecosistema` (productor cultural, ONG), `investigacion`.

La generalidad se descubre **después** de producir ejemplares, no se impone
antes. La vertical primaria de este archivo es
`experiencia + practica_o_corpus + ecosistema`.

Límite honesto: la generalidad está probada **debajo** de la línea de cultura
(observación, memoria, reconstrucción, Project IR). Arriba de esa línea no se ha
producido ningún producto para ningún caso.

---

## 10. Qué significa producir

No es validar un contrato ni emitir un reporte. Es:

1. seleccionar y componer, asumiendo el costo de lo que queda fuera;
2. proponer varias lecturas en vez de una verdad;
3. operar cada relación en su capa correcta;
4. descartar el atajo falso sin descartar la pieza;
5. construir narrativa y formato;
6. entregar algo que alguien usa;
7. registrar qué resultado tuvo cuando alguien lo usó.

Un episodio de aprendizaje necesita cuatro campos que los anteriores no tenían:
**propósito, variante producida, decisión del consumidor, resultado observado.**

No se acepta como aprendizaje un cambio de hash, un JSON distinto ni un episodio
nuevo si ningún consumidor tomó una decisión mejor.

---

## 11. Módulos y contratos

| Contrato | Módulo | Rol |
|---|---|---|
| `mak-portfolio-format-v1` | `src/flujo/knowledge/portfolio_format.py` | valida y carga la planta declarada |
| `mak-portfolio-claims-v1` | `src/flujo/knowledge/portfolio_claims.py` | proyección: afirmaciones con verbo, capa, estado, permiso, alcance, refs |
| `mak-portfolio-render-v1` | `src/flujo/knowledge/portfolio_render.py` | formato + afirmaciones → documento, con factibilidad previa |

Reutiliza y no reemplaza: `product_view.py`, `practice_evidence_state.py`
(`CLAIM_STATUSES`, `DIMENSIONS`), `product_plan.py` (`mak-product-plan-v1`,
la capa interpretativa que faltaba nombrar), `portfolio_dossier.py`,
`project_ir.LearningStore`. **Sin segunda base, segundo endpoint, segundo
crawler ni registro paralelo.**

---

## 12. Ritual retirado

| Pieza | Disposición |
|---|---|
| Orden de revisión de 917 proyectos | retirado: ningún consumidor lo lee |
| Cola de 50 preguntas al operador | retirada: contradice instrucción explícita del usuario |
| Prosa de abstención creciente | retirada |
| Selección de 8 por `class=obra` | retirada: es un filtro de fuente vestido de curaduría |
| 26 tests que premian negarse | invertidos: deben premiar sostener una lectura defendible |

Se conserva: el Hub read-only en `/api/portfolio/archive-view`, la procedencia
por hash, la triangulación de fuentes en modo lectura, y la maquinaria de tesis
en competencia **sólo si compite sobre propósitos y composiciones**, no sobre el
esquema de la propia proyección.

---

## 13. Hallazgos de la triangulación del SSD

El SSD está montado en `/media/mak/PortableSSD`. Leerlo cambió el resultado.

### Los 9 XML de la raíz eran la mejor evidencia del archivo

Estaban clasificados `indexed_only` porque el índice no guarda contenido. Son
**exportaciones de ScreenSetup de Resolume Arena 7**: el mapeo de proyección de
cada sala.

| Archivo | Lienzo | Pantallas | Slices | Nombres de pantalla | Días internos |
|---|---|---|---|---|---|
| BERLIN 1 | 3043×272 | 4 | **59** | pista modificada, pista original, club modificacion | 2024-09-18 → 2025-07-30 |
| la | 1920×1080 | 3 | 18 | Screen 1–3 | 2025-10-23 → 2026-01-03 |
| cobquecura | 3840×1664 | 2 | 12 | Screen 14, 15 | 2026-02-25 → 2026-02-26 |
| CHILLAN | 3400×1920 | 1 | 11 | Screen 2 | 2026-02-06 → 2026-05-29 |
| harry | 1080×1920 | 1 | 11 | Screen 2 | 2026-02-06 → 2026-05-29 |
| berlin 2 | 1920×1080 | 2 | 9 | nuevo map, club | 2025-08-06 → 2025-12-07 |
| KAYAKAZE 2025 2 | 1792×768 | 1 | 7 | CENTRAL | 2024-08-02 → 2024-12-31 |
| Black Boss Estandar TEMUCO | 1920×1080 | 2 | 5 | Pantalla Led, Teles | 2025-01-16 |
| ANDACOLLO | 1920×1080 | 2 | 4 | Screen 1, 2 | 2026-02-13 |

Total: **136 superficies con warp bezier en 18 pantallas**, entre 2024-08 y
2026-05. Es evidencia de práctica en vivo, y una herramienta generativa no
produce un mapeo coherente.

**Fiabilidad, corregida por el operador.** Un *guardar-como* arrastra el nombre
del documento y los ids de las pantallas conservadas. `CHILLAN.xml` declara
internamente `harry`: eso es **etiqueta obsoleta**, no un vínculo. Los días
internos fechan *una configuración*, y pueden preceder al uso real del archivo.
El módulo declara `label_reliability` y `dating_reliability` por archivo.

Lo que sostiene la relación Harry↔Chillán es la **atestación del operador**, no
el nombre interno.

### La autoridad externa resolvió las identidades

`data/artist_discographies.json` ya lo decía y nadie lo había leído:

| Contenedor | kind | canonical_name |
|---|---|---|
| DREFGIRA | music_artist, confirmado | **DrefQuila** |
| DREFMOVISTAR | **event**, confirmado | DrefQuila — evento |
| HARRY | music_artist, confirmado | Harry Nach |
| LYON | music_artist, confirmado | Lyon La F |
| MARLONLOLLA | music_artist, confirmado | Marlon Breeze |
| SCD | **venue**, probable | Salas SCD |
| FELINA | unknown, sin URLs | — |

La autoridad declara `canonical_name=DrefQuila` para el contenedor `DREFGIRA`.
Eso colapsa la lectura «dos clientes distintos» del empate DREFGIRA↔DrefQuila,
sin decidir si son el mismo encargo.

### Clasificación corregida de los 101 contenedores

Dos errores propios, encontrados y arreglados:

- `abril2026post` no era una secuencia de frames: sus «números» son **ids de
  medio de plataforma de 17 dígitos**. Es material publicado (1.809 mp4, 601
  jpg, 32 subtítulos) → `published_export`.
- 40 «contenedores» eran **archivos sueltos en la raíz del volumen**, no
  contenedores.

Resultado: 25 `production`, 10 `delivery`, 1 `published_export`, 1
`render_output`, 1 `source_footage`, 2 `installed_tool` (NestDrop y Loopback:
inventario de herramienta, no obra), 40 `loose_root_file`, 17
`system_metadata`, 4 `indexed_only`.

## 14. Estado de producción

Compilado con `tools/compile_portfolio.py`:

- **279 afirmaciones**: 175 `observed`, 77 `candidate`, 25
  `supported_candidate`, 2 `externally_attested`.
- **F1-trayectoria**: renderizado, 30 ítems.
- **F2-capacidad · visual para música y eventos**: renderizado, 24 ítems en 5
  secciones. Cifras reales: Blender 927 proyectos nativos en 19 contextos
  2016–2026; After Effects 408 en 16 contextos.
- **F3-rol-técnico**: renderizado, 16 ítems en 4 secciones.
- **F2-capacidad-barbería**: **no factible**, y eso es correcto — este archivo
  no tiene evidencia de barbería. Cargó sin tocar código: la prueba de
  generalización pasa.

Bugs de producto encontrados y corregidos al mirar el documento renderizado:
presupuesto de ítems que dejaba sin cupo a la última ranura obligatoria; la
misma afirmación apareciendo en dos ranuras; herramienta dominante calculada
alfabéticamente (decía *After Effects* para LYON, donde 426 de 559 son
Blender); escala sin nombrar el contenedor; concordancia de plural.

## 15. Progreso

- [x] Registro durable escrito
- [x] Especificaciones de formato F1, F2, F3 y F2-barbería como datos
- [x] `portfolio_format.py` con validador y techos por verbo
- [x] `portfolio_claims.py` con verbos, estados, permiso, alcance y refutación
- [x] `screen_setup_evidence.py` — lectura por contenido, con fiabilidad declarada
- [x] Atestaciones de autoridad nombrada (`data/portfolio_attestations.json`)
- [x] Partición del SSD en prácticas con base escrita y reversible
- [x] `portfolio_render.py` con factibilidad previa y asignación exclusiva
- [x] Tres documentos reales renderizados
- [x] 22 tests que premian producir (`tests/test_portfolio_production.py`)
- [x] Episodio con los cuatro campos, con consumidor y resultado en `pending`
- [x] Segundo episodio como hijo del primero, por delta real en la base
- [x] Suite completa: **3.794 passed, 5 skipped, 0 failed**
- [x] F4 transcrito de las bases reales capturadas de Fondart
- [x] `human_decision_log.py`: 66 decisiones y 62 clasificaciones humanas leídas
- [x] Tercer episodio con `consumer_decision=recorded` y línea base de 6,06%
- [x] 31 tests focalizados de producción
- [x] F7 lectura curatorial sobre 13 relaciones publicadas dibujadas a mano
- [x] `require_fields`: filtro por valor de campo en el contrato de formato
- [x] Deuda del scratch cerrada en `data/ssd_evidence/` con manifiesto
- [x] Tres superficies medidas y registradas sin conectar
- [x] Cinco episodios en linaje, el último con la corrección de RD
- [x] Las tres herramientas registradas en `CAPACIDADES.md` según la regla del repo
- [~] **Exponer la producción en el Hub: no se hace, a propósito.**

## 16. Lo que ya existía y no había buscado

Corrección del operador: *«todo lo que pides ya existe, solo que no buscaste».*
Tenía razón, y era el mismo error de toda la sesión — declarar un hueco antes de
leer.

### La demanda real estaba capturada

`experiments/pilots/ARICA-FONDART-2027/runs/enriched/opportunity.json` es un
`mak-opportunity-constraints-v1` completo para
**`fondart-nacional-investigacion-2027`**, con las bases PDF hasheadas y
localizadores de página:

| Criterio | Peso | Página |
|---|---|---|
| Impacto potencial de la actividad transferencia | **0.40** | p.15 |
| Calidad | 0.30 | p.15 |
| Currículo | 0.20 | p.15 |
| Viabilidad | 0.10 | p.15 |

Más **8 compuertas duras** (autorización ministerial de difusión,
cofinanciamiento, incompatibilidades, estudio de campo requerido, FUP completo,
requerimientos mínimos, una sola postulación, actividad de transferencia), **8
documentos requeridos** y un `unknown`: el plazo figura como
`constraint_status_unknown`.

**F4 es ahora una transcripción, no una invención**
(`F4-fondart-nacional-investigacion-2027.json`, 28 ítems renderizados). Y es
honesto sobre su alcance: el archivo alimenta Currículo y parte de Viabilidad —
0.30 del total. Calidad e Impacto de transferencia dependen del proyecto
propuesto, y la línea exige estudio de campo, así que el ajuste de una práctica
audiovisual a esta convocatoria es una decisión del postulante, no un resultado
del documento. Eso es la rúbrica restringiendo y la curaduría proponiendo.

### Las decisiones humanas ya estaban tomadas

`/home/mak/plataforma/director_runs/portfolio-editor-20260808/` contiene el
registro que declaré pendiente. `human_decision_log.py` lo lee:

- **`selections.jsonl`**: 84 eventos, 66 ítems. Estado final: 59 `descartar`,
  4 `seleccionar`, 3 `deseleccionar`. En 4 ítems la persona cambió de opinión.
  **Tasa de selección: 6,06%** — el primer resultado medido que MAK tiene.
- **`classifications.jsonl`**: 99 eventos, 62 ítems, todos `owner: human`,
  `status: human_draft`, `promotion: none`. Campos declarados a mano:
  `ownership` personal/client, `context_kind` artist/client, `purpose`
  expression/commercial, `nature` 2d/3d, `lane` **iskvw/rd**, `triage`
  work/record/review/discard.

Ese vocabulario humano coincide casi exactamente con el modelo: `ownership` es
el verbo `es_mio`, `context_kind` y `lane` son la capa de contexto, y `lane: rd`
confirma RD como práctica en el vocabulario del propio operador. Cinco ítems
tienen declaraciones que pueden elevar una afirmación, y se cargan **conservando
su `human_draft`**: una declaración en borrador es evidencia real de lo que la
persona dijo, y sigue sin ser verdad promovida.

### Y la distinción que importa

La tasa de 6,06% se midió sobre un portafolio **anterior**. El episodio la
registra como `observed_outcome.status=prior_selection_measured` con
`applies_to_these_documents=false`: es la **línea base** contra la que comparar
estos documentos, no su resultado. `learning.complete` sigue en `false`, y ahora
dice qué lo completaría.

## 16 bis. Segunda ronda de búsqueda: qué más había

Seguí buscando en lo que había listado como sin leer. Tres resultados, uno
positivo y dos negativos que valen igual.

### Relaciones curatoriales hechas a mano — sí existían

`connections.jsonl` tiene **24 pares** con relaciones tipadas por una persona,
y `copilot_feedback.jsonl` **12 confirmaciones** suyas. Los tipos se dividen en
dos cosas que se confundían:

| Tipo | Afirma | Pares |
|---|---|---|
| `same_carousel` | estructura de publicación | 4 |
| `same_date_context` | fecha declarada por la fuente | 11 |
| `same_event` | contexto de fuente | 1 |
| `shared_concept` | **interpretación** | 7 |
| `visual_similarity` | **interpretación** | 1 |

La primera clase es cómo se publicó el material; la segunda es la curaduría. Es
la distinción que hace posible **F7-lectura-curatorial**, que renderiza 13 ítems
con las dos secciones separadas por un filtro declarado.

Para lograrlo el contrato de formato ganó un campo: `require_fields`, un filtro
por valor de campo de epígrafe. Verbo, capa y estado no alcanzaban — dos ranuras
pueden tomar el mismo verbo y diferir sólo en lo que la afirmación afirma.

**Y 11 de los 24 pares eran fixtures** (`mak-replay-XX`, `obra-a`). Se excluyen
con una regla positiva —un ítem publicado tiene un id de plataforma numérico
largo— y se cuentan, porque un fixture filtrado a un log de decisiones es un
hecho sobre el log.

### Los 7 informes de fondos — no son demandas

`docs/becas/informes/` parecía una fuente de convocatorias. No lo es, y quedó
registrado en `data/demand_source_assessment.json` con
`verdict=not_usable_as_a_demand`:

- **1 de 7** tiene más de una fuente oficial; **6 de 7** citan documentos de
  metodología en scribd o scholar en vez de portales de fondos.
- **7 de 7** registran errores de ejecución: HTTP 429 y timeouts.
- Uno declara en su cuerpo «26 de octubre de 2023» dentro de un archivo de
  2026-07-22, titula «convocatoria 2027» y lista líneas con plazo ya vencido.
- Cita a DIBAM, organismo reemplazado en 2018.
- Su propio texto admite que no accedió a las bases.

Pertenecen a la misma clase que `copilot_external.jsonl`: propuestas de máquina
que pueden nombrar sus *unknowns* y nunca atestiguan. La diferencia con la
demanda real —bases PDF hasheadas, criterios con peso, localizadores de página—
es exactamente la que la arquitectura codifica.

### Propuestas de máquina

`copilot_external.jsonl`: 32 inferencias curatoriales de `watsonx` (22) y `aws`
(10), con **2 hipótesis y 40 unknowns**. Se cuentan, se nombra el proveedor, y
`attesting=false`. Sólo se leen filas de feedback cuyo proveedor es la persona.

### Deuda cerrada

Los insumos que vivían en el scratch del job están copiados a
`data/ssd_evidence/` con manifiesto y hashes verificados idénticos. La cadena ya
no depende de un tmp que se limpia.

## 16 ter. Tercera ronda: dos correcciones que salieron de leer

### Los datos de campo de RD son ficticios

`docs/becas/caso_mak_rd.md` §5 «Límites declarados» lo dice: *«Los datos de
campo mostrados en demos son ficticios (generados con semilla fija); los
reportes reales sólo existirán con operación real en terreno.»* Y
`data/rd_datos.db` con 0 filas lo corrobora.

Mi declaración de `TABLA_RD` estaba conservadora en la dirección correcta pero
por el motivo equivocado: puse `aggregate_only` por la frontera de privacidad,
cuando además **no existe todavía dato de campo real que mostrar**. Corregido en
la partición, junto con los otros dos límites que el propio anexo declara: el
análisis con reactivos es presuntivo por diseño, y el marco legal está en
validación profesional.

### La plantilla ya advertía sobre los informes

El checklist de `docs/becas/postulacion_base.md` instruye: *«Monto y fechas
cotejados con la fuente OFICIAL del fondo (no con el calendario auto-generado:
verificar URL oficial ese día).»*

Esa advertencia fue escrita antes de esta sesión y **corrobora de forma
independiente** el veredicto de `data/demand_source_assessment.json`. El propio
sistema ya sabía que su calendario auto-generado no era fuente.

### F6 no se escribe

`caso_mak_rd.md` ya es un producto del tipo correcto: anexo técnico para
evaluadores, con una sección de límites declarados que nombra lo presuntivo, lo
pendiente y lo ficticio. Escribirlo de nuevo como formato sería peor que el
original y duplicaría autoridad. Lo que falta de una postulación de RD
—identificación legal, presupuesto, equipo, cifras de campo reales— no es
derivable del archivo.

Registrado en `data/evidence_surface_assessments.json` junto con
`vision_features.jsonl` (33 filas de `aws`, observación de máquina, no
conectada) y `research/corpus/` (1.599 descripciones, `texto_autor=false`, cero
fechas de publicación, no conectada).

**El criterio en las tres:** no se conecta una superficie porque exista. Se
conecta cuando un formato la pide. Y no se escribe un formato cuando el
artefacto humano ya es mejor.

## 17. El patrón del error, para el próximo agente

Cinco veces en esta sesión declaré un hueco que no existía. Vale la pena
listarlas porque es el mismo movimiento, y es el más costoso:

| Declaré | Realidad |
|---|---|
| «el SSD no está montado, no puedo leer los XML» | estaba en `/media/mak/PortableSSD` y eran la mejor evidencia del archivo |
| «falta autoridad externa para las identidades» | `data/artist_discographies.json` las tenía todas |
| «hay que descubrir el rubro» | tres redescubrimientos ya documentados en `/home/mak/.codex/memories/MEMORY.md` |
| «falta una demanda real con sus bases» | `opportunity.json` con las bases hasheadas y localizadores de página |
| «falta una decisión de consumidor» | 66 decisiones y 62 clasificaciones humanas en el editor de portafolio |

La regla que se deriva: **antes de declarar que falta evidencia, buscarla.** El
costo de un `find` o un `grep` es segundos; el costo de construir sobre un hueco
inventado fueron ciclos enteros. Y es la misma raíz que el error arquitectónico:
auditar la ausencia en vez de leer lo presente.

Ya leídos en la segunda ronda: `connections.jsonl`, `copilot_feedback.jsonl`,
`copilot_external.jsonl` y los 7 informes de `docs/becas/informes/` (§16 bis).

Lo que sigue sin leer: **`research/corpus/`** (1.611 capturas, la mayor
superficie sin abrir), `vision_features.jsonl` (rasgos visuales por ítem),
`docs/becas/postulacion_base.md` (plantilla real de postulación para RD, con 10
secciones y checklist) y `docs/becas/caso_mak_rd.md` (anexo técnico que ya es un
producto del tipo correcto, con sección de límites declarados).

## 18. Lo que se decidió no hacer

**No se agrega superficie de Hub para la producción de portafolio.** Las dos
opciones eran un segundo endpoint —prohibido por la doctrina— o inyectar el
producto dentro de `/api/portfolio/archive-view`, que mezclaría dos productos
distintos con consumidores distintos en un solo payload.

Y el fondo: construir UI antes de que exista un consumidor es exactamente el
error de oferta que este rediseño corrige. La entrega hoy son los archivos en
`out/portfolio/`. Cuando aparezca una demanda real, la forma de exponerla la
determina esa demanda.

**No se debilitó `F2-capacidad-barbería` para que pasara.** Es no factible porque
este archivo no tiene evidencia de barbería. Bajar sus mínimos para forzar un
render habría destruido el único test de generalización que existe.

**No se resolvió ningún empate del orden SSD.** Los 50 siguen sin responder, y
ahora es visible que casi ninguno bloqueaba nada: F1, F2 y F3 renderizaron sin
resolver uno solo.
