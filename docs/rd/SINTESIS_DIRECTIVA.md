# Sintesis para la directiva: 5 informes de investigacion RD (F3e)

Fecha: 2026-07-22. Preparado a partir de 5 informes generados por el organo
research de MAK (LLM + busqueda web). Version completa de cada uno en
`docs/rd/informes/`. Revision humana de los 5 informes PENDIENTE.

## AVISO DE CALIDAD (leer antes que el resto)

Los 5 informes salieron de un pipeline automatico con LLM gratuitos que
tuvieron error de cuota (429) durante toda la corrida (ver bloque `meta`
de cada archivo). Resultado: casi todas las fuentes citadas son papers
metodologicos genericos sobre "que es la investigacion descriptiva"
(Redalyc, PUCP, Dialnet, Concepto.de), NO fuentes especificas y
verificadas sobre Marquis/Mecke/Mandelin, DanceSafe/Energy Control/TEDI,
ni la Ley 20.000 chilena en concreto. El informe legal cita una tesis
peruana de secundaria y un tomo universitario venezolano -- ninguna es
ley chilena, reglamento del ISP ni jurisprudencia. TRATAR TODO COMO PUNTO
DE PARTIDA. Ningun bullet aqui reemplaza asesoria legal real.

## 1. Que tenemos hoy

El repo ya tiene un catalogo consultable de reactivos y packs (`rd-db`,
proyeccion regenerable desde JSON), y una base de datos de campo
privacy-first (`rd-datos`, F3a): el schema NO tiene columnas de identidad
(nombre/rut/telefono/email) por diseno -- lo que no existe como columna no
se puede filtrar por accidente -- mas un filtro que escanea y rechaza o
sanitiza texto libre con PII antes de guardarlo. Con eso mas los 5
informes de hoy, ya podemos generar reportes de estado del arte y opciones
tecnicas sobre pedido, aunque con la calidad limitada descrita arriba.

## 2. Hallazgos clave por informe

**Reactivos colorimetricos (Marquis/Mecke/Mandelin)** -- fuentes debiles:
- Los 3 reactivos tienen limites conocidos (falsos positivos, fallan con
  analogos de fentanilo y catinonas nuevas).
- Tendencia 2026: lectores digitales/apps que cuantifican el color y
  reducen la subjetividad de la lectura visual.
- Buenas practicas sugeridas: doble verificacion y registro fotografico.
- Fuente citada (generica, no especifica al tema):
  https://www.researchgate.net/publication/315842152

**Bases de datos de testeo (DanceSafe, Energy Control, TEDI)**:
- Esquema tipico: ID de muestra + metadatos (fecha, evento) + resultado
  (metodo, sustancias, pureza, nivel de confianza).
- Anonimizacion tipica: pseudonimizacion de IDs + agregacion espacial y
  temporal (nunca hora exacta) -- coincide con el diseno ya usado en
  `rd-datos` de este repo.
- Tension reportada: rapidez de alerta vs. verificacion instrumental.
- Fuente citada (unica, repetida en casi todo el informe):
  https://dialnet.unirioja.es/descarga/articulo/8270501.pdf

**App publica de reduccion de danos** -- el mas util de los 5:
- PWA (React/Vite + hosting gratis) es mas barata y de mayor alcance que
  app nativa para una ONG con presupuesto limitado; casos citados (Safer,
  WAP) no verificados de forma independiente.
- Riesgo marcado por el propio informe: la Ley 19.628 (proteccion de
  datos personales) exige consentimiento y trazabilidad minima.
- Fuente sobre sistema de salud chileno (contexto, no legal):
  https://medicina.udd.cl/files/2019/12/Estructura-y-funcionamiento-del-sistema-de-salud-chileno-2019.pdf

**App interna de metricas para directiva** -- el mas generico de los 5:
- No entrega un listado verificado de dashboards FOSS self-hosted 2026;
  el propio informe admite que falta ese inventario.
- Punto util: la eleccion de metricas y su estetica ya comunican una
  postura (que se muestra, que se omite), a pensar al disenar el panel.
- Sin fuente fuerte que citar; todas son metodologicas genericas.

## 3. Marco legal (Ley 20.000) -- VERIFICAR CON ABOGADO, todo el bloque

El informe legal se basa en fuentes no-chilenas y no-oficiales (ver aviso
de calidad). Se listan sus bullets tal cual, sin agregar interpretacion
propia, y marcados para revision profesional real:

Segun el informe, una ONG chilena PODRIA (VERIFICAR CON ABOGADO):
- Dar informacion preventiva, educacion y capacitacion.
- Distribuir insumos esteriles (jeringas, kits de prueba).
- Hacer pruebas de pureza bajo convenio con laboratorio acreditado y
  reportar resultados al ISP.
- Recolectar y difundir datos anonimos con fines de vigilancia
  epidemiologica.
- Recibir financiamiento publico/privado si no se usa para comprar drogas.

Segun el informe, una ONG chilena NO PODRIA (VERIFICAR CON ABOGADO):
- Vender o distribuir sustancias controladas.
- Diagnosticar o prescribir sin personal medico certificado.
- Custodiar o manipular muestras sin autorizacion expresa del ISP (riesgo
  de que se interprete como trafico).
- Operar un espacio de consumo supervisado (el informe dice que no hay
  norma explicita que lo respalde en Chile).

El propio informe marca como "zona gris" el drug checking en terreno y
pide revision normativa 2025-2026 y jurisprudencia real -- eso no se hizo
en esta corrida. Antes de operar cualquier punto de arriba, se necesita
una lectura de abogado sobre la Ley 20.000 vigente, no este resumen.

## 4. Propuesta de camino

a) **Base de datos de testeo privacy-first: YA CONSTRUIDA.** `rd-datos`
   (F3a) ya implementa el patron que describen DanceSafe/Energy Control/
   TEDI: PII imposible por schema (no hay columna de identidad), fecha sin
   hora (evita reidentificar por marca fina), y filtro de texto libre que
   rechaza o sanitiza PII antes de guardar. No hace falta reinventar esto.

b) **Panel para la directiva via tunel:** exponer un dashboard de solo
   lectura sobre esos datos agregados (sin filas individuales sensibles),
   accesible por la directiva sin exponerlo al publico. No se eligio
   stack todavia -- el informe 5 no dio un listado confiable de opciones
   FOSS; conviene decidirlo aparte con criterios propios (soberania de
   datos, mantenimiento con recursos de la ONG).

c) **App publica: fase posterior.** El informe 4 sugiere PWA (React/Vite,
   hosting gratuito tipo GitHub Pages/Netlify, base de datos free-tier)
   como opcion mas barata y de mayor cobertura que una app nativa, con
   app nativa (Flutter/React Native) como extension futura si hace falta
   acceso a hardware del telefono. Ninguna decision de arquitectura debe
   tomarse solo con este informe: falta validar requisitos reales de la
   Ley 19.628 con la CNPD o un abogado antes de manejar cualquier dato de
   consumo de un usuario publico.

## 5. Que se necesita de la directiva

1. **Acta de acuerdo sobre datos:** que la directiva apruebe formalmente
   que datos de campo se registran (ya sin PII por diseno) y quien puede
   ver el panel agregado antes de construirlo.
2. **Validacion del marco legal:** encargar a un abogado (idealmente con
   experiencia en Ley 20.000 y ONG de salud) que confirme o corrija el
   bloque 3 de este documento contra la norma vigente y jurisprudencia
   real, antes de que la ONG ofrezca cualquier servicio de analisis o
   testeo apoyado en esta informacion.
