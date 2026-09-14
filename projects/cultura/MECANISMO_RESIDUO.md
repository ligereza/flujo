# MECANISMO_RESIDUO -- el residuo entre RAZONES, no entre ramas

Pieza generada con el protocolo `motor-omega` el 12-jul-2026 (arranque por pedido
real del artista, valido segun `puente/README.md`).

## Caveat, de entrada (no enterrado al final)
El solape de razones se mide como **bolsa de tokens**. Dos textos independientes casi
siempre difieren en palabras; por eso el residuo que esta pieza nombra PUEDE ser mero
ruido de sinonimia y no una diferencia real de mecanismo. La pieza no resuelve eso: lo
expone y lo somete a un lector no-autor (ver Omega11). Esta franqueza es parte de la
pieza, no una nota al pie.

## Semilla
**(+)4** (`puente/SEMILLAS.md`, 12-jul-2026): "dos [lectores] se inclinaron a la misma
[rama] por razones que no se traducen entre si; el desacuerdo sobre el MECANISMO es el
residuo, no la rama." Se usa SOLO como patron abstracto: misma salida, razones
inconmensurables, sobre un dominio cualquiera de elecciones justificadas. NO reabre ni
referencia el test de bifurcacion de OBRA_01.

## Que hace
`projects/cultura/mecanismo_residuo.py` recibe varios `Veredicto(agente, salida,
razones)` -- agentes que emitieron una eleccion y la justificaron -- y **cosecha el
residuo entre sus RAZONES cuando la SALIDA coincide**. No devuelve un numero.

Es la precipitacion de (+)4 un piso por encima de `tilde_residuo.py`: alla el "fondo de
traduccion que funciona" (Davidson, doc 01) era el texto plegado a ASCII legible; aca el
fondo es la COINCIDENCIA DE SALIDA. Contra ese fondo -- dos agentes que eligieron lo
mismo -- se vuelve visible el residuo: las razones que uno dio y el otro no, pese a haber
cruzado la salida limpio.

Ejemplo (`py projects/cultura/mecanismo_residuo.py`, fixture por defecto):

```
fondo (salida compartida): 'lingering after-meal conversation'
razones que cruzaron: ninguna
residuo de mecanismo (solape=0.00) -- razones que NO cruzaron, por agente:
  traductor_A: conversacion, duracion, formal, mantener, preservar, registro, temporal, termino
  traductor_B: comer, comunitaria, conservar, costumbre, despues, mesa, ritual, social, vinculo
misma salida, mecanismos inconmensurables. El instrumento NO elige entre estas dos lecturas:
  lectura A (robustez): ...
  lectura B (falso acuerdo): ...
```

Tres veredictos:
- `no_aplica`: las salidas no coinciden -> sin fondo, es desacuerdo comun (no el
  fenomeno de (+)4). Analogo del `ruido` de `tilde_residuo.py`.
- `eco`: misma salida y razones que se solapan -> convergieron tambien en el mecanismo,
  no hay residuo. Analogo de `traduccion_total`.
- `mecanismo_residuo`: misma salida pero razones que no se solapan -> el residuo real;
  imprime las dos lecturas incompatibles sin elegir. Analogo de `tilde`.

## Como activa cada operador
- **Precursor (precipitar):** colisiona las razones ya dadas por A contra las de B,
  ambos ya parados en la misma salida. El procedimiento es comparacion de conjuntos de
  tokens normalizados (plegado a ASCII reusado de `tilde_residuo.py` + minusculas +
  quitar vacias). Baja el umbral: dos justificaciones que nadie comparaba se vuelven
  comparables lado a lado. NO agrega contenido -- no inventa, resume ni parafrasea
  ninguna razon; solo interseca y resta lo que ya estaba escrito.
- **Psicosis (sobre-narrar hasta la bifurcacion):** cuando las salidas coinciden pero las
  razones no, la pieza SOSTIENE dos lecturas incompatibles sin colapsar -- robustez
  (triangulacion: la salida sale reforzada por venir de angulos distintos) vs. falso
  acuerdo (subdeterminacion Duhem-Quine: coincidir es barato, los agentes ni comparten el
  concepto de la decision). Las dos son cadenas FIJAS, curadas una vez, impresas verbatim;
  el instrumento NUNCA elige. El regularizador que evita el delirio es el lector no-autor
  de la Omega11.
- **Tilde (cosechar el residuo):** el residuo son los tokens de razon presentes en un
  agente y ausentes en el otro, PESE a que la salida cruzo limpio -- nombrados por agente,
  no como un diff pelado. Davidson operativizado: sin coincidencia de salida no hay fondo
  (no aplica); con salida igual y razones solapadas hay eco (sin residuo); solo con salida
  igual y razones que no cruzan existe el residuo de mecanismo.

## Estatutos (regla de escritura #2 del MOTOR)
- **"precipitar" / "colision de razones"**: PROCEDIMIENTO (comparacion de conjuntos ya
  dados). No es operador matematico.
- **"residuo de mecanismo"**: PROCEDIMIENTO respaldado por doc 01. Se nombra (que tokens,
  de que agente, contra que salida). No se decora.
- **"fondo que funciona"**: la restriccion de Davidson al nivel de la justificacion. Sin
  salida compartida no hay Tilde: no aplica.

## Omega11 (declarada ANTES de exponer)
> Esta pieza pierde si los tokens que nombra como residuo-privado son indistinguibles de
> ruido de sinonimia -- es decir, si un lector no-autor, dados los textos completos de
> razon MAS el residuo cosechado, juzga que los tokens "privados" de cada lado en realidad
> dicen la misma preocupacion con otras palabras, en vez de sustancia de razonamiento
> genuinamente distinta.

Evaluable por un lector que **no sea el autor**. COMO: para cada veredicto
`mecanismo_residuo` producido sobre un caso REAL (no el fixture), el lector marca cada par
de tokens privados como "razonamiento genuinamente distinto" o "misma preocupacion, otras
palabras"; si la mayoria son lo segundo a lo largo de sus casos reales, la pieza pierde.

## Regularizador (Cultura) -- COMPROMETIDO, PENDIENTE
El elemento fuera de control del autor: un lector que haya estado personalmente en los dos
lados de una situacion "mismo veredicto / razones distintas" (una code review, una revision
por pares, una decision editorial o de traduccion tomada por dos personas por separado)
alimenta la pieza con un caso REAL que vivio (anonimizado, roles genericos, nunca un tercero
real nombrado -- psicosis no perfila personas) y juzga la Omega11. Este paso -- conseguir y
juzgar un caso real -- NO puede hacerlo el autor ni un agente de codigo.

**Resultado: PENDIENTE.** Aun sin lector. No se fabrica veredicto. El fixture por defecto es
solo ilustrativo y NO cuenta como caso real para la Omega11.

## Riesgos (adversarial contra la propia pieza)
- **Bolsa de tokens vs. sinonimia:** el riesgo #1, el que la Omega11 existe para atrapar.
  Dos textos difieren en palabras casi por defecto; la pieza podria fabricar residuo espurio
  a partir de pura parafrasis.
- **Umbral 0.5 arbitrario** (heredado de `tilde_residuo.py`): moverlo cambia el veredicto.
  Esa fragilidad es parte de lo que la pieza expone, no un defecto oculto.
- **Las dos glosas pueden degradarse a disclaimer decorativo** si se imprimen sin un caso
  real detras; por eso el regularizador (lector + caso real) es lo que TERMINA la pieza, no
  un adorno. Sin ese lector la pieza esta inconclusa, no solo sin evaluar.
- **Puede colapsar a "un diff con vocabulario Omega encima";** lo que la salva (si la salva)
  es nombrar el residuo por agente y contra la salida compartida, no como set-difference pelado.

## Uso
```bash
py projects/cultura/mecanismo_residuo.py
py -m pytest tests/test_mecanismo_residuo.py -q
```
