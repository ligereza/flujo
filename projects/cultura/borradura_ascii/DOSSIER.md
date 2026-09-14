# Borradura ASCII — la regla que protege al sistema mutila al idioma

Pieza cultural, `projects/cultura/borradura_ascii/`. Protocolo motor-omega
corrido por el director; esta sesión materializa, no re-decide el concepto.

## Concepto

El repo `flujo` tiene una regla operativa: `CLAUDE.md` y `context/*.md`
deben ser ASCII-only. La regla nació como defensa técnica: bugs de
encoding en checkouts Windows. No nació como estilo, y mucho menos como
regla de idioma. El 23-jul-2026 se descubrió aplicada fuera de su alcance:
entregables reales de la ONG (Reduciendo Daño) salieron con "disenio" y
"ano" en vez de "diseño" y "año".

El par **año/ano** es el filo de la pieza: no es solo estética. "Ano" no
es una versión fea de "año" — es *otra palabra*, con otro significado. La
regla que protege al pipeline de un bug de Windows, aplicada sin límite de
alcance, no solo pierde una tilde: puede cambiar lo que una frase dice.

Esta pieza no opina sobre si la regla estuvo bien o mal. **Mide**: cuántas
borraduras reales hay en el corpus operativo del repo hoy, cuáles son
"solo estética" (la palabra sin tilde no es otra palabra, solo la forma
incorrecta) y cuáles son pares mínimos reales (la forma sin tilde ya es,
por sí sola, una palabra distinta del español).

## Evidencia de origen de la regla (git real)

La regla ASCII-only se puede rastrear a la ventana de checkpoints
v0.35.7–v0.35.9, 24-jun-2026, en encabezados de commit que ya nombran el
problema:

- `3b5b372` — "checkpoint: v0.35.7 - purple portal gmail windows handoff"
  (2026-06-24 07:00:04 -0400)
- `ecaa238` — "checkpoint: v0.35.9 - windows checkout issue titles"
  (2026-06-24 07:17:41 -0400), que agrega
  `scripts/cleanup_v0359_windows_paths.py` y toca `context/LAST_HANDOFF.md`
  y `src/flujo/version.py` — el checkpoint donde el problema de encoding en
  checkouts Windows se nombra y se parchea explícitamente.
- `b51d998` — "Fix non-ASCII em dash in LAST_HANDOFF (ASCII-only rule)" —
  primer commit que nombra la regla por su nombre ("ASCII-only rule") en
  el propio mensaje.

Al momento de escribir este dossier, `main` ya tiene un commit posterior
(`c19f926`, "docs: acotar ASCII-only a CLAUDE.md/context, meta-regla,
Omega semilla+expo") que acota explícitamente el alcance de la regla y
cita el incidente real:

> ASCII-only aplica SOLO a `CLAUDE.md` y a `context/*.md` operativos
> (LAST_HANDOFF.md y similares). Fecha: 2026-06-24. Causa: bugs de
> encoding Windows en esos archivos (commits v0.35.7-v0.35.9). Retiro:
> cuando un chequeo automatico de encoding en CI lo vuelva innecesario.
>
> Contraparte obligatoria: TODO entregable (`data/`, `docs/rd/`, informes,
> DB, piezas culturales) va en espanol correcto UTF-8. Mutilar diacriticos
> en un producto es defecto, no estilo (incidente 2026-07-23:
> "disenio"/"ano" colados en la DB para la directiva). ASCII-only NUNCA se
> extiende a entregables.

Ese párrafo ya es, en sí mismo, evidencia primaria del incidente que
motivó esta pieza: cita "disenio"/"ano" entre comillas como el ejemplo
real de la fuga de alcance. En una corrida de `borradura.py` sobre un
commit que ya incluye ese párrafo, el escáner detecta la palabra "ano" ahí
mismo, de forma automática, sin haber sido programado para buscarla —
confirma su propia génesis sin trampa.

## Cómo mide la pieza

1. **`borradura.py`** — lectura pura, determinística. Recorre 11 archivos
   `.md` operativos declarados por la regla (`CLAUDE.md` +
   `context/CAPATAZ.md`, `DIRECTOR_CONTRACT.md`, `DOCTRINA_CLAUDE.md`,
   `LAST_HANDOFF.md`, `MASTER_PLAN.md`, `PLAN_SEMANAL_OPUS.md`,
   `PLAN_SIGUIENTE_AGENTE.md`, `PLAN_UPSCALE.md`, `README.md`,
   `WALKTHROUGH.md`) **en su versión git en HEAD** (`git show
   HEAD:archivo`, nunca el working tree — la corrida es reproducible
   contra un commit fechado, no contra edición en curso; archivos ausentes
   en ese commit -- p.ej. `DIRECTOR_CONTRACT.md` en ramas mas viejas --
   se saltan sin romper la corrida). Compara cada palabra tokenizada
   contra un diccionario mínimo embebido de pares
   `palabra_con_marca -> forma(s)_ascii`. Reporta conteo por archivo y la
   lista completa de pares mínimos reales encontrados (palabra, archivo,
   línea, sha corto).

   El diccionario excluye deliberadamente palabras funcionales de alta
   frecuencia (`el/él`, `si/sí`, `mas/más`, `de/dé`, `se/sé`, `tu/tú`,
   `mi/mí`) — incluirlas produce falsos positivos masivos, porque en la
   inmensa mayoría de sus apariciones la forma sin tilde YA ES la palabra
   correcta (artículo, conjunción, preposición), no una borradura.
   Marcarlas como "cambia significado" habría sido fabricar evidencia, lo
   que la Ω11 (b) prohíbe. **`año/ano` es la única excepción real**: "ano"
   no es una palabra funcional de alta frecuencia, así que su aparición en
   un corpus técnico es señal fuerte de borradura real de "año" — es
   exactamente el par que el director señaló.

2. **`tapiz.py`** — salida ASCII. El texto del corpus sobrevive carácter
   por carácter (es ASCII, por regla). Debajo de cada línea con una
   borradura real, una segunda línea marca con `^` el hueco: la posición
   exacta donde vivía el diacrítico antes de que el plegado lo borrara. El
   propio ASCII que en la base de datos de la ONG fue la HERIDA (el bug de
   ortografía real, "disenio"/"ano") es aquí el MEDIO del tapiz — la
   misma restricción que protege el pipeline es el material con el que se
   construye la pieza que la audita. Esa tensión es la pieza. Salida
   determinística: mismo commit, mismo `tapiz.txt` byte a byte.

3. **`DOSSIER.md`** (este archivo) — UTF-8, español correcto, entregable
   cultural (no `context/`, no gobernado por ASCII-only).

## Resultado real de la corrida (branch `cultura/borradura-ascii`, sha `8c0f6f0`, base `iskvw`)

Comando: `py projects/cultura/borradura_ascii/borradura.py`

```
sha (HEAD): 8c0f6f0
archivos operativos escaneados: 11
borraduras totales encontradas: 209
de las cuales cambian significado (par minimo real): 0
solo perdida de acento (sin par minimo): 209
```

`8c0f6f0` es un commit de `iskvw` anterior a la actualización de
`CLAUDE.md` en `main` (`c19f926`) que acota explícitamente el alcance de
ASCII-only y cita el incidente "disenio"/"ano" — esa actualización
todavía no había llegado a `iskvw` cuando se abrió esta rama. Contra
`c19f926` (verificado en una corrida separada durante el desarrollo de
esta pieza) el escáner sí encuentra el par mínimo real: la palabra "ano"
aparece literal en la línea de `CLAUDE.md` que cita el incidente
("...disenio"/"ano" colados en la DB para la directiva..."), y ese
resultado (1 par que cambia significado, 220 solo-acento, 221 total) es
la evidencia primaria de génesis descrita arriba.

Top palabras "solo acento" más frecuentes (consistente entre ambos
commits): `sesion` (sesión), `codigo` (código), `version` (versión),
`publico` (público), `produccion` (producción) — vocabulario operativo
del propio `CLAUDE.md`, no un caso raro.

`tapiz.txt` (en este mismo directorio) es la salida completa, regenerable
con `py projects/cultura/borradura_ascii/tapiz.py`. `reporte.txt` es la
salida completa de `borradura.py` para el sha citado arriba.

## Ω11 (declarada por el director antes de producir)

> Esta pieza pierde si (a) algún conteo no es determinístico/reproducible
> sobre el corpus fechado; (b) inventa ejemplos — todo par mínimo debe
> existir literal en archivos del repo con su sha; (c) la pieza
> escribe/altera los archivos operativos que mide (debe ser lectura pura).

**Resultado: la Ω11 no se cumplió** — verificado con
`tests/test_borradura_ascii.py` (7 tests, corrida real contra el repo):

- (a) no se activó: dos corridas sobre el mismo sha producen el reporte
  byte-idéntico (`test_determinismo_dos_corridas`).
- (b) no se activó: cada par mínimo listado se verifica con `git show
  <sha>:<archivo>` y la palabra aparece literal en la línea reportada
  (`test_pares_verificables_contra_git_show`, muestra 3 hallazgos reales).
- (c) no se activó: `test_no_escribe_fuera_de_su_salida` corre
  `escanear_corpus` y `render_tapiz` y confirma que ningún archivo del
  corpus operativo cambió de contenido en disco (hash antes/después
  idéntico) — la pieza solo lee vía `git show`.

## Vínculo con ⊕₃/⊕₅ y el material MAK

Esta pieza es la misma familia de instrumento que `tilde_residuo.py`
(⊕₃/⊕₅, `puente/SEMILLAS.md` 12-jul-2026): el residuo que no cruza el
plegado a ASCII, nombrado con precisión, sin decorar y sin computar su
costo de significado como número. `tilde_residuo.py` mide el residuo
carácter por carácter, en cualquier texto que se le pase; `borradura.py`
lo mide palabra por palabra, sobre el corpus operativo real y fechado del
repo — es la aplicación forense de la misma idea, no un instrumento
nuevo desde cero.

El research MAK sobre el diccionario español de ~55k entradas y señal de
tilde (mencionado en la síntesis ejecutiva de investigación, docs(rd) PR
#162) es material de contexto para esta pieza — confirma que el problema
de pares mínimos con/sin diacrítico en español es sistemático, no
anecdótico — pero `borradura.py` NO depende de MAK para correr: su
diccionario es embebido y mínimo, curado a mano, y la pieza corre standalone
con solo `git` y la librería estándar de Python.
