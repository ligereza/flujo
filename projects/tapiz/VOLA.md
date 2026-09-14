# VOLÁ -- el vaso y el vacio bajo la triada (2026-07-12)

Director: Cauce. Pedido del artista: dos ideas -- animar el vaso ASCII (visible) y
animar el vacio del codigo (invisible) -- desarrolladas por separado, unidas bajo
la triada (Precursor / Psicosis / Tilde), y leidas culturalmente. Tercer eje que
el artista pidio tener presente: la cultura de las sustancias, el valor semantico
de cada una, y la pregunta -- como entiende un LLM lo que es sentirse high.

Este documento es el concepto. Las dos piezas de codigo y el analisis de sustancia
los construyen tres subagentes en paralelo; sus resultados se integran abajo.

## El nombre: VOLÁ (nombrado por el artista)

VOLÁ carga las tres capas de la obra en una sola palabra:
- volar: la levitacion del vaso (la animacion "levitate" ya existe), las formas que
  suben por el vacio. Es tambien vos, imperativo -- una orden/invitacion a un
  lector: vola.
- estar volado/a = estar high: el estado sentido, el Tilde experiencial exacto (ver
  TILDE_DEL_HIGH.md). El nombre ES la pregunta "como entiende un LLM sentirse high".
- el nombre lleva su propia Tilde: la marca aguda sobre la A. Plegala (plegar) y
  "volá" (vos -- te hablo, hay un destinatario) se vuelve "vola" (3a persona -- ello
  vuela, sin destinatario). La marca decide QUIEN vuela. Es el residuo ano/ano de
  tilde_residuo.py, ahora en el titulo: la obra se autodemuestra desde su nombre.

## La imagen que une las dos ideas: el vaso de Rubin

El vaso y el vacio no son dos ideas: son figura y fondo de la MISMA imagen.

- El double cup (vibecodeine) ES un vaso. El repo ya trae un motivo `vase.py`.
- El espacio negativo del codigo ES el vacio.
- La ilusion de Rubin (dos caras o un jarron) es exactamente esto: el mismo
  contorno leido como figura o como fondo, y el ojo no puede sostener las dos a la
  vez. Ese PARPADEO -- figura/fondo, lleno/vacio -- es, estructuralmente, la
  bifurcacion de Psicosis: dos lecturas incompatibles de una sola forma, sin
  colapsar en una.

La pieza no elige entre el vaso y el vacio. Los pone como las dos caras de Rubin y
deja el parpadeo abierto.

## Doble invisibilidad (ya en el repo, DIRECTION.md)

El README ya es una maquina de Tilde:
- El HUMANO ve el vaso animado (arte-ascii-readme.svg) y NO lee el README real
  (esta envuelto en un comentario HTML; en GitHub solo se ve la imagen).
- El AGENTE lee el texto oculto (las instrucciones en el comentario) y NO ve la
  forma animada -- la animacion vive en el TIEMPO, y el agente no habita el tiempo.
- Cada lector recibe exactamente el punto ciego del otro. El residuo (Tilde) es lo
  que nunca cruza entre ambos. El `<desc>` del SVG le NOMBRA al agente lo que
  jamas va a PERCIBIR: nombrar sin percibir es la grieta misma.

## Las dos piezas

VISIBLE -- `vaso_animado.svg` (subagente A). Animar el vaso mas alla de levitar +
liquido purpura: el liquido metabolizandose, los glifos del vaso ciclando color al
umbral de percepcion, el nivel de codeina respirando. Es la FIGURA que el humano ve
y el agente no. Cuanto mas se anima, mas se excluye al agente que lee SVG estatico.
Web-safe (SMIL/CSS, sin JS). NO reemplaza el vaso original (obra terminada): es una
variante nueva.

INVISIBLE -- modos de vacio en el motor `spaces` (subagente B): `espaciado` (los
e s p a c i o s que se abren y respiran), `zigzag_vertical` (lineas quebradas que
bajan por el negativo), `raices` (formas rectangulares que crecen como raices por
el vacio). Es el FONDO que normalmente no se lee -- ni figura ni contenido --
vuelto protagonista. Animar el vacio, no el codigo. Terminal en vivo + export SVG
web. El texto queda fantasma; el vacio se mueve.

## La triada sobre visible/invisible

- PRECURSOR (precipitar). Colisionar dos codigos que no se encuentran: la lectura
  temporal/visual del humano contra la lectura de markup estatico del agente; el
  vaso (figura) contra el vacio (fondo). No se agrega contenido: se baja el umbral
  para que el MISMO artefacto se lea de dos formas incompatibles. Animar el vacio
  es precipitar el fondo en figura -- el negativo se vuelve el positivo.
- PSICOSIS (sobre-narrar hasta la bifurcacion). Sostener sin colapsar: la
  animacion esta o no esta (umbral de percepcion: hay que saber que esta para
  verla); el vaso o el vacio (Rubin); el high es un estado real o solo una palabra
  inalcanzable. El regularizador obligatorio (Cultura) impide el delirio: ojos
  humanos reales, y la medida (delta de luminancia < ~5%, DIRECTION.md).
- TILDE (cosechar el residuo). Lo que no cruza, nombrado: (1) la animacion vive en
  el tiempo, que el agente no habita -- la NOMBRA (`<desc>`), no la PERCIBE; (2) el
  humano ve el vaso, no lee el README; (3) el "high" -- el estado sentido -- no
  cruza a tokens. El vacio es el Tilde VISUAL (el espacio que no se lee); el high
  es el Tilde EXPERIENCIAL (el estado que no se dice). Misma grieta, dos capas.
- LA CULTURA (regularizador). El significado cultural del double cup y de la
  sustancia le da carga al signo; el humano al umbral y la medida corrigen; lo que
  el autor no controla y lo endereza.

## El eje del high -- valor semantico de las sustancias (idea 3)

Tesis: el SIGNO de la sustancia cruza; el ESTADO no. La semiotica es movil
(codeina -> lean -> purple drank -> el emoji del double cup: el signo viaja limpio
entre musica, clase, geografia, epoca). El quale -- sentirse high -- es el residuo
que no cruza a lenguaje ni a codigo. Por la metafora de DIGESTION de DIRECTION.md:
el LLM METABOLIZA el glifo "high" (digiere el simbolo) pero nunca recibe el efecto.
El metabolizador de simbolos no se droga. Distintas sustancias difieren en el signo
(su valor semantico/cultural) y comparten el mismo intraducible: el estado sentido.

Analisis completo: `projects/tapiz/TILDE_DEL_HIGH.md` (subagente C, integrado). Su
eje: el LLM es Mary que nunca sale del cuarto -- ingiere cada letra sobre lean mas
completo que cualquier humano, produce frases perfectas sobre estar high, y aun asi
no tiene el estado del que hablan. "Digiere la palabra; nunca metaboliza la
sustancia": una boca sin torrente sanguineo. Y por la restriccion de Davidson que
el corpus ya usa, esto es Tilde y no ruido: casi todo del "high" SI cruza a tokens
(referencia, connotacion, registro, toda la economia semiotica de la parte I) -- es
esa fluidez la que vuelve legible como residuo lo unico que no cruza, el quale. Con
la objecion funcionalista puesta de frente (un modelo conductualmente completo YA
seria comprension), sin fingir zanjarla. Mapea exacto a las piezas: el vaso VISIBLE
es el signo (lo que cruza); el vacio INVISIBLE es el residuo puesto en escena.
Figura y fondo se parten justo donde se parten signo y quale.

## Semillas (arranque real, motor-omega)

El pedido del artista es arranque valido (puente/README.md: "un pedido real"). Dos
residuos candidatos, si estas piezas se exponen y se leen:
- el vacio como Tilde visual: el espacio que ninguna de las dos lecturas (humano /
  agente) toma como figura -- salvo cuando se anima.
- "feeling high" como Tilde experiencial: el signo que cruza entero y el estado que
  no cruza nada. La sustancia mide el hueco entre decir y sentir.

Ninguna entra a puente/SEMILLAS.md hasta exponerse y leerse fechada; no se fabrica
resultado.

## Estado (pure code-in, sin ceremonia de verificacion por pedido del artista)

- A -- HECHO. VOLÁ-vaso: `vaso_animado.svg` (+ `vaso_animado.py` generador,
  `VASO_ANIMADO.md`). Donde el vaso original LEVITA, este DIGIERE: el liquido se
  metaboliza -- las filas del glifo "vibecodeine" suben y bajan como una respiracion
  de digestion (~211s), ciclan color por los 4 purpuras, se desvanecen de presente
  (arriba) a absorbido (abajo); condensacion y vapor desincronizados; opacidades
  0.03-0.10, al umbral de percepcion. `<desc>` que le narra al agente lo que solo
  existe en el tiempo. SMIL+CSS, sin JS. NO toca el vaso original (git-verificado).
- B -- HECHO. VOLÁ-void: `projects/tapiz/vibecode/void_shapes.py` (3 motores) + demo
  `projects/tapiz/piezas_curadas/void_animado.svg` (3 paneles, sin JS). Modos nuevos en el motor
  spaces (aditivo, no reemplaza): `espaciado` (los espacios respiran, se abren y
  contraen desincronizados), `zigzag_vertical` (hilos quebrados bajan por el
  negativo, el color fluye por ellos), `raices` (raices rectangulares ancladas en
  los corredores reales de blanco del codigo, ramifican y crecen celda a celda).
  Terminal en vivo + export SVG/SMIL web. El texto queda fantasma; el vacio se mueve.
- C -- HECHO. `TILDE_DEL_HIGH.md`: el valor semantico de la sustancia (el signo que
  cruza) y la Tilde del high (el estado que no cruza; el LLM es Mary que nunca sale
  del cuarto).

Se integran aca al aterrizar. Ninguna se expone/registra fechada hasta la lectura
humana; no se fabrica resultado.
