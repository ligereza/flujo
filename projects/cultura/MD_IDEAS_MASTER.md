# Mapa maestro de ideas culturales

Este documento consolida la capa de ideas sin reemplazar los dossiers ni las
sesiones originales. La fuente de direccion es
`RAINSTORM_2026-07-10.md` y el metodo es:

```text
dossier -> instrumento -> material -> pieza
```

## Tilde / idioma / borradura

Pregunta: que significado sobrevive cuando el texto se comprime o cruza un
canal con perdida.

Instrumentos y piezas:

- `desktop/tilde_meter.py`
- `projects/tilde/sobrevivencia.py`
- `projects/cultura/tilde_residuo.py`
- `projects/cultura/borradura_ascii/borradura.py`
- `projects/cultura/borradura_ascii/tapiz.py`
- `tools/idioma.py`
- `tools/validar_curaduria.py`

Estado actual: la idea vive en el contrato tecnico. El codigo nuevo usa
English ASCII; el producto humano usa espanol UTF-8 correcto. No es una
prohibicion de espanol: es una frontera entre maquina y persona.

## Tapiz / Cauce / vacio

Pregunta: que pasa cuando el codigo y sus espacios dejan de ser solo soporte y
se vuelven patron visual.

Instrumentos y piezas:

- `projects/tapiz/vibecode/`
- `projects/tapiz/vibecode/cauce.py`
- `tools/sala3d/`
- `projects/tapiz/piezas_curadas/cauce_cauce.svg`
- `projects/tapiz/piezas_curadas/cauce_sala3d.svg`
- `projects/tapiz/VOLA.md`

Estado actual: Tapiz es la biblioteca visual; Cauce es un modo de Tapiz.
VOLA y las piezas SVG son material curado, no nuevas herramientas base.

## Psicosis / registro / incertidumbre

Pregunta: como estudiar una conducta sin confundir registro con verdad.

Instrumentos y material:

- `projects/cultura/psicosis_agente/`
- `projects/cultura/fila_cero.py`
- `projects/cultura/mecanismo_residuo.py`
- `projects/cultura/cartografia_filtros/`

Estado actual: prototipos culturales y reglas de procedencia. Nunca es una
herramienta de vigilancia ni de diagnostico sobre terceros.

## Precursor

Pregunta: como la cultura del diseno, los nombres y los artefactos legales
construyen significado alrededor de sustancias.

Fuentes:

- `knowledge/dossiers/precursor.yaml`
- `projects/cultura/dossiers/precursor.md`

Estado actual: dossier-first. No hay que inventar un instrumento operativo
solo para llenar el hueco.

## Cruces actuales

```text
Tilde -> lenguaje y preservacion del significado
Tapiz/Cauce -> materializacion visual de texto, codigo y vacio
Psicosis -> procedencia, incertidumbre y lecturas que no se deben colapsar
Curatoria -> carpetas, indices, dossiers y propuestas
Venue/VJ -> espacio, geometria, pantallas y escenografia
RD -> plano, rider, evento y propuesta operativa
Portfolio -> proyeccion publica aprobada
```

## Curatoria / archivo / postulaciones

Pregunta: como convertir una carpeta caotica, una convocatoria y una
investigacion en una propuesta verificable sin confundir borrador con hecho.

Fuentes y superficies:

- `docs/recovered/claude_sessions_2026-08-12/raw/MEMORIA_DIRECCION.md`
- `projects/cultura/dossiers/convocatorias_mak_ruta.md`
- `docs/becas/CALENDARIO_POSTULACIONES.md`
- `docs/becas/postulacion_base.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/fondos-fondart-terminos-condiciones-requisitos-2027.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/postulacionfondartborrador.md`

Estado: la memoria de direccion contiene la hipotesis de servicio; la ruta de
convocatorias y los documentos de becas son instrumentos de trabajo; los
extractos recuperados son evidencia de investigacion. El pipeline puede
indexar, relacionar y preparar borradores, pero no debe afirmar elegibilidad,
fechas o requisitos sin volver a la fuente primaria. No hay auto-postulacion ni
promocion automatica en este corte.

## RD / VJ / venue / propuesta visual

Pregunta: como unir la realidad tecnica del venue, el layout de pantallas y la
entrega RD sin fusionar bases que tienen privacidad o propietarios distintos.

Fuentes y superficies:

- `projects/plano/README.md`
- `docs/HERRAMIENTAS_VISUALES.md`
- `linea_editorial/v4.1.md`
- `docs/rd/DB_PRODUCTORAS_ESTADO.md`
- `projects/plano/referencia_plano_teatro.py`
- `tools/venue_geometria_scd.py`

Estado: esta es una linea activa con consumidores reales. El plano/rider,
venue tecnico, catalogo RD, skin publico y portfolio comparten IDs y
procedencia, pero conservan contratos separados. La geometria SCD es
prototipo/demostrador hasta que sus medidas de entrada sean aportadas y
verificadas.

## Editorial y memoria de producto

`linea_editorial/v4.1.md` es contrato humano de RD y debe convivir con la base
de configuracion operativa. `MAPA.md`, `CAPACIDADES.md` y `PLAN.md` son mapas
de arquitectura/capacidad/backlog: sirven para orientar la lectura, pero cada
afirmacion que afecte integracion debe cruzarse con el consumidor y la
verificacion actual. Esto evita que una version editorial o una idea historica
se convierta accidentalmente en dependencia de runtime.

## Bioma / Puente

Pregunta: que ocurre cuando Precursor, Psicosis y Tilde funcionan como un
modelo cultural de informacion, traduccion, ruido y autocorreccion.

Fuentes:

- `puente/MANIFIESTO_DEL_BIOMA.md`
- `puente/v1/FASE_1_el_axioma_absoluto.md`
- `puente/v1/FASE_2_bucle_de_dilatacion_temporal.md`
- `puente/v1/FASE_3_despliegue_trinidad.md`
- `puente/v1/FASE_5_haz_temporal_presente_dividido.md`
- `puente/v1/FASE_6_traduccion_y_boolean_cultural.md`
- `puente/v2/03_DIAGNOSTICO_DIFERENCIAL.md`

Estado: teoria y manifiesto, sin consumidor runtime ni blueprint operativo.
Conserva la genealogia de Tilde/Psicosis/Precursor y sirve para lectura
artistica, no para diagnosticar personas ni para inventar una herramienta por
obligacion de completitud.

## Investigacion de archivos / Firecrawl / privacidad

Pregunta: como medir la entropia documental de una organizacion y devolver un
mapa util sin apropiarse de documentos, personas o ideas.

Fuentes:

- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/quantified-self-firecrawl.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/00-indice.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/03-revisiones-ong.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/05-auditoria-firecrawl.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/06-sintesis-populares.md`
- `docs/recovered/claude_sessions_2026-08-12/raw/solid_hpi_quantified_self/07-sintesis-trending.md`

Estado: investigacion/prototipo de metodo para Curatoria. La unidad de medida
es el sistema documental, no el rendimiento individual. Firecrawl y otros
proveedores son bordes externos: no se ejecutan ni se convierten en
dependencia por la mera existencia de estos informes. Requiere autorizacion,
anonimizacion, limites de retencion y devolucion del mapa a la organizacion.

## Research RD / reduccion de danos

Pregunta: como traducir investigacion sobre reactivos, datos, ley, apps y
financiamiento en materiales responsables para RD sin presentarla como consejo
legal, diagnostico o evidencia de campo.

Fuentes principales:

- `docs/rd/informes/reactivos_estado_arte.md`
- `docs/rd/informes/bases_datos_harm_reduction.md`
- `docs/rd/informes/ley_20000_marco_legal.md`
- `docs/rd/informes/app_publica_factibilidad.md`
- `docs/rd/informes/app_directiva_metricas.md`
- `docs/becas/informes/20260722-171629-fundaciones-internacionales-que-financia.md`

Estado: informes generados por Research, con revision humana pendiente
declarada en sus encabezados. Funcionan como mapa de preguntas, fuentes y
riesgos para dossiers y propuestas; no autorizan una operacion clinica,
quimica, juridica, financiera o de proveedor. Las futuras salidas deben
separar fuente primaria, inferencia y propuesta.

## Tapiz / Resolume / operador VJ

`tools/TAPIZ_RESOLUME_SPEC.md` es una especificacion para que un operador
conecte `system_status.json` a Resolume mediante OSC; `docs/TAPIZ.md` conserva
la pieza visual y su genealogia. Estado: especificacion/prototipo de operador,
no servicio permanente. Antes de convertirla en integracion se debe comprobar
el contrato JSON, las direcciones OSC de la composicion real y un ensayo
acotado sin equipo externo.

## Regla de consolidacion

Una idea queda en el maestro cuando tiene nombre, pregunta, fuente, instrumento
o razon explicita para seguir como dossier-only, consumidor real y estado de
publicacion. Las sesiones recuperadas siguen siendo evidencia; no se convierten
automaticamente en producto.
