# Corpus del olvido -- dossier

Pieza generada con el protocolo `motor-omega` el 18-jul-2026 (pieza MANIFIESTO
#9 del `puente/MANIFIESTO.md`). Director: Cauce/Fable.

## Semilla

**MANIFIESTO #9** (`puente/MANIFIESTO.md`, linea 19): "El corpus esta escrito
para lectores que olvidan... El genero real del proyecto no es el ensayo ni
la obra: es el *handoff* -- texto disenado para cruzar la brecha entre dos
que no comparten presente. Ya lo estas haciendo; solo falta llamarlo obra."

Cruce con material existente: el historial git de `context/LAST_HANDOFF.md`.
Ese archivo se reescribe cada sesion -- no se versiona a mano, se pisa. Cada
commit es una capa donde una sesion declaro su presente sabiendo (por regla
de `CLAUDE.md`, "Continuidad entre sesiones") que la siguiente no lo iba a
recordar y solo iba a leer el archivo. Ese cruce es literal, no metaforico:
el genero que MANIFIESTO #9 nombra ya estaba siendo producido, en produccion
continua, desde antes de que hubiera pieza.

## Omega11 (declarada ANTES de producir)

"Esta pieza pierde si (a) el corpus inventa o edita contenido de sesiones --
todo fragmento debe ser extraccion literal del historial git, verificable
contra su sha; (b) un lector no puede rastrear cada fragmento a su sesion de
origen (sha corto + fecha visibles junto a cada fragmento); (c) la salida no
es determinista dado el mismo historial."

## Precipitacion (el cruce de codigo)

El plegado es `git log --follow` + `git show <sha>:archivo` sobre
`context/LAST_HANDOFF.md`: una traduccion de "todo lo que paso en esa sesion"
a "lo que quedo escrito en el header antes del primer `## `". Es una
traduccion que MAYORMENTE funciona -- el header sobrevive intacto -- por eso
el residuo (todo lo demas de la sesion: el trabajo, la duda, el proceso) se
ve por ausencia. `corpus_olvido.py` no edita ni normaliza el texto extraido
mas alla de trim de whitespace en los bordes: no resume, no traduce, no
corrige errores de tipeo de sesiones pasadas. Extrae.

Variantes que se consideraron y no colapsaron en la primera obvia: (1) todo
el archivo por commit (descartada -- demasiado ruido, el header es la parte
que la sesion misma senalo como "esto es lo que importa ahora"); (2) solo el
diff entre versiones consecutivas (descartada -- un diff no es un presente
declarado, es una comparacion retrospectiva que ninguna sesion hizo en su
momento); (3) el header completo, tal como qued/o escrito, ordenado
cronologico (la elegida -- es lo mas cercano a "lo que esa sesion creyo que
bastaba para que la siguiente supiera donde estaba parada").

## Sobre-narracion (mas de una lectura defendible, sin resolver en una sola)

1. **Archivo.** Es un instrumento de trazabilidad operativa: 104 capas de
   estado real, cada una con su sha y su fecha, consultable como bitacora de
   ingenieria. Sirve para auditar cuando cambio la version, que se declaro
   "listo" y cuando, sin re-leer 104 commits a mano.

2. **Memoria.** Es la unica memoria del sistema entre sesiones -- no hay
   memoria de modelo, hay archivo. Leido entero, el corpus muestra que la
   memoria de flujo no es continua: es una cadena de reescrituras donde cada
   eslabon confia en el anterior sin haberlo vivido. Eso es literalmente como
   funciona la continuidad de este proyecto, no una analogia.

3. **Performance del olvido.** Leido de corrido, el corpus repite casi la
   misma estructura 104 veces ("Date:", "Current version:", "done/doing/next")
   con variaciones minimas -- la forma de alguien que se despierta sin
   memoria y reconstruye el mismo ritual cada vez para orientarse. La
   redundancia no es defecto del extractor: es el sintoma. El genero
   "handoff" existe PORQUE nadie que lo escribe va a leerlo con la memoria de
   haberlo escrito.

Estas tres lecturas no se resuelven aca. El corpus.md generado no elige
ninguna -- solo pone las 104 capas una despues de otra, en orden, con su sha
y su fecha, para que quien lo lea decida cual de las tres (o cual otra) le
sirve.

## Resultado real

Verificado con `tests/test_corpus_olvido.py` (7 tests, repo git THROWAWAY en
`tmp_path`, nunca toca el historial real) y con una corrida real sobre este
repo el 18-jul-2026:

- `py -m pytest tests/test_corpus_olvido.py -q`: 7 passed.
- `py -m pytest tests/ -q`: suite completa verde (sin regresiones).
- Corrida real: **104 capas** encontradas, desde **2026-06-30T04:36:22-04:00**
  (`bee102e`) hasta **2026-07-18T03:54:23-04:00** (`5a045e2`). Dos corridas
  consecutivas produjeron `corpus.md` byte-identico (determinismo verificado
  a mano, no solo en test).

La Omega11 **no se cumplio**: (a) no se activo -- cada fragmento del
`corpus.md` committeado es la salida literal de `git show <sha>:archivo`,
sin edicion mas alla de trim de whitespace; verificable rehaciendo
`git show <sha>:context/LAST_HANDOFF.md` contra cualquier entrada. (b) no se
activo -- cada entrada del corpus lleva su fecha ISO y su sha corto en el
header de seccion (`### <fecha> <sha>`). (c) no se activo -- dos corridas
sobre el mismo historial produjeron el mismo `corpus.md` byte a byte.

`corpus.md` SE COMMITEA junto con el generador: es determinista dado el
estado actual del historial de `context/LAST_HANDOFF.md`, asi que es una
impresion valida del corpus a esta fecha. Si el historial de ese archivo
crece (nuevas sesiones), correr `py projects/cultura/corpus_olvido/
corpus_olvido.py` de nuevo regenera `corpus.md` con las capas nuevas -- no
hay drift oculto, el archivo committeado es exactamente lo que el script
produce hoy.

## Residuo, sin cruzar

El header de `LAST_HANDOFF.md` cambio de forma varias veces en las 104
capas -- versiones tempranas usan "done/doing/next" en ingles, versiones
mas recientes mezclan espanol y estructura distinta. El corpus no normaliza
eso (seria editar), asi que el genero "handoff" que MANIFIESTO #9 nombra no
es homogeneo: tiene su propia deriva de forma, capa sobre capa, que nadie
diseno a proposito. Si eso es una ⊕ nueva (la forma del handoff tambien
olvida su propia forma anterior) queda anotado aca, sin resolver.
