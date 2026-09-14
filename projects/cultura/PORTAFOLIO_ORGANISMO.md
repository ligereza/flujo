# Portafolio organismo

Estado: expediente de direccion, fase 1.

Este documento consolida el proyecto antes de tocar la navegacion publica, el
`readme.svg` o el hosting. No es una obra, un framework nuevo ni una segunda
fuente de verdad. Es el puente entre el contexto artistico del autor, el
archivo pesado y la experiencia publica ligera.

## Proposicion madre

El portafolio no solo muestra obras terminadas. Es un organismo que transforma
su propio archivo en tres lecturas coordinadas:

1. **Comunidad:** conserva registros, colaboraciones, eventos y aportes de
   otras personas con procedencia y consentimiento.
2. **Obra:** convierte relaciones, texto, color, tiempo y navegacion en una
   experiencia generativa.
3. **Herramienta:** permite ordenar, editar, curar y derivar nuevas salidas sin
   exigir que el visitante entienda la infraestructura.

Son tres funciones de una misma base, no tres sitios ni tres repositorios.

## Material de origen

| Material | Funcion correcta | No debe confundirse con |
|---|---|---|
| `postulacionfondartborrador.md` | Primer intento de proyecto y tesis de presentacion | Una obra terminada o una investigacion factual |
| `organismo.html` | Referencia de experiencia, navegacion y posicion del artista | Un build definitivo |
| `3d-double-cup-fluid-visualizer.zip` | Referencia de forma, proporcion y movimiento para el vaso | La aplicacion que debe vivir dentro de MAK |
| `projects/cultura/doublecup/` | Memoria tecnica del vaso semantico y sus limites | Un reemplazo automatico del original |
| `convocatorias-mak.zip` | Radar de oportunidades y fuentes para validar | Una base de oportunidades vigentes sin revalidacion |

El borrador de Fondart precede al prototipo 3D. Por eso la siguiente lectura
no es rehacer ambos por separado: es usar el prototipo como evidencia visual y
tecnica para fortalecer una segunda version del proyecto.

## Dos capas, una identidad

### Capa 1: archivo y produccion

Es la capa pesada y privada/de trabajo. Conserva los originales y sus
relaciones:

- imagenes, videos, reels e historias;
- descripciones originales y metadata de Instagram;
- obras, procesos, eventos, venues, artistas y colaboraciones;
- propuestas, convocatorias, fuentes y versiones de postulacion;
- decisiones humanas, procedencia, consentimiento y estado de revision.

Esta capa no se duplica para cada superficie. MAK la indexa y conserva los
vinculos; no convierte cada registro audiovisual en obra ni cada hipotesis en
hecho.

### Capa 2: organismo publico

Es la capa ligera y portable. Proyecta relaciones seleccionadas mediante SVG,
GLSL, ASCII, texto, color y navegacion. No carga todo el archivo de una vez.

- muestra primero vectores, metadatos y relaciones;
- carga imagen o video solo cuando el visitante lo solicita o llega a la obra;
- permite una galeria, una lectura generativa o una herramienta sin copiar los
  datos de origen;
- puede vivir en un hosting liviano aunque el archivo pesado este en otro;
- conserva URL estables para volver a una obra, evento o registro.

La capa publica es una proyeccion, no la fuente de verdad. El micelio, la
galeria y el `readme.svg` deben leer el mismo sustrato, pero no renderizarlo de
la misma manera.

## Contrato minimo de proyeccion

Cada bloque de portafolio expuesto por MAK lleva un sobre derivado, no una
copia del registro. Su esquema es `faro-portfolio-entity-v1` y sus campos
comunes son:

| Campo | Funcion |
|---|---|
| `entity_id` | identidad estable del item del inbox |
| `source_id` | publicacion o fuente de origen |
| `lane` | `obra`, sin convertir el registro en obra terminada |
| `purpose` | triage audiovisual sin llamar obra a una historia |
| `format` | `registro` para historia o el formato ya declarado |
| `evidence_kind` | `media_metadata` u otra evidencia ya declarada |
| `status` | seleccion existente: pendiente, seleccionar o deseleccionar |
| `next_action` | `review`, `triangulate` o `reject` |
| `owner` | humano cuando falta decision; MAK cuando puede ejecutar la accion |
| `consent` | estado y base declarada del permiso, sin asumir autorizacion |
| `publication` | estado de salida y gate humano antes de exponer |

El contrato se deriva en `cultura/mak_plataforma/contrato_archivo.py` y se
proyecta desde el Hub. No inventa titulos, autores, eventos ni relaciones. La
galeria y el organismo pueden ignorar los campos que no necesitan, pero no
pueden cambiar identidad, procedencia o estado.

El editor consulta primero `/api/portfolio/contract`, una superficie ligera
que devuelve solo el contrato y la politica de publicacion. La proyeccion
completa `/api/portfolio/organism` se reserva para clientes que realmente
necesitan bloques y relaciones; asi el editor no descarga el micelio entero
para verificar una regla.

## Flujo de transformacion

```text
archivo o idea
  -> candidato con procedencia
  -> MAK ordena y separa formato
  -> evidencia y relaciones
  -> decision humana cuando corresponde
  -> proyeccion: galeria / organismo / herramienta / convocatoria
```

MAK puede sugerir conexiones, mejorar un borrador o detectar vacios, pero no
decide por si solo que algo es obra, atribucion, evento confirmado o
publicacion.

## Primer proyecto de prueba

`Grados de desacuerdo` sera el primer proyecto que atraviese las dos capas.

En la capa de archivo queda como:

- tesis artistica;
- contexto personal del autor;
- metodologia propuesta;
- referencias y afirmaciones que requieren verificacion;
- cronograma, presupuesto y posibles convocatorias;
- versiones del borrador y decisiones de revision.

En la capa de organismo se traduce en una experiencia de portafolio: el
visitante no solo ve una imagen, sino que recorre una relacion entre corpus,
percepcion, medida, texto, forma y desacuerdo.

La postulacion mejorada no debe ser una reescritura cosmetica. MAK debe
comparar el borrador con el contexto real, el modelo de navegacion y el
prototipo visual; luego separar tesis, obra, metodologia, impacto comunitario,
factibilidad y presupuesto. Las afirmaciones cientificas permanecen como
pendientes de evidencia hasta ser verificadas.

## Rol del double cup

El vaso doble es la referencia formal que faltaba para la animacion del
`readme.svg`:

- fija la silueta y la proporcion del vaso;
- aporta estados de movimiento: reposo, giro, derrame y retorno;
- permite generar referencias visuales sin convertir el runtime 3D en una
  dependencia del portafolio;
- sirve como entrada para una traduccion a texto, color, ASCII y vectores.

El resultado final no tiene que simular literalmente una escena 3D. La forma
puede aparecer porque el color y las lineas de texto se desplazan de acuerdo
con ella. La animacion es la obra; el prototipo 3D es solo el laboratorio que
ayuda a encontrar su comportamiento.

## Reglas de direccion

- No crear un segundo ledger, grafo o framework para este proyecto.
- No publicar el archivo pesado por defecto.
- No tratar el HTML teorico como build definitivo.
- No tratar el ZIP 3D como dependencia de MAK.
- No transformar automaticamente historias o convocatorias en obras o hechos.
- Mantener descripcion original, interpretacion de MAK y decision del artista
  como capas separadas.
- Mantener consentimiento, registro comunitario y publicacion como capas
  distintas. Una historia puede ser visible para el editor y seguir siendo
  privada para el organismo publico.
- Mantener familia, enfermeria y otros dominios privados fuera del archivo
  publico de arte.
- Toda salida publica debe poder rastrearse hasta su fuente y su decision.

## Fases posteriores

1. **Mejora de postulacion:** hacer que MAK critique y reestructure el borrador
   Fondart con evidencia, vacios y versiones comparables.
2. **Ruta de convocatorias:** incorporar candidatos al radar existente sin
   presentarlos como vigentes hasta verificar fuente, fecha y elegibilidad.
3. **Superficie comunitaria:** separar registros publicos, consentimiento,
   eventos y colaboraciones del archivo privado de trabajo.
4. **Hosting:** escoger primero la arquitectura de archivo pesado y organismo
   ligero; el dominio se decide despues.
5. **Prueba visual:** retomar el `readme.svg` solo cuando el artista lo pida,
   usando la silueta doble y una animacion de color/texto con fallback estatico.

La fase 1 se considera cerrada cuando una persona puede entender que es el
proyecto, donde empieza, que parte es archivo, que parte es obra y que parte
es herramienta, sin leer la infraestructura interna.
