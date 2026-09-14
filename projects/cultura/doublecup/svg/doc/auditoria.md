# Auditoría adversarial de `sistema/sintesis.svg`

Auditor externo. No se modificó `sintesis.svg` ni `sintesis.py`.
Fecha: 2026-07-25. Archivo auditado: 565.362 B (552 KB), 3.321 líneas.

Metodología: parser XML (`xml.etree`), análisis léxico del CSS y del árbol,
Chromium/Playwright headless (viewport 676x904) con 10 capturas a t = 0.3, 2,
4.5, 7, 9, 13, 17, 20, 22, 25.5 s más una pasada con `reducedMotion:'reduce'`,
inspección de estilos computados en vivo, y lectura de `sintesis.py`,
`motor.py`, `cableado.py`, `relieve.py`.

Scripts añadidos por la auditoría (no tocan la obra): `/tmp/proto/audit_cap2.js`,
`/tmp/proto/vfy.js`. Capturas: `/tmp/proto/aud_t*.png`, `/tmp/proto/aud_reduced.png`.

---

## Resumen ejecutivo

Lo que está bien, en una línea cada cosa: el XML es válido; no hay ids colgando
ni duplicados; los 4 ids (`cristal`, `tinte`, `mv`, `ml`) están todos referenciados
y todos los `url(#…)` resuelven; los 13 `values` de cada `<animate>` tienen los
mismos 129 comandos, así que la interpolación de `d` es real y no un salto
discreto; los `keySplines` (12) casan con los 12 intervalos; `glifos()` devuelve
exactamente `len(cam)` entradas, así que el desfase del pulso está bien
normalizado; ningún label de nodo sale truncado (78 = 26 x 3 copias, todos con
`]` de cierre); 0 trazas sin ruta.

Todo lo demás está mal en algún grado. Los tres defectos que hunden la pieza son:
(1) la iluminación de relieve es **código muerto**, sobrescrita por la animación;
(2) el vaso **no existe** durante ~7 de los 26 s del ciclo, y cuando existe no
tiene silueta de vaso; (3) el contraste global es de **1,05:1**, es decir, la
obra es indistinguible del fondo negro salvo en unos pocos píxeles.

---

## CRÍTICO

### C1 — El relieve no ilumina nada: `AMB` es CSS muerto
**Severidad: crítica. Categoría: honestidad del mapeo.**

`sintesis.py:140-141` emite por cada glifo:

```
.g0_0{opacity:0.76;animation:p0 2.60s -0.000s infinite linear}
```

`opacity:0.76` es el ambiente difuso calculado en `sintesis.py:124`
(`AMB = clip(0.52 + 0.55*nz*LZ + 0.30*F/Fmax, 0.45, 1.0)`). Pero la animación
`p{t}` **anima la misma propiedad `opacity`** con `infinite`, y una animación en
curso gana siempre sobre la declaración estática. El valor de relieve nunca se
muestra.

Evidencia medida en Chromium (`vfy.js`), con la pieza corriendo:

```
{"computada":"0.62","declarada":"0.76","muestras":207,"mediaComputada":"0.649"}
```

La opacidad declarada por relieve es 0,76 y la computada es 0,62 — exactamente
la meseta del keyframe. Sobre 207 celdas muestreadas al azar la media computada
es 0,649, o sea todas están en 0,62 salvo las pocas que pasan por el frente del
pulso.

Consecuencia directa: la línea de la `<desc>` ("El brillo base de cada celda lo
da el relieve del propio campo") y el `luz: relieve` de la leyenda visible en
pantalla son **falsos**. Es exactamente la tercera mentira del mismo tipo que ya
se corrigió dos veces: `relieve.py` entero (9,2 KB), `normales()`, `LZ`, `K_REL`
y los 41.054 B de `opacity:` en el SVG no producen ni un píxel de diferencia.

Agrava: el rango de `AMB` es 0,73–1,00 (28 valores distintos). Aunque no
estuviera muerto, un 27 % de rango de opacidad sobre glifos que ya están a
1,05:1 de contraste sería invisible de todos modos.

**Arreglo:** mover el ambiente a un canal que la animación no toque —
`fill-opacity:{amb}` en la regla `.g` y dejar `opacity` para el pulso, o mejor,
hacer que el keyframe interpole `opacity:{amb}` -> `opacity:{amb*0.62}` por celda
(exige un keyframe por bucket de ambiente, ~28) para que el relieve module el
pulso en vez de ser tapado por él.

---

### C2 — El vaso literalmente no existe durante el 25 % del ciclo
**Severidad: crítica. Categoría: legibilidad.**

Los tres primeros estados de la historia tienen área 0. Sellos del propio SVG:

```
2026-06-30  bee102e  0 celdas
2026-07-04  1657e7d  0 celdas
2026-07-06  3b9eaa5  0 celdas
2026-07-09  f6fda67  382 celdas
```

Y las máscaras lo confirman: bbox de los `values` de `#mv`, estado por estado:

```
mv: 0x0, 0x0, 0x0, 202x180, 234x215, 177x167, 173x144, 234x227,
    252x251, 258x251, 275x263, 276x264, 0x0   (el 13.º es el retorno al 0.º)
```

El `d` de esos estados es `M209.5,409.3L209.5,409.3L209.5,409.3…` — 129 comandos
todos al mismo punto. Máscara de área nula: las capas `vidrio` y `liquido` quedan
completamente ocultas. Con `CICLO_HIST = 26 s` y 12 estados, eso son los primeros
**6,5 s de cada 26**, más la vuelta al estado 0 al final: ~7 s por ciclo, **27 %
del tiempo**, en los que el espectador ve solo el sustrato a `opacity:.13`.

Verificado visualmente: `aud_t0.3.png` y `aud_t2.png` no tienen ninguna zona
iluminada; el porcentaje de píxeles con luminancia >20 sobre el fondo es 0,31 % y
0,18 % respectivamente, contra 0,64 % en `aud_t22.png`.

El estado 12 (`d` degenerado) es además el que cierra el bucle, así que la
transición 11 -> 0 es un colapso de toda la forma a un punto: el peor frame de la
pieza está exactamente en la costura del loop.

**Arreglo:** filtrar en `construir()` los estados con `area_vidrio == 0` antes de
armar la lista (o arrancar `sel` desde el primer commit con área > 0), y no
volver a `estados[0]` sino cerrar el loop con el último estado repetido.

---

### C3 — Contraste 1,05:1: la pieza es prácticamente invisible
**Severidad: crítica. Categoría: legibilidad.**

Medición de luminancia relativa (WCAG) sobre las capturas, fondo `#0a0a0c`
(L = 7,4):

| captura | p99 de L | contraste p99 | máx | px >bg+20 |
|---|---|---|---|---|
| aud_t0.3 | 16 | **1,05:1** | 38 | 0,31 % |
| aud_t2 | 14 | **1,04:1** | 37 | 0,18 % |
| aud_t4.5 | 17 | **1,06:1** | 83 | 0,51 % |
| aud_t9 | 17 | **1,06:1** | 220 | 0,55 % |
| aud_t17 | 17 | **1,07:1** | 125 | 0,60 % |
| aud_t22 | 18 | **1,07:1** | 182 | 0,64 % |

El percentil 99 de la imagen entera está en 1,05:1. El mínimo WCAG AA para texto
es 4,5:1 (3:1 para texto grande). Solo el 0,2–0,6 % de los píxeles supera el
fondo en más de 20 niveles.

Causas acumuladas, todas multiplicativas:
- `.sustrato{opacity:.13}` (`sintesis.py:202`) mata el 87 % de la capa que ocupa
  el 100 % del lienzo.
- El keyframe deja las trazas en `opacity:.62` el 84 % del tiempo
  (`sintesis.py:133-134`).
- 40 de las 59 trazas tienen color en el extremo frío de la rampa (ver H2), a
  partir de `#384e75`, que sobre negro ya es un contraste bajísimo.
- El `feColorMatrix` `cristal` solo multiplica los canales por ~0,9–1,0 y suma un
  offset de 0,15–0,20 sobre un rango [0,1]: el "vidrio" apenas aclara.

Esto no es una elección estética defendible como "sutil": a 1,05:1 la mayoría de
los monitores y prácticamente todos los proyectores no muestran nada. El
sub-encargo "se lee como un vaso de codeína **de lejos**" falla: de lejos no se
lee nada.

**Arreglo:** subir `.sustrato` a ~0,30, elevar la meseta del pulso de 0,62 a 0,80
y desplazar el extremo frío de la rampa de `(56,78,117)` a algo alrededor de
`(110,130,180)`, y volver a medir hasta que el p99 pase de 2,5:1.

---

## ALTO

### A1 — La forma que se llama "vaso" no tiene forma de vaso, y sí deriva
**Severidad: alta. Categoría: honestidad del mapeo.**

La tesis del docstring (`sintesis.py:29-34`) dice: "la FORMA es el vaso
(contorno, es la referencia fija, es codeína)" y "el recipiente es la referencia
que no puede derivar". Pero:

1. `anim('c_vidrio')` (`sintesis.py:221`) hace derivar el contorno entre 12
   estados a lo largo de 26 s. Es lo contrario de una referencia fija. El propio
   `<desc>` lo admite dos líneas más abajo ("respira entre 12 estados"): el texto
   se contradice consigo mismo.
2. El contorno sale de `contorno()` (`motor.py:170`), que muestrea 128 rayos
   desde el centroide y umbraliza el campo. Lo que produce es una **mancha
   estrellada**, no un vaso. En `aud_t17.png` y `aud_t22.png` la región iluminada
   es un blob irregular de ~250x260 px centrado a media altura, sin borde, sin
   base, sin pared vertical. Nada en el pipeline impone la silueta de un vaso.
3. La capa `liquido` no es líquido: es el mismo campo con umbral 0,62 en vez de
   0,30, es decir un blob concéntrico dentro del otro. No tiene línea de
   superficie horizontal ni respeta la gravedad. Peor: su máscara es de área nula
   en 7 de los 13 estados (0,1,2,3,5,6,12) y **parpadea de forma no monótona**
   (presente en el 4, ausente en el 5 y el 6, presente en el 7). Un líquido que
   desaparece y reaparece dos veces por ciclo no es un mapeo, es un artefacto de
   umbral.

**Arreglo:** o se declara honestamente que la forma es "el contorno del campo",
retirando la palabra vaso y la palabra "fija" del `<desc>` y del docstring, o se
intersecta el contorno con una silueta de vaso fija y se documenta que la
silueta es un a priori impuesto.

---

### A2 — Las posiciones de los nodos no codifican distancia semántica
**Severidad: alta. Categoría: honestidad del mapeo.**

`cableado.py:85-110` (`colocar`). El comentario reconoce a medias el problema
("el PCA amontona todo en el centro: se conserva el ORDEN de cada eje pero se
reparte por rango"), pero la consecuencia no está declarada en la obra:

- Se toma el **rango** de cada nodo en cada eje por separado y se reparte
  uniformemente: `c0 = 2 + rx/N*(cols-16)`, `f0 = 2 + ry/N*(filas-5)`. Tras esa
  transformación, la distancia entre dos nodos en la imagen ya **no es
  proporcional a nada**: dos términos semánticamente pegadísimos y dos
  antipodales pueden quedar a la misma distancia en píxeles si sus rangos
  difieren igual.
- Peor: es una transformación por eje independiente, así que ni siquiera preserva
  la topología del plano PCA, solo las dos proyecciones ordinales.
- Y encima el bucle antichoque (`for r in range(0, 40)`) puede desplazar un nodo
  hasta **40 celdas** de su posición calculada sin que quede registro. Con
  `cols=100`, eso es hasta el 40 % del ancho del lienzo: un desplazamiento
  arbitrario mayor que casi cualquier señal.

El espectador que "lee el grafo de cerca" leerá cercanía como relación. No lo es.

**Arreglo:** anotar en `<desc>` que la posición codifica solo el orden por eje
del PCA, no la distancia, o sustituir el reparto por rango por un
`force-directed` sobre las distancias PPMI reales y usar el rango solo como
semilla.

---

### A3 — La rampa de color usa solo su cuarto frío; el 68 % de las trazas cae en el primer tramo
**Severidad: alta. Categoría: honestidad del mapeo.**

`t = (v-lo)/(hi-lo)` en `sintesis.py:116`. Distribución real de los 59 valores de
`t`, reconstruida desde los ciclos del CSS:

```
min 0.000   mediana 0.259   max 1.000
t > 0.35 : 19 de 59      t > 0.5 : 9 de 59      t > 0.6 : 4 de 59
```

40 de 59 trazas caen dentro del **primer tramo** de la rampa (0,00–0,35, de
`#384e75` a `#818cf8`), todo azul-índigo. Los tramos morado, magenta y amarillo
—los tres cuartos "calientes" y los únicos con contraste decente— se los reparten
4 trazas. Los 59 colores distintos verificados en el CSS lo muestran: 53 son
azules/índigos, 2 morados, 1 naranja, 1 amarillo.

Lo mismo con el pulso: `ciclo = 9.0 + (2.6-9.0)*t` da a esas 40 trazas ciclos
entre 9,00 s y 6,76 s. Dos ciclos que difieren en un 30 % sobre 7 s son
perceptualmente indistinguibles sin cronómetro. Es decir: la corrección de la
segunda mentira es técnicamente correcta pero **perceptualmente nula para el 68 %
de la pieza**.

Añadido: `t` es min-max **relativo a este render**. La traza más débil siempre
sale exactamente en `#384e75` a 9,00 s y la más fuerte siempre en `#facc15` a
2,60 s, sea cual sea su PPMI absoluto. El color no es comparable entre dos
renders del mismo repo en fechas distintas, lo cual contradice la premisa de una
pieza que se regenera con cada commit.

**Arreglo:** ecualizar `t` por su rango percentil (`t = rank/(n-1)`) para que la
rampa se use entera, y anclar el extremo de la escala a un PPMI absoluto fijo
documentado en `<desc>` para que los renders sean comparables.

---

### A4 — Ninguna concesión a `prefers-reduced-motion`
**Severidad: alta. Categoría: riesgo en navegador / accesibilidad.**

No hay ni una `@media` en todo el archivo (`'prefers-reduced-motion' in svg ->
False`). Verificado en Chromium con `reducedMotion:'reduce'`: la pieza sigue
corriendo las **8.176 animaciones** y la levitación, idéntica a la normal
(`aud_reduced.png`).

Además, SMIL no responde a `prefers-reduced-motion` ni siquiera si se añadiera el
media query en CSS: los dos `<animate>` de las máscaras hay que pararlos con
`begin`/`fill` o con un `<set>`, no con CSS.

**Arreglo:** añadir
`@media (prefers-reduced-motion:reduce){.levita,[class^="g"]{animation:none}}`
y sustituir el `d` animado por el `d` del último estado cuando ese media query
esté activo (requiere generar dos variantes o usar `CSS.supports` sin JS: en la
práctica, congelar el vaso en HEAD).

---

## MEDIO

### M1 — 8.176 animaciones sobre tres copias de un texto enmascarado y filtrado: coste de repintado
**Severidad: media. Categoría: riesgo en navegador.**

Inventario del DOM:

| elemento | cuenta |
|---|---|
| `<tspan>` | 8.469 |
| `<text>` | 16 |
| animaciones activas (`getAnimations()`) | **8.176** |
| reglas CSS | 3.463 |
| `<animate>` SMIL | 14 |
| `<filter>` | 2 (aplicados a 2 grupos de ~100 KB de texto) |

El grupo `.levita` traslada verticalmente, cada 9 s, un subárbol que contiene
**tres copias completas** del bloque de 7.200 celdas, dos de ellas con `mask` y
`filter`. Cada frame de la levitación obliga a Chromium a recomponer dos capas
filtradas de 676x904 y a re-evaluar 8.176 opacidades animadas. En headless, el
contador de `requestAnimationFrame` devolvió **0 frames en 4 s** con la pieza en
marcha, y varias capturas salieron completamente negras (`aud_t13.png`,
`aud_t20.png`, `aud_t25.png`: 3.606 B, lienzo vacío) porque el compositor no
alcanzó a pintar antes del screenshot. Headless no es prueba de fps real en
hardware acelerado, pero sí es evidencia de que la composición no es barata.

`transform-origin:center` en `.levita` (`sintesis.py:205`) es además una
declaración inútil: la animación solo hace `translateY`, para la que el origen es
irrelevante. Ruido.

**Arreglo:** promover `.levita` con `will-change:transform` y, sobre todo,
reducir a una sola copia del bloque (ver M2), lo que divide por tres la
superficie filtrada.

### M2 — 54 % del archivo son tres copias byte a byte del mismo bloque
**Severidad: media. Categoría: costo.**

Reparto real de los 565.362 B:

| sección | bytes | % |
|---|---|---|
| tres `<text class="mat">` | 305.247 | **54,0 %** |
| bloque `<style>` | 212.391 | 37,6 % |
| atributos `class="nN gN_K"` (dentro del anterior) | 144.003 | 25,5 % |
| reglas `.gN_K` | 203.910 | 36,1 % |
| `opacity:` muerto (ver C1) | 41.054 | 7,3 % |
| 59 `@keyframes pN` **idénticos** | 3.648 | 0,6 % |
| `<path>` y `values` de las máscaras | 43.108 | 7,6 % |
| reglas `.nN` (color) | 1.052 | 0,2 % |

Los tres bloques miden **exactamente 101.749 B cada uno**, idénticos. Es la
técnica de prototipo_01 (glifos idénticos en posiciones idénticas) implementada
por copia literal en vez de por referencia.

Ahorros, en orden de retorno:

| optimización | ahorro |
|---|---|
| `<defs><g id="bloque">…</g></defs>` + 2 `<use href="#bloque">` | **203.498 B (36 %)** |
| borrar `opacity:` muerto de las 3.158 reglas `.g` (C1) | 41.054 B |
| fusionar `nN` y `gN_K` en una sola clase con nombre base36 | ~60.000 B |
| un solo `@keyframes p` compartido (los 59 son idénticos) | 3.586 B |
| **total** | **~308 KB, de 552 KB a ~245 KB (-55 %)** |

Matiz honesto: gzip -9 deja el archivo en **60.662 B**, así que en la red la
triplicación cuesta poco. El coste real no es el peso sino el DOM: 8.469 nodos y
8.176 animaciones no se comprimen. La optimización que importa es la de M1/M3,
no la de bytes.

### M3 — 8.175 `<tspan>` de un solo carácter
**Severidad: media. Categoría: costo.**

Verificado: los 8.175 segmentos con clase tienen **longitud 1** sin excepción.
Cada carácter dibujado cuesta ~29 B (`<tspan class="n0 g0_0">-</tspan>`) y un
nodo del DOM. El agrupado por run-length de `sintesis.py:150-161` no puede fusionar
nada porque la clave `k` incluye `g{t}_{kk}`, que es única por celda: la
optimización está escrita pero es inoperante por construcción.

Caracteres reales dibujados: `-` (3.996), `|` (3.102), `+` (1.077). Solo tres
glifos distintos en 8.175 elementos.

**Arreglo:** cuantizar el desfase del pulso a ~24 buckets por traza
(`d = -ciclo * round(24*kk/n)/24`); glifos consecutivos compartirían clase y el
run-length volvería a funcionar, con una reducción esperada de ~3x en `<tspan>` y
en animaciones (de 8.176 a ~2.800), a cambio de un frente de pulso escalonado que
a 6 px por celda es imperceptible.

---

## BAJO

### B1 — La fuente monoespaciada no es opcional: sin ella la grilla se rompe
**Severidad: baja-media. Categoría: validez de render.**

`.mat` pide `ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace`
pero el posicionamiento **no** depende de la métrica de la fuente: cada fila es un
`<tspan x="10" dy="12">`, es decir, `x` absoluto por fila y avance vertical fijo.
Solo el avance **horizontal** dentro de una fila queda a merced de la fuente.

Medición en Chromium: `getBBox()` del bloque da `w = 601,22` para 100 columnas a
`adv_x = 6,0` -> lo esperado son 600,0. El error acumulado es de 1,22 px sobre
601 (0,2 %), o sea la fuente resuelta (`Liberation Mono` / fallback `monospace`)
avanza 6,012 px en vez de 6,0.

Es tolerable, pero **no está garantizado**: la posición de las trazas y de las
máscaras se calcula en el generador asumiendo `adv_x = 6,0` exacto
(`motor.py:53`). En una fuente monoespaciada con otro ratio ancho/alto a 10 px
(p. ej. Consolas, 5,5 px), la última columna se desplazaría ~50 px y las trazas
se saldrían de la máscara del vaso. Y si el sistema no tiene **ninguna**
monoespaciada, el fallback proporcional destruye la grilla por completo.

Un archivo que se llama "el grafo real del repo" no debería depender de una
métrica que no controla.

**Arreglo:** emitir `textLength="600" lengthAdjust="spacingAndGlyphs"` en cada
`<tspan>` de fila, o pasar a `<text>` con `x="10 16 22 …"` explícito por columna.

### B2 — Constantes mágicas duplicadas y desincronizables
**Severidad: baja. Categoría: honestidad / mantenimiento.**

- `LZ = 0.55` está definido **dos veces**: `sintesis.py:55` y `relieve.py:55`.
  `sintesis.py` importa `normales` de `relieve` pero redefine `LZ` en local en vez
  de importarlo. Si uno cambia, el otro no se entera. (Da igual hoy porque el
  resultado es código muerto, ver C1, pero es la misma clase de defecto.)
- El `16%` del keyframe (`sintesis.py:133`) es `LARGO_PULSO = 0.16` de
  `cableado.py:47`, **hardcodeado a mano** en vez de importado.
- `CICLO = 6.0` en `cableado.py:46` ("s que tarda el pulso en recorrer una traza")
  quedó obsoleto y contradice a `PULSO_MIN`/`PULSO_MAX`. Sigue ahí, sin usar.
- `PALETA` en `cableado.py:49` es la paleta rotativa de la primera mentira ya
  confesada. Sigue en el árbol, sin usar. Un lector del código concluiría que el
  color todavía es rotativo.
- `CRUCE` se importa en `sintesis.py:50` y no se usa nunca.
- `sintesis.py:45` importa `math` y `json`; ninguno se usa en el archivo.
- Los coeficientes de `AMB` (0.52, 0.55, 0.30, clip a 0.45–1.0) y los de
  `colocar` (`cols-16`, `filas-5`, `range(0,40)`) no están justificados ni
  documentados. Son ajustes a ojo presentados con la misma tipografía que los
  parámetros derivados de datos.

**Arreglo:** importar `LZ` y `LARGO_PULSO` de sus módulos, borrar `CICLO`,
`PALETA` y los imports muertos, y anotar cada coeficiente estético con un
comentario que diga explícitamente "a ojo".

### B3 — `render()` recibe `sha` y `fecha` de HEAD y no los usa
**Severidad: baja. Categoría: honestidad.**

`sintesis.py:121` declara `render(F, estados, nodos, pos, trazas, p, sha, fecha,
fallidas)`. `sha` y `fecha` no aparecen en el cuerpo. El sello que se ve en
pantalla viene de `estados[i]`, no de HEAD. `main()` desempaqueta `sel[-1]` para
pasarlos y no sirve de nada. Tampoco `campo` (`sintesis.py:244`) se usa en render.

**Arreglo:** borrar los parámetros o mostrar el sha de HEAD junto a la leyenda,
que es lo que la firma sugiere que se pretendía.

### B4 — `keyTimes` del último sello termina en `1.0000;1`
**Severidad: baja. Categoría: validez.**

`sintesis.py:183-184` genera para `i = n-1`:
`keyTimes="0;0.9167;0.9200;0.9967;1.0000;1"` — los dos últimos valores son
iguales. La especificación SMIL exige que la lista sea **estrictamente
creciente** salvo el primero y el último; dos valores idénticos en el borde son
un caso límite que Chromium tolera (el sello se apaga instantáneamente) pero que
otros renderizadores pueden rechazar, invalidando la animación entera del sello.
Con `values="0;0;1;1;0;0"` el intervalo de duración cero produce además un
apagado duro justo en la costura del loop, que coincide con el colapso del vaso
descrito en C2.

**Arreglo:** usar `(i+0.999)/n` en vez de `(i+1)/n` para el penúltimo keyTime.

### B5 — Las tres capas se superponen sobre las mismas celdas
**Severidad: baja. Categoría: legibilidad.**

Dentro de la máscara `mv` se pintan simultáneamente `sustrato` (0,13),
`vidrio` (1,0) y, dentro de `ml`, también `liquido` (1,0): el mismo glifo,
tres veces, con antialiasing sumado. Produce un engrosamiento visible del texto
en el interior del blob (comparar el centro de `aud_t17.png` con la periferia).
No es un error, pero es una fuente de contraste que la pieza no declara y que
compite con el mapeo de opacidad de C1.

**Arreglo:** invertir la máscara del sustrato (`mask` con el path en negro) para
que las capas sean disjuntas en vez de aditivas.

---

## Apéndice: chequeos que pasaron

| chequeo | resultado |
|---|---|
| XML bien formado (`xml.etree.ElementTree`) | OK |
| ids definidos / referenciados | 4 / 4, sin colgar |
| ids duplicados | ninguno |
| ids sin usar | ninguno |
| `url(#…)` resueltos | 4/4 |
| `<animate>` `values` con nº de comandos homogéneo | 129 en los 13 estados de ambas máscaras |
| `keySplines` vs intervalos | 12 vs 12, correcto |
| `glifos()` vs `len(cam)` para el desfase | coinciden |
| labels de nodo truncados por `[:an]` | 0 de 78 |
| trazas sin ruta | 0 de 59 |
| delays negativos | 3.158 de 3.158, todos con `animation-fill-mode` por defecto y `infinite`: comportamiento correcto y bien definido (adelantan la fase, no saltan) |
