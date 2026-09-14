# Punto de inflexión: archivo artístico, publicaciones y aprendizaje

**Fecha:** 2026-08-24
**Estado:** registro fechado de un cambio de dirección. **No está en el orden de
lectura** (`agents.md` → `docs/MAK_CURRENT_STATE.md` → `context/LAST_HANDOFF.md`).
Vale como historia del *por qué*, no como estado actual. Ver `docs/AUTORIDAD.md`.
**Alcance:** MAK / `flujo`; no modifica producción, `WIN` ni la base viva

Este documento congela el aprendizaje que cambia la dirección del proyecto.
Su propósito es evitar que una continuación vuelva a interpretar MAK como un
clasificador de carpetas o como un sistema de administración de proyectos.

## 1. La corrección central

MAK no debe aprender principalmente **qué archivo va en qué carpeta** ni
**qué `tool_id` elegir**. Debe reconstruir, con evidencia graduada, un archivo
artístico que pueda responder:

- qué manifestaciones públicas existen;
- qué entregables o piezas visuales/audiovisuales las sostienen;
- qué documentos nativos, escenas, composiciones, capas y fuentes pudieron
  producirlas;
- qué relaciones son seguras, cuáles son hipótesis y cuáles faltan;
- cómo agrupar piezas en obras, series, procesos o líneas de investigación;
- qué vista de portafolio, dossier o postulación se puede construir sin
  inventar intención, fecha, versión, licencia o relaciones de producción.

El producto artístico suele ser una imagen, un video, una secuencia, una
instalación documentada u otra manifestación entregable. Un `.blend`, `.psd`,
`.aep`, proyecto de DaVinci o archivo similar es normalmente una fuente de
producción, una receta, un estado de trabajo o un consumidor de otros assets.
No es automáticamente la obra. El mismo archivo puede aparecer en varias
vistas del archivo sin que eso implique duplicarlo ni moverlo físicamente.

### La autoría del archivo de entrada es una restricción fija

El caso de uso base no es un SSD colectivo con archivos de muchos artistas. Es
un archivo desordenado perteneciente a **un artista**, acompañado por sus
publicaciones y materiales. Por lo tanto, MAK no debe gastar aprendizaje en
resolver “a qué artista pertenece cada archivo”. El `artist_id`/`archive_id`
entra como raíz del lote y se hereda a todas sus observaciones y candidatos.

La incertidumbre está dentro del archivo: qué publicación corresponde a qué
entregable, qué entregable fue producido por qué documento nativo, qué escenas,
composiciones, capas o fuentes participaron, qué archivos son versiones,
procesos, librerías, cachés o entregas, y qué conjunto constituye una obra,
serie o línea de investigación.

Un nombre de persona, una firma o una biografía pueden enriquecer el contexto,
pero no son necesarios para resolver el primer problema de ordenamiento. La
pregunta correcta no es “¿quién es el autor?”, sino “¿desde qué evidencia puedo
relacionar dos nodos del archivo de este autor?”.

La unidad de análisis, por tanto, no es el árbol de carpetas ni el archivo
aislado: es un **grafo de evidencia y transformaciones**.

```text
artist/archive root
              │ restricción global, no etiqueta aprendida
              ├── publicación / post / reel / historia
              │ evidencia de manifestación
              ▼
entregable / imagen / video / secuencia
              │ consumidor nativo, hash, metadata, formato, tiempo
              ▼
composición / escena / timeline / capa / nodo / material
              │ dependencias
              ▼
fuentes / texturas / footage / audio / modelos / referencias
              │ hipótesis semánticas y contexto externo
              ▼
obra candidata / serie / proceso / línea de investigación
              │
              ▼
vista curatorial, dossier o postulación
```

Las flechas son relaciones con evidencia, no afirmaciones automáticas de
identidad. Una relación puede ser `confirmed`, `supported`, `candidate`,
`contradicted` o `unknown`, siempre con referencias a la observación que la
justifica.

## 1.1. Los dos extremos de entrada

No existe un único punto de inicio universal. El archivo se recorre desde el
extremo que tenga la evidencia más fuerte, y luego se busca la relación hacia
el otro extremo.

### Entrada pública

Cuando existe el export de Instagram, la ruta inicial es:

```text
publicación -> media exportado -> coincidencias de entregable local
            -> documento nativo consumidor -> componentes -> fuentes
```

Es la ruta preferida para construir el portafolio porque comienza con algo que
ya fue mostrado. Los embeddings solo reducen la búsqueda entre posibles
coincidencias; la relación se confirma por hash, formato, secuencia, metadata,
consumidor nativo o revisión humana.

### Entrada de archivo

Cuando hay documentos nativos o entregables locales sin publicación encontrada,
la ruta inversa es:

```text
documento nativo / entregable -> output declarado o consumidor
                              -> componentes y fuentes
                              -> publicación buscada o estado unanchored
```

MAK no debe esperar a que exista un post para reconocer un proceso o una obra
candidata. Debe conservarla como `unanchored`, buscar posibles
manifestaciones y producir una pregunta de investigación si la falta de
publicación es material para el portafolio.

### Entrada de proceso

Si solo existe una escena, composición, timeline o conjunto de fuentes sin
entregable reconocible, el punto inicial es el grafo técnico:

```text
fuentes -> componentes -> documento nativo -> output desconocido
```

El resultado es una hipótesis de proceso, no automáticamente una pieza de
portafolio. La ausencia de output es información que debe quedar visible.

La arquitectura, por tanto, es bidireccional en la ingestión pero conservadora
en la semántica: se puede buscar desde ambos extremos, pero nunca se inventa
la arista solo porque el archivo pertenece al mismo artista.

## 2. Invariantes que quedan fijados

### Evidencia, conocimiento y política son capas distintas

1. **Evidencia:** bytes, hashes, timestamps, metadata declarada, export de
   Instagram, referencias nativas, errores de consumidores, registros de
   ejecución, observaciones de una aplicación y fuentes externas.
2. **Conocimiento semántico:** hipótesis derivadas sobre una pieza, obra, serie,
   proceso, tema, técnica, relación o contexto. Tiene procedencia, confianza,
   contradicciones y fecha de revisión.
3. **Política operativa:** qué puede hacer MAK, bajo qué precondiciones, con qué
   validador, costo, riesgo y plan de recuperación.

Una incompatibilidad entre `semantic_rule` y el router no demuestra por sí sola
que la separación conceptual sea incorrecta. Primero hay que distinguir si
falló el contrato de integración, la evidencia, la semántica o la política.
Las reglas no deben convertirse en una autoridad transversal solo porque el
router pueda leerlas.

### No existe una correspondencia uno-a-uno obligatoria

El modelo debe aceptar, sin forzar excepciones:

- una publicación con varios medios, como un carrusel;
- varias publicaciones que muestran una misma obra o versión;
- un entregable derivado de varias composiciones;
- una composición que alimenta varios entregables;
- una obra sin publicación encontrada;
- una publicación cuyo archivo fuente no está disponible;
- archivos de proceso, librerías, cachés, duplicados técnicos y entregas de
  cliente que no deben convertirse en obras;
- una misma fuente compartida por distintas obras.

Por eso el modelo mínimo es un grafo multipartito, no una tabla
`post -> proyecto`:

```text
P publicaciones  ↔  D entregables  ↔  A authoring  ↔  S fuentes
                         │                  │
                         └──── W obras/series candidatas ────┘
```

### La ausencia también es un estado informativo

- **Post sin proyecto base:** `published_without_source`. Significa que MAK
  puede documentar una manifestación pública, pero no debe fabricar un
  proyecto local.
- **Proyecto/archivo sin post:** `unanchored`. Puede ser privado, inédito,
  descartado, trabajo para cliente, proceso, librería, caché, otra plataforma
  o un registro público aún no exportado.
- **Tres posts y demasiados archivos:** los posts son anclas de alto valor, no
  el universo completo. El resto se procesa por embudo y conserva una lista de
  candidatos no anclados.

Ningún caso debe desaparecer por no tener pareja. La ausencia debe alimentar
  una cola de investigación, no una decisión binaria.

### El nombre del archivo es una señal, no una identidad

Un nombre solo gana fuerza cuando una autoridad externa o un consumidor puede
refutarlo o confirmarlo: discografía, publicación, metadata nativa, referencias
de composición, secuencia de frames, manifest, licencia, conversación o
registro de entrega. La regla operativa es:

> una señal es tan fuerte como la autoridad que puede refutarla.

No volver a llamar “obra”, “proyecto”, “render final” o “caché” a un contenedor
solo por su nombre, extensión, carpeta o parecido visual.

## 3. El embudo para un archivo real

El flujo para un colega que entrega un SSD desordenado y un export de Instagram
debe ser mecánico al inicio y abierto a revisión solo donde la evidencia no
alcanza.

### Etapa 0: inventario completo y reversible

Registrar rutas, bytes, hash, extensión real, firma, timestamps disponibles,
duplicados byte a byte, sidecars, secuencias, tamaños y errores de lectura. No
copiar, renombrar ni mover. El inventario completo es necesario aunque el
export social tenga solo tres publicaciones.

### Etapa 1: separación barata por función probable

Particionar sin decidir identidad artística:

- publicaciones/exportables;
- documentos nativos editables;
- imágenes, videos, audio y secuencias;
- fuentes/footage/texturas/modelos;
- librerías, cachés, proxies, autosaves y temporales;
- duplicados y versiones probables.

La clasificación aquí es operacional y reversible. Sirve para reducir el
espacio de búsqueda, no para declarar qué es una obra.

### Etapa 2: anclas públicas

Leer el export de Instagram completo, incluyendo posts, reels, historias y
archivados cuando existan. La publicación aporta existencia, fecha declarada,
texto, menciones, agrupación de carrusel y media disponible. No prueba por sí
sola que el media sea una obra autónoma, ni cuál es su archivo fuente,
intención, versión o exclusividad.

Las historias permanecen por defecto como registros audiovisuales; post y reel
son candidatos de media/obra, no obras confirmadas.

### Etapa 3: triangulación hacia atrás

Para cada media público, buscar primero coincidencias fuertes y baratas:

1. hash exacto o relación de export conocida;
2. dimensiones, duración, codec, frame rate, color y nombre técnico;
3. metadata de creación/exportación y secuencias vecinas;
4. referencias declaradas por el documento nativo;
5. consumidores y outputs del documento;
6. similitud visual/semántica únicamente como evidencia exploratoria.

La ruta nativa importa. En Blender, por ejemplo, la observación útil no es solo
“usa una imagen”, sino `imagen -> nodo/material -> objeto -> escena -> render`.
En After Effects, Photoshop, DaVinci y otras aplicaciones se deben buscar sus
referencias, composiciones, timelines, capas, proxies, footage faltante y
mensajes de error. Un asset ausente o un material rosado es una observación
del grafo de consumidores, no una orden de reparación.

### Etapa 4: hipótesis de obra y serie

Agrupar entregables y procesos solo cuando convergen varias señales. Cada
hipótesis debe poder mostrar:

- qué evidencia la sostiene;
- qué evidencia falta o la contradice;
- qué otras hipótesis compiten;
- qué observación de bajo costo la separaría de las demás.

Una obra candidata puede reunir varias publicaciones y varias fuentes; también
puede existir con una sola publicación o ninguna. El sistema no debe exigir
que cada grupo tenga un “proyecto base” local.

### Etapa 5: vistas, no reorganización destructiva

Desde el grafo se generan vistas distintas: portafolio público, proceso,
archivo técnico, serie temática, entregas a clientes, investigación y
postulación. La vista no cambia la fuente. El portafolio debe elegir
manifestaciones y relaciones defendibles; el archivo técnico puede mostrar
escenas, capas y dependencias; una postulación necesita además contexto,
derechos de uso, fechas, texto y requisitos de la convocatoria.

## 4. Qué estaba haciendo cada pieza y qué no hacía

### `instagram_source.py`

Ya resuelve una parte importante: lee el export, preserva la unidad de
publicación/carrusel, encuentra posts, reels, historias y media, y mantiene
las historias como `story_record`. Produce candidatos revisables; no enlaza
todavía el catálogo social con el SSD ni reconstruye el linaje de producción.

### `project_reconstruction.py`

Ya clasifica unidades del SSD con roles como `project_unit`, `subproject`,
`library_dependency`, `shared_resource`, `exported_product` y `undecided`.
Funciona como reconstrucción local, pero no sabe que un output corresponde a
una publicación pública ni que un post puede no tener fuente local.

### El Copilot/editor

El Copilot existente aprende una superficie de revisión: ranking, facetas,
feedback aceptar/rechazar/corregir, incertidumbre, cobertura y diversidad.
Sus vectores de 32 dimensiones son una representación hashable y reproducible,
no un modelo semántico profundo. Esto es útil para decidir qué candidato
mostrar al humano, pero no para generar el conjunto de candidatos ni para
reconstruir el linaje del SSD.

La distinción que no se debe perder es:

```text
Copilot actual:  archivo de candidatos -> orden de revisión
MAK necesario:   evidencia social + SSD + apps nativas -> grafo de candidatos
                 -> obra/serie/proceso -> vista de portafolio/postulación
```

### El experimento de operating world

El prototipo aislado mostró evidencia arquitectónica: en seis casos, el
planificador tipado alcanzó `6/6`, el router directo `3/6` y el learner `2/6`;
el planificador pudo expresar composiciones de cinco y cuatro pasos y detectar
`license_approved` como precondición inalcanzable. Esto no es prueba estadística
ni autoriza a desplegar el planificador: sus contratos de capacidad todavía
fueron declarados en el benchmark, no aprendidos de trazas reales.

La conclusión válida es más acotada: una etiqueta única no expresa bien
composición, dependencias, imposibilidad ni capacidad faltante. El próximo
experimento debe aprender o validar esas relaciones sobre casos reales nuevos,
no crear otra infraestructura de políticas por anticipación.

## 5. Lo que falló y la lección durable

1. **Confundir el producto con el archivo de producción.** Se intentó buscar la
   respuesta en el producto cuando el dato decisivo puede estar en la escena,
   capa, timeline, material, dependencia o error del documento nativo.
2. **Confundir una carpeta con un proyecto.** Un contenedor puede mezclar obras,
   librerías, cachés y entregas; el límite de proyecto es una hipótesis.
3. **Confundir una publicación con una obra confirmada.** Instagram es evidencia
   de manifestación pública y contexto, no una verdad completa sobre la unidad
   de obra, la versión, la fuente o el linaje de producción.
4. **Confundir ranking con aprendizaje del archivo.** El Copilot mejoró la
   selección de preguntas/candidatos, no la reconstrucción del caos.
5. **Intentar resolver incertidumbre con una etiqueta o una política.** La
   abstención, la contradicción y la falta de capacidad deben ser salidas
   explícitas.
6. **Leer historia antes que evidencia actual.** Los handoffs y commits sirven
   como procedencia, pero no sustituyen una medición física o una ejecución
   reproducible. A partir de este punto, primero se usa este documento, el
   handoff actual y una slice acotada; no se reabre el corpus histórico entero.

## 6. Arquitectura que queda autorizada para el siguiente slice

El siguiente paso no es migrar producción ni crear `active_policy`. Es construir
una superficie aislada, read-only y evaluable llamada provisionalmente
`publication_archive_bridge`.

Su contrato mínimo debe representar nodos y aristas con procedencia:

```text
Publication
Asset / Deliverable
AuthoringDocument
Component (scene, comp, layer, timeline, node, material)
SourceAsset
WorkHypothesis / SeriesHypothesis
EvidenceObservation
```

Cada arista necesita, como mínimo, `relation_type`, `status`, `confidence`,
`evidence_refs`, `observed_at`, `extractor_version` y una razón explícita de
abstención cuando no se puede resolver. La bridge debe reutilizar los
catálogos, Project IR, procedencia y sustrato existentes; no crear una segunda
base de autoridad.

El primer benchmark debe contener deliberadamente:

1. una publicación con export local y documento nativo que la consume;
2. una publicación sin fuente local;
3. un proyecto local con entregable sin publicación;
4. tres publicaciones y muchos archivos, con cachés, duplicados, librerías,
   dos versiones y una sola cadena de consumidores;
5. un carrusel cuyas slides pertenecen a roles distintos;
6. un mismo asset usado por dos obras;
7. una falsa coincidencia visual con nombres parecidos;
8. un caso donde falta una capacidad o permiso y el sistema debe declararlo,
   no adivinar una herramienta.

Debe compararse contra el enfoque actual con exactamente los mismos casos.
Métricas mínimas:

- cobertura de publicaciones ancladas sin falsos enlaces;
- cobertura de entregables no publicados sin convertirlos en ruido;
- tasa de joins incorrectos y duplicados;
- recuperación del camino nativo consumidor/producción;
- calidad de abstención ante contradicción o ausencia;
- composición de una vista de portafolio y explicación de sus huecos;
- detección de capacidad, permiso o evidencia faltante.

No se debe usar incertidumbre para elegir automáticamente “lo más seguro”. El
benchmark tiene casos cuyo resultado correcto es una unión, una separación,
una composición de pasos o una imposibilidad explícita.

## 7. Criterio de avance

MAK podrá salir de esta fase solo si el experimento demuestra, sobre casos
independientes y trazables, que la bridge:

- recupera relaciones que el clasificador de una etiqueta no puede expresar;
- no aumenta los falsos enlaces al incorporar más archivos no anclados;
- conserva los casos sin pareja como estados útiles;
- produce una vista curatorial explicable y no solo una taxonomía técnica;
- permite convertir evidencia y huecos en preguntas de research o requisitos
  de postulación;
- y puede ser validada por un consumidor independiente.

Si falla, se conserva el inventario y las observaciones, se retira la hipótesis
de bridge que haya fallado y se identifica qué relación no es observable. No se
retrocede a ordenar carpetas manualmente ni se maquilla el resultado con una
label adicional.

## 8. Estrategia de aprendizaje: reutilizar representaciones

La restricción de cómputo no es un problema secundario: obliga a medir primero
qué conocimiento ya existe en modelos preentrenados y qué diferencia aportan
los datos propios de MAK. El orden de aprendizaje queda fijado así:

```text
datos normalizados
    -> representaciones preentrenadas congeladas + features técnicos
    -> baseline simple
    -> evaluación por proyecto sin leakage
    -> pares/relaciones revisados
    -> aprendizaje de métrica o pequeña cabeza propia
    -> adapter/LoRA solo si la evidencia lo justifica
    -> distillation solo si hace falta desplegar un modelo más pequeño
```

### Qué significa cada técnica aquí

- **Transfer learning / feature extraction:** reutilizar un encoder visual,
  textual o audiovisual ya entrenado como sensor congelado. No significa que el
  encoder conozca la historia de MAK ni que sus similitudes sean evidencia.
- **Embeddings:** vectores comparables para buscar cercanía, duplicados,
  versiones y candidatos. Deben existir representaciones separadas para media,
  texto, metadata técnica, consumer graph y procedencia; no se debe comprimir
  todo en un vector sin conservar sus fuentes.
- **Representation learning:** el objetivo central es que “misma obra”,
  “derivado de”, “asset compartido” y “no relacionado” puedan separarse en un
  espacio útil. La etiqueta final de portafolio es una consecuencia posible,
  no la unidad primaria.
- **Similarity/metric learning:** con pares o tripletes revisados puede
  aprenderse una distancia específica de MAK. Un `same_work` positivo y un
  `not_same_work` negativo son más expresivos para este dominio que un catálogo
  cerrado de clases.
- **Clustering:** sirve para descubrir familias, secuencias y outliers. Un
  cluster es una hipótesis de exploración, nunca una declaración de obra,
  autoría o serie. Debe evaluarse por estabilidad y por evidencia, no solo por
  una métrica geométrica.
- **Supervised / self-supervised:** las decisiones humanas aportan etiquetas
  escasas y caras; el archivo aporta señales auto-supervisadas como variantes
  de export, secuencias, carruseles, archivos consumidos por la misma escena y
  duplicados controlados. La señal auto-supervisada no reemplaza el juicio
  curatorial: enseña estructura, no intención.
- **Fine-tuning, adapters y LoRA:** son etapas posteriores. Congelar el modelo
  y entrenar una cabeza pequeña debe fallar antes de justificar adaptar capas.
  LoRA/adapters reducen parámetros entrenables, pero no corrigen una unidad de
  datos mal definida ni convierten una conjetura en evidencia.
- **Knowledge distillation:** un teacher puede producir rankings, pares o
  descripciones estructuradas que un student pequeño aprenda a aproximar. El
  student no debe heredar como verdad una inferencia del teacher: cada salida
  debe conservar la observación original y su estado epistemológico.

La literatura de representation learning motiva buscar espacios que separen
factores de variación; SimCLR muestra el valor de aprender invariancias con
señales de augmentación; SBERT demuestra el uso de embeddings comparables para
texto; FaceNet formaliza una distancia aprendida para verificación y clustering;
los adapters y LoRA muestran adaptación eficiente con pesos base congelados; y
distillation permite comprimir el comportamiento de modelos grandes en uno
menor. Son fundamentos metodológicos, no evidencia de que alguna técnica ya
funcione para MAK.

### Representación propia de MAK

La primera representación propia no debe ser un único embedding neuronal. Debe
ser una composición auditable de:

1. embedding visual/audio/textual del entregable o registro;
2. features técnicos de formato, dimensiones, duración, codec, secuencia,
   versión y hash;
3. features de documento nativo: escenas, comps, capas, timelines, nodos,
   materiales y referencias;
4. features temporales y de procedencia: publicación, export, observación,
   fuente y consumidor;
5. relaciones de grafo y estados de evidencia.

La fusión debe ser tardía o por canales separados para poder explicar si una
relación fue sugerida por contenido visual, texto, metadata o por un consumidor
nativo. El actual `portfolio_vector` de 32 dimensiones se conserva como baseline
hashable y reproducible; no se debe describir como embedding semántico aprendido.

### Benchmark mínimo antes de adaptar un modelo

Sobre el mismo conjunto de casos, sin cambiar producción, comparar:

1. hash/features actuales;
2. similitud coseno y k-NN sobre embeddings congelados;
3. regresión logística o clasificador lineal;
4. árbol/ensemble pequeño y MLP pequeño, solo como comparación;
5. clasificador de pares para `same_work`, `derived_from`, `shared_asset` y
   `not_same_work`;
6. clustering exploratorio con estabilidad y revisión de outliers.

El split debe ser por proyecto/obra/serie, no por archivo aleatorio. Un post,
su export local y su documento fuente pertenecen al mismo grupo y no pueden
repartirse entre train y test. Toda normalización, reducción dimensional,
selección de features, clustering o ajuste de umbral se aprende solo con train.
El test se mantiene intacto hasta la evaluación final; de lo contrario el
resultado es leakage y no evidencia de generalización.

El gate de avance es falsable: si los embeddings congelados no superan o no
aportan cobertura explicable frente al baseline hashable en proyectos de
holdout, no se justifica LoRA, fine-tuning ni destillation. El siguiente intento
debe mejorar la evidencia o la representación técnica. Si sí superan el
baseline, se puede probar metric learning con pares revisados, manteniendo una
comparación contra el encoder congelado.

## Instrucción de continuidad

Antes de implementar el próximo slice, leer este documento y
`context/LAST_HANDOFF.md`. No reconstruir el pasado completo. No cambiar
`WIN`. No mover, renombrar ni borrar archivos artísticos. No promover políticas
ni entrenar pesos. El objetivo inmediato es obtener evidencia nueva sobre el
puente entre manifestación pública, producción nativa y obra candidata.
