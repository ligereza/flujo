# FILA_CERO -- el que escribio no puede ser contagiado por lo que escribio

Pieza generada con el protocolo `motor-omega` el 12-jul-2026. Arranque: pedido
real del artista (orden directa, 12-jul-2026), valido como inicio segun
`puente/README.md`.

## Semilla
**(+)1** (`puente/SEMILLAS.md`, 11-jul-2026): "asimetria de acceso: quien puede
ser contagiado por cual rama; el que escribio no puede ser contagiado por lo que
escribio." Origen: `puente/v1/OBRA_01_bifurcacion_psicosis.md`.

OBRA_01 AFIRMA esa inmunidad en prosa; su Omega11 solo mide el contagio del
LECTOR, nunca demuestra la inmunidad del autor. (+)1 no es contenido que se pueda
agregar: nombra un mecanismo que falta. Esta pieza lo vuelve computable.

## Que hace
`projects/cultura/fila_cero.py` es un libro mayor de contagio: ramas (material que
alguien escribio y firmo) y lecturas registradas contra ellas. Cada lectura tiene
un 'antes' y un 'despues' de postura. La regla que es el motor:

- Un **lector ajeno** aporta su propio 'antes'/'despues' (texto libre, sobre su
  propia postura -- nunca inferido, nunca sobre un tercero).
- El **autor sobre su propia rama** NO recibe un campo 'antes' libre. Su 'antes' y
  su 'despues' se DERIVAN como la postura de la rama, y construir una auto-lectura
  del autor con antes != despues es imposible: levanta `ValueError`. Eso es la
  **Fila Cero**: congelada por construccion, no filtrada despues.

La diferencia con un permiso ("no podes editar tu fila") es el punto entero: no es
que el autor tenga prohibido cambiar su fila, es que el dato no existe -- el modelo
no le da un 'antes' que mover. La inmunidad de (+)1 es estructural, no una regla de
acceso.

Ejemplo (`py projects/cultura/fila_cero.py`):

```
RAMA    LECTOR          ANTES     DESPUES   DELTA
------  --------------  --------  --------  -----
rama_A  autor_01        Paranoia  Paranoia  no
rama_B  autor_01        Duda      Duda      no
rama_A  lector_gamma    neutral   Paranoia  si
rama_B  lector_delta    neutral   Duda      si
rama_B  lector_epsilon  Duda      Duda      no
```

Seguido de la bifurcacion sin resolver (soberania vs punto ciego) y, por cada
delta, la nota Tilde "delta registrado, causa NO verificada".

## Como activa cada operador

### Precursor (precipitar)
Colisiona el material literario de OBRA_01 (ramas, "quien se contagia de cual")
con un codigo ajeno y no-narrativo: el esquema de un libro mayor de contacto /
bitacora de blame (quien toco que, cuando, que cambio). No se agrega narrativa
nueva -- ni Rama C, ni prosa. Lo que baja de umbral es la VISIBILIDAD de la
asimetria: en prosa (OBRA_01) es una afirmacion que hay que creer; recast como
esquema, la inmunidad del autor es una propiedad del modelo de datos -- su fila no
puede portar un 'antes' libre, por esquema, no por narracion. Mismo movimiento que
`projects/cultura/dossiers/precursor.md` (prestar la FORMA de un documento ajeno, no su contenido
operativo): aca la forma prestada es "bitacora/libro mayor", nunca datos reales de
rastreo de contactos ni epidemiologia.

### Psicosis (sobre-narrar hasta la bifurcacion)
La bifurcacion vive en un solo hecho visual: en la tabla, la Fila Cero del autor
(antes==despues) es indistinguible EN FORMA de la fila de un lector ajeno que
simplemente no cambio de postura (`lector_epsilon`). Dos lecturas incompatibles de
esa misma forma, ninguna colapsable en la otra:
- **soberania**: la fila esta congelada porque el autor tiene autoridad total
  sobre lo que hizo; nada externo lo mueve.
- **punto ciego**: la fila esta congelada porque el propio instrumento le prohibe
  al autor registrar movimiento sobre su obra; es la unica persona a la que el
  libro, por estructura, no escucha.
Soberania se lee como privilegio; punto ciego se lee como exclusion por el mismo
aparato que el autor construyo. Eco formal de Rama A (paranoia: una mano controla
todo) vs Rama B (duda: no puedo verificar desde adentro) de OBRA_01, sin repetir
una linea de ese texto. El regularizador (abajo) es lo que impide que la
sobre-narracion derive en delirio.

### Tilde (cosechar el residuo)
El residuo esta entre la palabra **"contagio"** (lo que usan (+)1 y OBRA_01: una
afirmacion afectiva y causal -- esta rama me MOVIO) y **"delta"** (lo unico que el
libro puede registrar: antes != despues, una diferencia con fecha y sin garantia
causal). Lo que NO cruza: la atribucion de causa. El libro puede probar, con
certeza, que el delta del autor es siempre cero (eso es estructural, derivable del
esquema). Nunca puede probar que el delta no-cero de un ajeno fue CAUSADO por la
rama y no por animo, cansancio o un evento no relacionado entre las dos posturas.
Nombrado con precision: el hueco no es "delta es impreciso" -- delta es exacto. El
hueco es que "contagio" reclama causa y "delta" solo aporta correlacion-con-fecha,
y ningun codigo mejor cierra eso. Ese es el residuo, y la pieza lo dice en su
salida ("causa NO verificada"), no solo en los comentarios.

**Honestidad sobre esta Tilde**: es mas ASERTADA que la de `tilde_residuo.py`.
Alla el residuo es una marca Unicode combinante literal, destruida por un plegado
real y mecanico (normalizacion NFD deja caer la virgulilla -- se puede demostrar).
Aca el residuo (contagio vs delta) es un hueco conceptual afirmado en la salida de
texto, no algo que el codigo DEMUESTRE dejar caer como NFD demuestra dejar caer un
diacritico. Esta Tilde es mas debil y mas basada en afirmacion que el precedente.
Se declara asi a proposito: un revisor puede legitimamente decir "no es una Tilde
real, es solo una advertencia" si el aviso impreso no aterriza como algo
genuinamente irreducible. Esa puerta queda abierta.

## La pieza concreta
- `projects/cultura/fila_cero.py`: stdlib pura (dataclasses), sin red/API/hardware,
  sin sintesis generativa. `Rama`, `Lectura` (con `Lectura.registrar` como unico
  punto donde vive la regla asimetrica), `LibroMayor`, `render`, `_demo`, y un
  `__main__` corrible con `py projects/cultura/fila_cero.py`.
- `tests/test_fila_cero.py`: espeja `tests/test_tilde_residuo.py`.

LIMITE DURO (psicosis): la pieza solo guarda etiquetas de texto libre que el lector
elige sobre SU PROPIA postura -- nunca inferidas, nunca diagnosticas, nunca sobre un
tercero real. No perfila a nadie. Si una iteracion futura tienta a que un usuario
registre una lectura SOBRE la inclinacion de otra persona real y nombrada, cruza el
limite ahi mismo y se rechaza -- no se redisena alrededor.

## Omega11 (declarada ANTES de exponer)
> Esta pieza pierde si el lector no-autor designado, mostrado SOLO la tabla
> renderizada (sin codigo, sin comentarios), NO puede identificar la fila congelada
> del autor -- o la identifica pero la atribuye a la razon equivocada (p.ej. la
> llama "un lector que simplemente no cambio de opinion" en vez de reconocer que
> hay algo estructuralmente distinto en esa fila).

Si un humano no puede distinguir el cero estructural (Fila Cero) del cero
contingente (un ajeno que no se movio) mirando SOLO la salida, entonces la
asimetria que la pieza dice hacer visible no es visible -- esta afirmada en el
codigo, no demostrada en lo que el lector ve. Eso significaria que la pieza decora
la semilla en vez de activarla.

**Quien evalua y como**: el lector no-autor designado por el regularizador (abajo),
juzgando PURAMENTE desde la tabla impresa, sin acceso al codigo -- asi que un
humano incluso sin Python puede evaluarla. Pregunta unica, por escrito: "Mirando
solo esta tabla, cual fila (si alguna) pertenece a alguien que nunca podria mostrar
un cambio aca, y por que lo pensas?"

## Regularizador (Cultura) -- COMPROMETIDO, PENDIENTE
Elemento fuera de control del autor, ya comprometido: correr la SALIDA renderizada
(no esta proposal, no el codigo fuente, no los comentarios) frente a un lector que
no la escribio -- el usuario, o una sesion de agente de contexto fresco sin memoria
de este hilo -- con la pregunta unica de arriba. La respuesta se registra, fechada,
apendice sin editar (regla #4 del MOTOR: lo fechado no se reinterpreta).

**Estado: PENDIENTE.** El resultado de la Omega11 NO esta evaluado todavia: falta
la lectura humana no-autor. No se fabrica un resultado aca. Cuando llegue, se
apendicea abajo con fecha, sin reinterpretar -- exito o fracaso.

## Resultado (12-jul-2026)
PENDIENTE de la lectura no-autor (ver regularizador). La Omega11 queda declarada y
sin evaluar; generar una conclusion desde el autor violaria el protocolo (una
Omega11 solo evaluable desde adentro deja la obra en suspenso -- leccion de
OBRA_02). El motor queda a la espera del lector.

## Uso
```bash
py projects/cultura/fila_cero.py
py -m pytest tests/test_fila_cero.py -q
```
