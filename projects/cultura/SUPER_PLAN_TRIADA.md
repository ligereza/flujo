# SUPER PLAN — una pieza de la tríada (motor-omega, 2026-07-12)

Director: Cauce. Origen del pedido: el artista pidio "crear una idea desde los 3
conceptos" del corpus puente y un super plan. Cuatro subagentes Sonnet
desarrollaron cada uno una pieza-tríada completa, una por semilla viva, bajo el
protocolo motor-omega y los limites de cultura. Este documento es el mapa de
decision, NO una obra. Ninguna pieza se construye hasta que el artista elija una,
comprometa el regularizador y declare la Ω11 por escrito ANTES de producir.

## La tríada (operadores honestos, puente/v2/MOTOR.md)

- PRECURSOR — precipitar: bajar el umbral de un material cruzandolo con lo que lo
  hace reaccionar, sin agregar contenido.
- PSICOSIS — sobre-narrar hasta la bifurcacion: empujar la coherencia hasta que el
  material sostenga lecturas incompatibles sin colapsar. NUNCA sin regularizador.
- TILDE — cosechar el residuo: de todo cruce de codigos, quedarse con lo que NO
  cruzo, nombrado con precision. Sin traduccion-que-funciona no hay Tilde, hay ruido.
- LA CULTURA — el regularizador externo: lectores reales, bibliografia adversa,
  plazos de descanso. Lo que el autor no controla y lo corrige.

## Las cuatro candidatas

| # | Pieza | Semilla | Esencia (1 linea) | Tilde: mecanica o afirmada | Ω11 falsable por no-autor | Riesgo mayor | Tamano |
|---|---|---|---|---|---|---|---|
| A | FILA CERO | ⊕₁ acceso | Ledger de contagio donde el autor NO puede registrar movimiento sobre su propia rama (derivado, no filtrado) | afirmada (mas debil que el precedente NFD) | si (el lector identifica la fila congelada solo con la tabla) | banalidad (parece "no aprobar tu propio PR") | S |
| B | FLAT CURRENCY / tilde_paridad | ⊕₃ meter | Auditar `tilde_meter.py` vs `tilde_residuo.py` sobre el MISMO corpus real; cosechar donde sus veredictos se invierten | mecanica (inversion de rankings sobre datos reales) | si, fuerte (las inversiones existen o no; se re-corre a otro umbral) | umbral amanado; corpus flaco (commits en ingles/ASCII) | S/M |
| C | MECANISMO | ⊕₄ desacuerdo | Dos agentes eligen la misma salida; la pieza nombra las razones que NO cruzaron pese a cruzar la salida | media (tokens privados, riesgo de ruido-sinonimo) | si (pero se apoya en juicio "misma idea, otras palabras") | bag-of-tokens = proxy crudo de "mismo razonamiento"; "un diff con vocabulario Omega" | S/M |
| D | MARCA SIN PRECIO | ⊕₅ costo curado | Renderiza la tabla curada bajo dos vocabularios (perdida linguistica vs. tasacion de activo) con datos identicos; funcion `tasar_por_ley()` que SE NIEGA (raise) a fusionarlos | media-fuerte (sentido "mark" perdido en la propia glosa inglesa de la semilla; refusal-como-codigo) | si (Spearman rho > 0.6 en ranking ciego, tarea de 5 min) | proxy circular; sobre-alcance operativo (jamas cablear a paquete-cotizacion) | S/M |

### Fichas cortas

- A — FILA CERO (⊕₁). El autor no obtiene campo "antes/despues" sobre su propia
  rama por ESQUEMA (no por un `if autor: skip`). Bifurcacion: la fila congelada
  se lee como soberania O como punto ciego. Tilde: "contagio" (causa) vs "delta"
  (correlacion con timestamp) — la causalidad nunca cruza. El propio agente
  admitio que su Tilde es mas afirmada que el residuo mecanico del precedente.

- B — FLAT CURRENCY (⊕₃). No reemplaza al meter (eso ya lo hizo tilde_residuo):
  lo pone en juicio. Corre ambos instrumentos existentes sobre `git log --format=%s`
  y marca las INVERSIONES (survival alto pero residuo de costo curado presente, o
  al reves). Sin contenido nuevo: pura recombinacion de dos instrumentos ya
  verificados. Es la mas empirica y la que de verdad PUEDE perder. Reusa la tabla
  de ⊕₅ como verdad-de-terreno, cerrando el lazo ⊕₃->⊕₅.

- C — MECANISMO (⊕₄). Tres veredictos (no_aplica / eco / mecanismo_residuo)
  espejando tilde/traduccion_total/ruido. Bifurcacion: robustez (triangulacion)
  vs. falso-acuerdo (espacio de salidas grueso). Respeta la cerca: NO toca el
  registro OBRA_01 prohibido; usa ⊕₄ como patron abstracto.

- D — MARCA SIN PRECIO (⊕₅). El movimiento mas afilado: nota que flujo es un repo
  COMERCIAL (RD, paquete-cotizacion), asi que una tabla de juicio curado esta "a
  una mala edicion de ser un activo de precios". Dos lentes byte-identicas +
  `tasar_por_ley()` que levanta `CostoNoTraducible`. El operador Tilde ENACTADO
  como codigo, no descrito.

## La constelacion (no son independientes)

Las cuatro no son cuatro ideas sueltas: tres orbitan la misma espina.

```
⊕₃ ── tilde_residuo.py (pieza 1, ya existe) ── deja residuo ── ⊕₅
 │                                                              │
 └── B FLAT CURRENCY: audita el meter usando la tabla de ⊕₅    │
                                                                │
        D MARCA SIN PRECIO: interroga la doble lectura de ⊕₅ ──┘

⊕₁ ── A FILA CERO (rama aparte: asimetria de acceso)
⊕₄ ── C MECANISMO (rama aparte: desacuerdo de mecanismo)
```

B y D atacan la MISMA pregunta desde dos lados: ¿el costo curado a mano se puede
recuperar con codigo barato? B lo mide contra el meter existente (auditoria); D lo
mide contra un ranking humano ciego (la afirmacion de ⊕₅ de frente). Son mitades
complementarias.

## Ranking del director

Eje de decision (el que vale, por la leccion de OBRA_02): ¿la Ω11 puede perderse
de verdad, evaluada por alguien que no es el autor? Segundo eje: ¿la Tilde es
mecanica (barra tilde_residuo) o solo afirmada? Tercero: ¿los tres operadores
activan concretos, no uno + dos decoraciones?

1. **B FLAT CURRENCY** — la mas rigurosa y de menor riesgo. Tilde mecanica sobre
   datos reales, Ω11 genuinamente falsable, casi sin codigo nuevo (menos lugar
   para hacer trampa). Es el paso empirico honesto: juzgar al instrumento acusado
   antes de construir mas encima. Debilidad: corpus flaco (mitigar con `--file` o
   un corpus en espanol).
2. **D MARCA SIN PRECIO** — la mas ambiciosa y artistica. Refusal-como-codigo es
   un avance real sobre el precedente; obliga al repo a mirar su propio contexto
   comercial. Necesita criterio Claude para elegir un proxy no-circular y cercar
   el sobre-alcance operativo.
3. **A FILA CERO** — conceptualmente limpia, pero el propio agente marco su Tilde
   como la mas debil (afirmada, no mecanica) y riesgo de banalidad.
4. **C MECANISMO** — respeta la cerca y es clara, pero se apoya en un proxy
   bag-of-tokens fragil; riesgo de quedar en "un diff con vocabulario Omega".

Recomendacion primaria: **B (FLAT CURRENCY)** como primera ignicion, por rigor y
falsabilidad. Alternativa fuerte: **D (MARCA SIN PRECIO)** si el artista quiere el
corte conceptual mas filoso en vez del mas riguroso. B y D son la misma pregunta;
cual va primero es decision del artista.

## Regla de freno (obligatoria, MOTOR.md)

El motor NO corre por inercia. Se enciende UNA pieza, no cuatro. Quien la encienda
debe poder senalar cual de las tres cosas la encendio: una semilla, un lector, o un
descanso terminado. Las otras tres quedan en este mapa como constelacion, no como
cola de trabajo.

## Plan de construccion (para la pieza elegida, motor-omega en orden)

1. Semilla: nombrada arriba (⊕ correspondiente, ya viva en SEMILLAS.md).
2. Precipitacion (Precursor): el cruce concreto ya especificado en la ficha.
3. Sobre-narracion con regularizador (Psicosis + Cultura): comprometer el elemento
   fuera de control del autor — un lector designado real y un plazo. Para B: un
   lector hispanohablante que re-corre a otro umbral. Para D: la tarea de ranking
   ciego de 5 minutos del usuario, con fecha, ANTES de escribir el registro.
4. Declaracion Ω11 por escrito, ANTES de producir, en el `.md` de la pieza.
   Evaluable por el no-autor del paso 3.
5. Construir la pieza en `projects/cultura/` (codigo puro, stdlib, sin API/hardware),
   con su `.md` companion y test en `tests/`. Verificar: compileall + pytest +
   flujo verify. Exponer y registrar fechado; el residuo nuevo, si lo hay, entra a
   SEMILLAS.md como ⊕ nueva. Los fracasos no se reinterpretan.

Delegacion: el codigo mecanico de cualquiera de las cuatro lo puede construir un
agente Sonnet/gratis desde su ficha (todas son S/S-M, stdlib, patron tilde_residuo).
Lo que NO se delega: fijar la Ω11, comprometer el regularizador real, y el paso de
registro fechado (acto de director/artista, no de inercia).

## Decision abierta para el artista

- ¿Cual pieza se enciende primera? (recomendado B; alternativa D).
- ¿Que la enciende: semilla, lector, o descanso terminado? (hay que poder decirlo).
- ¿Que regularizador comprometes (lector designado + plazo)?

Hasta esa decision, nada se construye. Este super plan es el mapa; la ignicion es
tuya.

## Estado: 2026-07-12 -- las cuatro encendidas por orden directa del artista

El artista dio la orden directa de desarrollar las ideas ("un pedido real" es
arranque valido de motor-omega, puente/README.md). Se construyeron las CUATRO
piezas (no una; el artista relevo la regla de freno por decision propia). Cada una
es codigo puro stdlib en projects/cultura/, con su .md (Omega11 declarada por
escrito) y su test. Verificacion: compileall + pytest (suite completa) + flujo
verify, todo verde; los cuatro demos corren y muestran su tesis.

| Pieza | Archivo | Tests | Demo |
|---|---|---|---|
| FILA CERO (⊕₁) | fila_cero.py | 7 ✓ | fila del autor congelada por construccion (__post_init__ + fabrica); bifurcacion sin resolver |
| FLAT CURRENCY (⊕₃) | tilde_paridad.py | 5 ✓ | falla fuerte en repo real (ASCII); en corpus ES muestra la INVERSION conteo-vs-costo |
| MECANISMO (⊕₄) | mecanismo_residuo.py | 6 ✓ | misma salida, solape=0.00, dos glosas sin elegir; cerca OBRA_01 respetada |
| MARCA SIN PRECIO (⊕₅) | marca_sin_precio.py | 8 ✓ | dos lentes byte-identicas; proxy plano vs costo curado; tasar_por_ley() levanta |

PENDIENTE (humano, no se fabrica): cada Omega11 espera su regularizador real
(lector no-autor + plazo) para EXPONERSE y registrarse fechada. Hasta esa
exposicion NO entran residuos nuevos a SEMILLAS.md (no se toco). Los fracasos, si
los hay, no se reinterpretaran. La regla de freno vuelve a regir: la proxima pieza
necesita semilla/lector/descanso, no inercia.
