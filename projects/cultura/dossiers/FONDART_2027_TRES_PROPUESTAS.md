---
document_id: fondart-2027-three-proposals-v1
status: working_draft
owner: artist
lane: obra-investigacion
opportunity: fondart-nacional-investigacion-2027
source_of_truth: local_evidence_plus_official_bases
---

# Tres propuestas Fondart 2027

Este documento convierte tres lineas reales de MAK en expedientes de trabajo.
No declara elegibilidad ni reemplaza el FUP o las bases oficiales. La funcion
es separar tesis, metodo, evidencia, resultado y vacios para que la decision de
postular sea concreta.

## 1. Regla de convocatoria que cambia la estrategia

La linea **Investigacion - Fondart Nacional 2027** esta abierta hasta el 10
de septiembre de 2026 a las 15:00. Su Grupo A incluye artes visuales y
plasticas, fotografia, nuevos medios e interdisciplina. Exige un plan de
transferencia de conocimientos y las bases indican que solo se puede presentar
una postulacion en esta linea por responsable.

La convocatoria permite entre $500.000 y $15.000.000 por proyecto en el Grupo
A, con ejecucion iniciada entre el 1 de marzo y el 30 de abril de 2027 y un
plazo maximo de 12 meses. La transferencia puede solicitar entre 5% y 10% de
los recursos, y la asignacion del responsable tiene un tope de 40%. Estos datos
son de las bases 2027 leidas el 18 de agosto de 2026 y deben volver a
comprobarse al preparar el FUP.

**Decision:** no conviene presentar las tres como si fueran una trilogia
indiferenciada ni enviar las tres a Investigacion. Se desarrollan las tres,
pero se elige una para esta linea. Las otras quedan listas para otra
convocatoria o para una segunda fase del portafolio.

## 2. Criterio comun de lectura

Cada expediente usa la semantica de DIMENSIONES sin copiar sus proyectos:

`pregunta -> fuentes -> claims -> metodo -> experimento -> obra/prototipo ->
transferencia -> evidencia -> riesgo -> decision -> siguiente accion`

Los roles de MAK son distintos y no se deben mezclar:

- `mak_research`: captura, normalizacion, relacion y contexto.
- `mak_curatoria`: selecciona el corpus, detecta vacios y prepara la lectura.
- `mak_vigia`: mantiene separadas las oportunidades actuales de los
  antecedentes historicos.
- `mak_plataforma`: guarda el contrato de lote, proveedor, resultado y
  revision; una respuesta de modelo nunca es una fuente.
- `tools/research_job_router.py`: expresa los doce procesos del trabajo sin
  necesidad de llamar a un proveedor.
- `tools/interpretive_garden_workflow.py`: ejecuta la semantica especifica de
  Jardines interpretativos.

## 3. Propuesta A - Grados de desacuerdo

### Tesis

Investigar como un archivo personal de obras, ideas, pruebas y descartes puede
convertirse en un organismo publico navegable sin reducirlo a un curriculum,
una taxonomia rigida ni una interfaz de diagnostico.

### Pregunta de investigacion

¿Que formas de lectura aparecen cuando un portafolio artistico se organiza como
relaciones, tensiones y recorridos, en vez de como una lista lineal de obras?

### Metodo

1. Delimitar un corpus publico y un corpus privado que no se publicara.
2. Registrar cada pieza con fuente, estado, relacion, decision editorial y
   permiso de publicacion.
3. Comparar tres modos de navegacion: cronologico, por familias y por
   relaciones/contradicciones.
4. Producir un prototipo de lectura y probarlo con personas externas al
   desarrollo.
5. Registrar que recorridos se comprenden, donde se pierde el contexto y que
   lenguaje produce falsas interpretaciones.
6. Transferir el metodo mediante una sesion publica y un protocolo breve de
   archivo artistico.

### Resultado tangible

- Un prototipo publico del portafolio-organismo.
- Un dossier de investigacion con matriz de fuentes, relaciones y decisiones.
- Un instrumento editable que permita mantener el archivo sin convertir MAK en
  una caja negra.
- Un informe de prueba de lectura y accesibilidad.
- Una actividad de transferencia presencial o virtual.

### Evidencia local existente

- `/home/mak/flujo/projects/cultura/dossiers/grados_de_desacuerdo.md`
- `/home/mak/flujo/projects/cultura/PORTAFOLIO_ORGANISMO.md`
- `/home/mak/flujo/projects/cultura/doublecup/`
- `/home/mak/flujo/cultura/mak_curatoria/diagnostico_proyectos.py`
- `/home/mak/flujo/cultura/mak_curatoria/triangular.py`
- `/home/mak/flujo/cultura/mak_plataforma/hub.py`
- `/home/mak/flujo/tools/research_job_router.py`

### Consumidor y publico

El consumidor primario es el propio archivo del artista y su portafolio. El
publico secundario son artistas, curadores, investigadores y personas que
necesitan leer un proceso creativo sin recibir una vitrina publicitaria
cerrada.

### Vacios criticos

- Definir el corpus exacto y sus permisos de publicacion.
- Ejecutar pruebas con lectores reales y dejar evidencia de las correcciones.
- Escribir una tesis breve que no dependa del vocabulario interno de MAK.
- Nombrar, si corresponde, una colaboracion de mediacion o accesibilidad.
- Separar el prototipo de doublecup de cualquier promesa medica o psicologica.
- Convertir la arquitectura en cronograma, presupuesto y entregables del FUP.

### Encaje y riesgo

Tiene encaje preliminar en Grupo A por nuevos medios/interdisciplina, pero su
riesgo es parecer un sitio web personal o una reorganizacion administrativa.
La postulacion debe demostrar una pregunta artistica, un metodo de
investigacion, un prototipo y transferencia de conocimiento.

## 4. Propuesta B - Jardines interpretativos

### Tesis

Investigar una forma de transformar fuentes botanicas, culturales y tecnicas
heterogeneas en interpretaciones visuales trazables, conservando la diferencia
entre dato, inferencia, analogia y decision artistica.

### Pregunta de investigacion

¿Como puede un sistema de relaciones entre fuentes producir un jardin visual
interpretativo sin borrar la procedencia de los conocimientos ni confundir una
metafora artistica con una instruccion tecnica?

### Metodo

1. Seleccionar un caso acotado y una familia de fuentes verificables.
2. Capturar cada fuente y guardar su procedencia en SQLite.
3. Extraer claims, entidades, relaciones, contexto y nivel de certeza.
4. Construir una interpretacion visual y registrar sus decisiones.
5. Comparar el resultado con las fuentes y con una lectura humana externa.
6. Publicar un prototipo del jardin, un protocolo reproducible y una actividad
   de transferencia.

La cadena operativa es:

`discover -> capture -> extract -> normalize -> relate -> contextualize ->
interpret -> simulate -> validate -> curate -> publish -> audit`

### Resultado tangible

- Un corpus acotado con trazabilidad de fuentes y claims.
- Un jardin visual interactivo o una pieza generativa documentada.
- Un mapa de relaciones entre conocimiento, imagen, contexto e interpretacion.
- Un protocolo MAK para investigaciones culturales con correlacion y base de
  datos.
- Una instancia de transferencia para artistas, curadores o investigadores.

### Evidencia local existente

- `/home/mak/research/jardines_interpretativos/JARDINES_INTERPRETATIVOS_RESEARCH.md`
- `/home/mak/flujo/tools/interpretive_garden_workflow.py`
- `/home/mak/flujo/tools/research_job_router.py`
- `/home/mak/flujo/cultura/mak_research/`
- `/home/mak/research/corpus/fondart_annual_2015_2025_20260813_v5/sources.sqlite`
- `/home/mak/flujo/cultura/mak_vigia/fuentes.json`

### Consumidor y publico

El consumidor es el departamento Research de MAK, que puede reutilizar el
protocolo para curatoria, proyectos de arte y postulaciones. El publico puede
ser una comunidad de artistas visuales, investigadores o mediadores culturales;
la comunidad concreta debe definirse antes del FUP.

### Vacios criticos

- Elegir un solo caso y no prometer una enciclopedia de plantas.
- Definir fuentes primarias y una persona asesora de la disciplina si resulta
  necesaria.
- Ejecutar un piloto con entradas, relaciones y salida visual verificables.
- Declarar que la pieza no entrega diagnosticos, tratamientos ni instrucciones
  operativas de cultivo.
- Definir territorio, publico de transferencia y mecanismo de evaluacion.
- Convertir el documento de research en un expediente con calendario,
  presupuesto y resultados observables.

### Encaje y riesgo

Es el encaje mas directo con la linea Investigacion porque ya tiene pregunta,
metodo, semantica de procesos y una base de procedencia. Su riesgo principal
es la amplitud: si intenta abarcar botanica, alimentos, sustancias, memoria y
visualizacion a la vez, pierde viabilidad. El proyecto debe comenzar con un
caso demostrable y dejar los adaptadores como continuidad.

## 5. Propuesta C - Tapiz / VibeCode

### Tesis

Investigar como el codigo, el texto, la perdida semantica y los patrones
visuales pueden convertirse en una gramatica de tapiz contemporaneo, donde la
ejecucion informatica es material de la obra y no solo una herramienta de
produccion.

### Pregunta de investigacion

¿Como se transforma un conjunto de instrucciones, palabras, vacios y
variaciones en una pieza visual que conserve la tension entre regla,
interpretacion y accidente?

### Metodo

1. Elegir una tesis unica para el tapiz y un conjunto limitado de motivos.
2. Verificar las fuentes historicas o culturales antes de presentarlas como
   linaje.
3. Ejecutar variaciones reproducibles con VibeCode y conservar sus parametros.
4. Comparar salidas digitales, SVG y una posible derivacion material.
5. Seleccionar una pieza o serie final con criterios curatoriales explicitos.
6. Transferir el procedimiento mediante una demostracion o taller de lectura
   de codigo e imagen.

### Resultado tangible

- Una pieza o serie curada, no solo un conjunto de pruebas.
- Un generador reproducible con entradas y salidas documentadas.
- Un dossier visual y de procedencia de los motivos.
- Salidas SVG/HTML editables para exhibicion o portafolio.
- Una actividad de transferencia que explique el metodo a otros artistas.

### Evidencia local existente

- `/home/mak/flujo/projects/cultura/dossiers/tapiz.md`
- `/home/mak/flujo/projects/tapiz/README.md`
- `/home/mak/flujo/projects/tapiz/DIRECTION.md`
- `/home/mak/flujo/projects/tapiz/vibecode/loom.py`
- `/home/mak/flujo/projects/tapiz/vibecode/spaces.py`
- `/home/mak/flujo/projects/tapiz/piezas_curadas/`
- `/home/mak/flujo/projects/tilde/`
- `/home/mak/flujo/projects/cultura/borradura_ascii/`

### Consumidor y publico

El consumidor es el departamento Cultura/Portfolio y la cadena de produccion
VibeCode. El publico son artistas visuales, VJ, diseñadores y personas
interesadas en la relacion entre codigo y artesania visual.

### Vacios criticos

- Decidir si el resultado sera una pieza unica, una serie o una instalacion.
- Reemplazar el estado "fuentes sin verificar" por referencias comprobadas.
- Reducir la cantidad de herramientas expuestas en la tesis final.
- Definir la experiencia de publico y un modo de transferencia evaluable.
- Preparar un presupuesto de produccion, documentacion y exhibicion.

### Encaje y riesgo

Puede encajar en Grupo A por nuevos medios/interdisciplina si la investigacion
es el centro. Su riesgo es que el jurado vea un generador tecnico o una
coleccion de estilos. La propuesta debe presentar una pregunta, una decision
curatorial y una obra final; `tilde` y `borradura_ascii` son antecedentes
metodologicos, no tres proyectos adicionales.

## 6. Antecedentes historicos encontrados en MAK

El corpus local de Fondart fue abierto en modo lectura desde
`/home/mak/research/corpus/fondart_annual_2015_2025_20260813_v5/sources.sqlite`.
No se copio ningun proyecto ni se uso un antecedente como prueba de elegibilidad.
Los siguientes patrones sirven para calibrar lenguaje y escala:

- Archivos/nuevos medios: 176 coincidencias por titulo; mediana historica de
  $10.940.339; 17 coincidencias de 2024-2025.
- Territorio/naturaleza: 218 coincidencias; mediana historica de $10.000.000;
  37 coincidencias de 2024-2025.
- Textil/visual: 273 coincidencias; mediana historica de $9.948.123; 55
  coincidencias de 2024-2025.

Ejemplos de antecedentes seleccionados, siempre con su fuente original:

- `Encuentro 2025: Archivos de arte y Practicas colaborativas` (Biobio, 2025).
- `4° Version - EUREKA, Festival Internacional de los Nuevos Medios 2025`
  (Biobio, 2025).
- `1° Laboratorio Nacional de Archivos de Arte` (Metropolitana, 2024).
- `Desierto Despierto: Primer Encuentro de las Artes de la Visualidad y la
  Naturaleza` (Atacama, 2025).
- `Territorio y medioambiente. Propuestas de mediacion artistica interactiva`
  (Biobio, 2024).
- `XII version del Festival de la Lana. Montecarmelo` (Metropolitana, 2025).
- `Exposicion Witral Urdimbre Incandescente` (O'Higgins, 2025).
- `Hub Creativo: Conferencia, Laboratorio, Mercado y Festival de Nuevos Medios
  y Artes Visuales` (Valparaiso, 2024).

Estos ejemplos muestran precedentes de archivo, nuevos medios, territorio,
mediacion y textil, pero no prueban que una propuesta de MAK sea admisible.

## 7. Seleccion recomendada

### Para la convocatoria Investigacion 2027

1. **Jardines interpretativos**: mejor cumplimiento inmediato de pregunta,
   metodo, trazabilidad y transferencia.
2. **Grados de desacuerdo**: mejor ancla de portafolio y mayor potencia
   autoral, pero necesita prueba de lectura y un corpus publico definido.
3. **Tapiz/VibeCode**: mejor evidencia de implementacion visual, pero necesita
   cerrar tesis, fuentes y pieza final.

Esta prioridad es especifica para la linea Investigacion. No significa que
Jardines sea la obra principal del portafolio ni que Grados pierda prioridad
artistica.

### Rutas alternativas que no se deben forzar

- **Barrios Creativos 2027**: solo para una version colectiva, territorial y
  con comunidad nombrada. No aplica hoy a ninguna de las tres sin cambiar su
  contrato.
- **Organizacion de Muestras, Ferias y Encuentros 2027**: sirve para una
  exhibicion o encuentro posterior. La modalidad nacional exige al menos dos
  versiones anteriores; no es el encaje actual de las tres obras.
- **Becas Chile Crea 2027**: puede apoyar formacion individual en mediacion,
  diseño digital o IA, pero no reemplaza la postulacion de una de estas obras.

## 8. Paquete de postulacion pendiente

Para la propuesta que se elija se debe producir, en este orden:

1. Resumen de una pagina en lenguaje de jurado.
2. Pregunta, objetivos general/especificos y metodologia.
3. Cronograma de hasta 12 meses, comenzando entre marzo y abril de 2027.
4. Presupuesto con cotizaciones y funciones reales; sin montos inventados.
5. Plan de transferencia con al menos una actividad presencial o virtual.
6. Antecedentes, CV y colaboradores confirmados.
7. Evidencias publicables con links vigentes y sin claves.
8. Matriz final de riesgos, permisos, accesibilidad y propiedad intelectual.
9. Relectura contra el Anexo 2 y envio de una sola postulacion dentro de plazo.

## Fuentes oficiales consultadas

- [Investigacion - Fondart Nacional 2027](https://www.fondosdecultura.cl/fondos/fondart-nacional/lineas-de-concurso/investigacion-fondart-nacional-2027/)
- [Bases de Investigacion Fondart Nacional 2027](https://www.fondosdecultura.cl/wp-content/uploads/2026/08/investigacion-fondart-nacional-2027.pdf)
- [Barrios Creativos Fondart Nacional 2027](https://www.fondosdecultura.cl/fondos/fondart-nacional/lineas-de-concurso/barrios-creativos-fondart-nacional-2027/)
- [Organizacion de Muestras, Ferias y Encuentros 2027](https://www.fondosdecultura.cl/fondos/fondart-nacional/lineas-de-concurso/organizacion-de-muestras-ferias-y-encuentros-fondart-nacional-2027/)
- [Calendario de Fondos Cultura](https://concurso.fondosdecultura.cl/)

## Estado

`working_draft`: las tres propuestas estan desarrolladas hasta matriz de
postulacion y priorizacion. Ninguna se marca como enviada, elegible o
financiada. El siguiente trabajo ejecutable es convertir **Jardines
interpretativos** en el primer FUP de prueba, manteniendo Grados y Tapiz como
expedientes separados.
