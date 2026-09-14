# TILDE_RESIDUO -- la Tilde cosechada, no contada

Pieza generada con el protocolo `motor-omega` el 12-jul-2026.

## Semilla
**(+)3** (`puente/SEMILLAS.md`, 12-jul-2026): "tilde_meter mide tokens = dialecto
Omega degradado. La Tilde NO es ahorro de tokens, es residuo intraducible."
Origen: `desktop/tilde_meter.py`.

## Que hace
`projects/cultura/tilde_residuo.py` cruza un texto espanol a ASCII -- una
traduccion que mayormente funciona -- y **cosecha lo que no cruzo**: cada
diacritico y apertura que el plegado destruye, nombrado por su identidad Unicode
y con su costo de significado. No devuelve un numero.

La diferencia con `desktop/tilde_meter.py` es el punto entero de (+)3: aquel
cuenta tokens (el dialecto degradado); este nombra el residuo (la Tilde como la
define el doc 01, con la restriccion de Davidson: el residuo solo se ve contra un
fondo de traduccion que funciona).

Ejemplo (`py projects/cultura/tilde_residuo.py "año"`):

```
fondo (traduccion que funciona): 'ano'
residuo intraducible (1 marca(s)):
  @1 'ñ' -> 'n' | COMBINING TILDE | 'año' (year) -> 'ano' (anus); la marca ES la virgulilla homonima de esta pieza
```

Tres veredictos: `tilde` (fondo legible + residuo), `traduccion_total` (fondo
legible, nada se perdio) y `ruido` (sin fondo legible -- nada cruzo, no es Tilde).

## Estatutos (regla de escritura #2 del MOTOR)
- **"plegado a ASCII"**: PROCEDIMIENTO (NFD + descartar marcas combinantes + borrar
  aperturas invertidas). No es operador matematico.
- **"residuo"**: PROCEDIMIENTO respaldado por doc 01. Se nombra (que, entre que y
  que, su costo), no se decora.
- **"fondo legible"**: la restriccion de Davidson operativizada. Sin fondo que
  funcione no hay Tilde: hay ruido, y el instrumento lo dice en vez de inventar.

## Omega11 (declarada ANTES de producir)
> Esta pieza pierde si el residuo que reporta es indistinguible de un `diff` de
> caracteres cualquiera -- es decir, si NO nombra ningun residuo cuyo costo de
> significado un hispanohablante reconozca como perdida real (p.ej. año/ano).

Evaluable por cualquier lector hispanohablante, no por el autor.

## Resultado (12-jul-2026)
La Omega11 **no se cumplio**: la pieza nombra año/ano, papá/papa, aún/aun,
pingüino -- perdidas que un hispanohablante reconoce como reales. La pieza no
perdio por su condicion declarada. Un lector humano puede refutar este juicio:
esa puerta queda abierta a proposito (el veredicto final del costo no es del
autor; ver residuo nuevo).

Correr la pieza destapo dos cosas fechadas, sin reinterpretar:
1. Un bug real: la entrada llegaba a veces descompuesta (NFD) y la 'ñ' se
   cosechaba como marca suelta. Se corrigio normalizando a NFC primero; la
   cosecha ya no depende de como se tipeo la entrada.
2. Un residuo del propio instrumento -> **(+)5** (registrado en `SEMILLAS.md`):
   la pieza nombra QUE se perdio con precision Unicode, pero el COSTO de
   significado sigue curado a mano. Ese juicio -- cuanto duele año/ano -- no
   cruza a codigo. Lo intraducible se corrio un piso: de la marca al valor de la
   marca.

## Uso
```bash
py projects/cultura/tilde_residuo.py "El año pasado, ¿aún hablás español?"
py -m pytest tests/test_tilde_residuo.py -q
```
