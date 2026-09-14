# svg — el vaso semantico

Rama de trabajo. Sistema generativo que **lee este repositorio** y produce un
SVG autoanimado: sin JavaScript, sin frames, sin GIF. Solo CSS `@keyframes`
y SMIL dentro del propio documento.

`arte-ascii-readme.svg` (raiz) es obra terminada y **no se toca**. Esto es
tejido nuevo, en archivo nuevo, como manda la regla.

---

## De que va

El punto de partida es una tesis sobre la imagen: **una ilustracion contiene
informacion potencial que hay que LEER para que tome valor**. La misma razon
por la que existen `plano` / `rider`, y antes el plano de teatro: dejar de
pelear con anclas de Illustrator y construir algo que sirva a futuro en vez
de a una entrega.

Aqui eso se lleva al limite: no hay ningun pixel decorativo. Cada elemento
visible afirma un dato medido del repo, y si el dato falla, el fallo se ve.

**vibecodeine** — hacer algo sin saber como se hace (coding) contra una
sustancia que inhibe y estimula a la vez (codeina). El sistema reparte los
dos en capas que no se tocan:

- la **MATERIA** es el proyecto: deriva con cada commit. Es el coding.
- la **FORMA** es el vaso: la referencia que no puede derivar. Es la codeina.

De lejos deberia leerse una figura; de cerca, el grafo real de lo que el repo
dice de si mismo.

---

## Las tres capas de `union.svg`

| capa | que es | de donde sale |
|---|---|---|
| TERRENO | el mapa de cicatrices como relieve ascii, con luz que gira y se ocluye de verdad | `polos.py` + `oclusion.py` |
| MATERIA | el netlist PPMI de HEAD, ruteado con A* ortogonal sobre la grilla de caracteres | `cableado.py` |
| FORMA | el contorno de la altura a lo largo de 13 estados de la historia, interpolado con SMIL | `motor.py` |

---

## El problema del 0 y el 255

Para cualquier mapa en escala de grises hay que decidir que es el minimo y
que es el maximo. Aqui la pregunta no era tecnica: **cuales son los polos del
vibecoding.**

La respuesta que se implemento, en `polos.py`:

    H = normalizar( max(E - P, 0) )

- **255** — la zona donde el exceso de error sobre placer es maximo. El
  racimo de terminos del que el repo SOLO habla cuando algo se rompio.
  Cicatriz pura.
- **0** — dos cosas distintas que el suelo junta: **placer asintomatico**
  (hubo trabajo y no dejo rastro de dano) e **ignorancia** (nunca paso nada
  ahi). Por eso se devuelve tambien el campo de soporte `S`: el suelo de este
  mapa no es homogeneo y no se disimula.

**El error se mide por PERSISTENCIA, no por densidad**: dias distintos con al
menos un fix que menciona el termino, no cantidad de fixes. La densidad esta
contaminada por el tamano del commit.

**Por que se resta el placer si el placer no deja rastro.** Precisamente por
eso. `P` no excava — de ahi el `max(...,0)`, nunca hay altura negativa. `P`
se resta como **modelo nulo**: mide cuanto habla el repo de una zona por el
mero hecho de estar viva. Un termino que aparece tanto en commits de placer
como de error no tiene cicatriz, tiene verbosidad.

Y es medible, no retorico. Sobre este repo:

    corr(E crudo, actividad) = 0.96     <- decoracion con otro nombre
    corr(H rectificado, act) = 0.13     <- ya no

---

## Los hallazgos

**Las cicatrices de este repo** son `context`, `src`, `flujo`, `tests`,
`handoff`. `claude` cae al fondo pese a sus dias de fix porque tambien
acumula placer. Lo que cronicamente se rompio no es el producto: es **como el
proyecto se pasa informacion a si mismo.**

**El vaso se descentro.** Con la altura honesta, la forma dejo de estar en el
centro: la cicatriz vive abajo a la izquierda y el circuito de HEAD habla de
otra cosa. Solo el **3.7%** del cobre cae dentro de la forma (antes 17.8%,
cuando ambas capas median lo mismo: "donde hay texto"). El dano acumulado y
la conversacion actual estan en zonas distintas del mismo espacio. Es el
hallazgo, no un bug — y el costo fue perder la lectura "de lejos es un vaso".

---

## Las mentiras, y quien las encontro

Criterio de la pieza: si algo afirma codificar un dato y no lo hace, es una
mentira, aunque se vea bien. Se encontraron cinco.

1. El **color** de cada traza decia ser fuerza PPMI y era una paleta
   rotativa. *(confesada por mi)*
2. El **pulso** corria a la misma velocidad en toda traza. *(confesada)*
3. El **relieve era codigo muerto**: cada regla declaraba `opacity:AMB` y
   encima le aplicaba `animation` sobre la misma propiedad. La animacion gana
   siempre. `relieve.py` entero y 41 KB de CSS no pintaban un pixel, y la
   leyenda decia "luz: relieve". *(la encontro una auditoria adversarial)*
4. **El vaso no existia el 27% del ciclo**: los primeros estados tenian area
   cero y el peor frame caia en la costura del loop. *(auditoria)*
5. **Contraste 1.05:1**: la rampa de color usaba solo su cuarto frio porque
   `t` era min-max sobre una distribucion sesgada. *(auditoria)*

Las cinco estan corregidas en `union.py`. `sintesis.py` se conserva sin
arreglar, como registro de las tres primeras. El informe completo esta en
`projects/cultura/doublecup/svg/doc/auditoria.md`.

---

## Estructura

    sistema/       los .py, en orden de construccion (ver LEEME.md)
    salidas/       los .svg generados
    capturas/      frames de referencia (Playwright, tiempos reales de reloj)
    doc/           la auditoria adversarial
    referencias/   material visual de entrada
    LEEME.md       instalacion y como correrlo

## Correr

    pip install -r requirements.txt
    cd sistema
    python3 union.py --repo /ruta/a/este/repo --salida ../salidas/union.svg

El clon tiene que ser **completo**: `git fetch --unshallow` si hace falta.
La historia entera es el material.

## Abierto

- `servidor.py` — regeneracion por visita. Es lo que justifica que la pieza
  salga de GitHub y viva en portafolio propio.
- Costo del DOM: ~8.500 `<tspan>` y ~8.000 animaciones activas. El peso (620
  KB, 60 KB gzip) no es el problema; el repintado si.
- Las posiciones de nodo se reparten por rango en cada eje: **la cercania
  entre nodos no es distancia semantica** y el espectador la va a leer como
  si lo fuera.
