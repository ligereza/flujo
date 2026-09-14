# Grados de desacuerdo — expediente de mejora

Estado: propuesta en desarrollo; no es obra terminada ni investigacion
factual. Este expediente es una base para que MAK critique y mejore un primer
borrador de postulacion sin convertirlo en una reescritura automatica.

## Identidad de trabajo

```yaml
work_id: project:grados-de-desacuerdo:v1
lane: obra
purpose: desarrollar un instrumento de presentacion y navegacion del portafolio
format: proposal_brief
owner: artist
status: draft_for_critique
```

La propuesta trata sobre como se muestra y se experimenta un portafolio. No
debe clasificarse como un dispositivo medico, una prueba diagnostica ni una
investigacion clinica. Las referencias cientificas del borrador son insumos
que requieren verificacion antes de afirmarse publicamente.

## Linaje

1. El borrador de Fondart es el primer intento de formular el proyecto.
2. `organismo.html` aporta la experiencia de navegacion, la posicion del
   artista y la relacion entre visitante, archivo y obra.
3. El prototipo `3d-double-cup-fluid-visualizer` aporta una referencia de
   forma, proporcion, estados de movimiento y exportacion visual.
4. `projects/cultura/doublecup/` contiene la memoria tecnica del vaso
   semantico y sus limites.
5. Las convocatorias son una via de circulacion posterior; no son evidencia
   de la tesis artistica y no deben mezclarse con ella.

## Tesis de proyecto

El portafolio se presenta como un organismo: un archivo que no solo almacena
obras, sino que permite recorrer relaciones entre percepcion, medida, texto,
forma, tiempo y contexto. La navegacion es parte de la obra y tambien una
herramienta de lectura.

La propuesta tiene tres salidas coordinadas:

- **Experiencia:** el visitante navega una capa ligera de vectores, texto,
  color y relaciones antes de cargar medios pesados.
- **Obra:** la forma no ilustra simplemente un contenido; el comportamiento
  del sistema hace visible la tension entre lo que se ve, lo que se lee y lo
  que queda fuera.
- **Herramienta:** el artista puede editar el archivo, corregir asociaciones
  y producir distintas lecturas publicas sin duplicar la base.

## Arquitectura de presentacion

### Archivo pesado

Conserva originales, videos, historias, descripciones, metadata, procesos,
eventos, venues, colaboraciones, versiones de propuesta y decisiones. Su
funcion es preservar procedencia y permitir una revision posterior.

### Organismo ligero

Proyecta la misma base mediante SVG, GLSL, ASCII, texto, color y navegacion.
Su funcion es dar una experiencia publica de bajo peso y no depender de que
el visitante cargue todo el archivo. La capa pesada aparece solo cuando una
obra o registro lo necesita.

El `readme.svg` queda aplazado por decision del artista y no forma parte del
criterio de cierre de este expediente.

## Como mejorar el borrador Fondart

MAK debe trabajar en cuatro operaciones separadas:

1. **Diagnosticar:** detectar saltos entre tesis, experiencia, metodologia,
   presupuesto, cronograma y resultados.
2. **Reestructurar:** ordenar el proyecto para que un evaluador entienda que
   se produce, que experimenta el visitante y que queda disponible despues.
3. **Contrastar:** marcar afirmaciones que necesitan fuente primaria,
   colaborador profesional, prueba de usuario o limitacion explicita.
4. **Proponer:** entregar una version mejorada con cambios trazables, no
   borrar la version original ni inventar evidencia.

La version mejorada debe distinguir siempre:

| Capa | Puede afirmar | No puede afirmar sin verificacion |
|---|---|---|
| posicion artistica | intencion, experiencia, lenguaje, metodo de obra | resultado cientifico universal |
| prototipo | comportamiento observado, tecnologia usada, limitaciones | eficacia clinica |
| investigacion | dato citado y fuente primaria | conclusion basada solo en intuicion |
| comunidad | participacion, accesibilidad, consentimiento y archivo | impacto medido sin datos |
| postulacion | actividades, entregables, presupuesto y cronograma | elegibilidad o fechas no verificadas |

## Entregables de MAK

La proxima corrida de mejora debe producir, en este orden:

1. una critica estructural del borrador;
2. un indice de postulacion version 2;
3. una matriz de afirmaciones con `confirmada`, `requiere_fuente`,
   `interpretacion_artistica` o `pendiente_humano`;
4. una tabla de cambios que conserve el texto original y explique cada
   modificacion;
5. una lista de convocatorias compatibles, separada del expediente y sujeta
   a fuente oficial, fecha y elegibilidad verificadas.

El resultado no entra automaticamente al ledger como verdad ni se publica.
Debe quedar como `draft_for_critique` hasta que la version y sus afirmaciones
sean revisadas.

## Revision estructural externa

Watsonx y AWS revisaron una copia redactada de este brief. Sus observaciones
son orientacion de estructura, no evidencia ni aprobacion de la postulacion.
Coinciden en cuatro mejoras concretas:

- explicar con mayor precision la relacion entre tesis artistica,
  experiencia del visitante y entregables;
- describir mejor como se relacionan el archivo pesado y el organismo ligero;
- separar con mas claridad postura artistica, afirmacion verificable y
  resultado esperado;
- demostrar la experiencia con una prueba pequena, sin presentar el
  prototipo 3D como dependencia tecnica.

Las brechas quedan registradas como tareas: faltan pruebas de experiencia de
usuario, fuentes primarias para las afirmaciones factuales y confirmacion de
convocatorias compatibles. La decision de aplazar `readme.svg` se mantiene.
La siguiente version debe resolver estas brechas sin borrar el borrador.

## Estructura propuesta v2

Esta es una estructura de trabajo derivada de ambas revisiones; no es aun la
postulacion final:

1. **Posicion y contexto:** que problema artistico nace del archivo y por que
   el autor necesita esta forma de presentarlo.
2. **Tesis y experiencia:** que se propone explorar y que hace el visitante,
   sin confundir la navegacion con un resultado clinico o cientifico.
3. **Arquitectura de dos capas:** que conserva el archivo pesado y que
   proyecta el organismo ligero, incluyendo como se relacionan.
4. **Obra y prototipo:** que experiencia visual se produce y como el double cup
   sirve de referencia sin convertirse en dependencia tecnica.
5. **Herramienta para el artista:** que puede editar, ordenar, corregir y
   exportar el autor despues del desarrollo.
6. **Comunidad:** que registros, colaboraciones, consentimiento y acceso se
   conservan, sin prometer impacto no medido.
7. **Produccion:** entregables, etapas, presupuesto y cronograma comparables
   con una convocatoria real.
8. **Evidencia, riesgos y evaluacion:** que se probara, que queda pendiente y
   que no se afirmara sin fuente o decision humana.

### Matriz inicial de afirmaciones

Se adopta la lectura conservadora cuando Watsonx y AWS no clasifican igual:

| Afirmacion | Clasificacion | Evidencia o accion |
|---|---|---|
| El portafolio se presenta como organismo | interpretacion_artistica | declaracion del artista y prototipo de navegacion |
| La navegacion es parte de la experiencia de obra | interpretacion_artistica | prueba de recorrido y registro de decisiones |
| El prototipo double cup aporta forma, proporcion y estados de movimiento | confirmada | archivos del prototipo y documento tecnico |
| El archivo pesado conserva originales, relaciones y versiones | confirmada local | indice del archivo y contrato de proyeccion |
| El organismo ligero mejora la participacion comunitaria | pendiente_humano | definir prueba de uso y criterio de accesibilidad |

La tabla de cambios conserva el borrador original: cada reescritura futura debe
referir su seccion, motivo y evidencia, nunca sustituir silenciosamente el
texto anterior. Las convocatorias candidatas siguen en
`convocatorias_mak_ruta.md` y en el radar, separadas de esta tesis y sin estado
de vigencia.

## No objetivos

- No transformar el prototipo 3D en una dependencia de MAK.
- No convertir el proyecto en una aplicacion medica.
- No publicar el contexto personal sensible del autor por defecto.
- No unir convocatorias, archivo comunitario y tesis artistica en un solo
  informe generico.
- No resolver ahora la animacion del `readme.svg`.

## Criterio de avance

La propuesta mejora de verdad cuando puede responder, sin ambiguedad:

1. que experiencia recibe el visitante;
2. que obra o prototipo se produce;
3. que herramienta queda para el artista;
4. que parte beneficia a la comunidad;
5. que afirmaciones son verificables y cuales siguen siendo postura
   artistica.
