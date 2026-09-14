# MARCA SIN PRECIO -- el juicio curado y su proxy, lado a lado, sin fusion

Pieza generada con el protocolo `motor-omega` el 12-jul-2026.
Arranque valido: pedido real del artista (orden directa, 12-jul-2026; ver
`puente/README.md`, "un pedido real" enciende el motor).

## Semilla
**(+)5** (`puente/SEMILLAS.md`, 12-jul-2026): "el costo de significado del residuo NO
cruza a codigo: se cura a mano (tabla curada); lo intraducible se corrio de la marca al
VALOR de la marca."
Origen: `projects/cultura/tilde_residuo.py` (precipitacion de (+)3). (+)5 no es una idea:
es el residuo que cayo al construir aquella pieza -- nombro QUE se perdio con precision
Unicode, pero el COSTO (cuanto duele `ano` (year) -> `ano` (anus)) quedo en
`_COSTO_POR_CHAR`, una tabla que el programa importa pero no puede generar.

## Que hace
`projects/cultura/marca_sin_precio.py` **importa** (no re-escribe) la tabla curada
`_COSTO_POR_CHAR` desde `tilde_residuo`, le calcula al lado un **proxy mecanico** y
muestra ambas columnas bajo dos lentes de vocabulario intercambiado -- sin fundirlas
nunca. La negativa a fundirlas es una funcion que levanta una excepcion: el limite es
codigo, no comentario.

Ejemplo (`py projects/cultura/marca_sin_precio.py --lente marca`):

```
=== el valor de la marca y su tasacion -- lente marca ===
columnas: activo | marca base (plegada) | valor curado (a mano) | tasacion mecanica (distancia de codepoint (formal, no dinero))
  'ñ' -> 'n' | 'ano' (year) -> 'ano' (anus); la marca ES la virgulilla homonima de esta pieza | 131
  ...
-- intento de tasacion por regla (tasar_por_ley) --
  CostoNoTraducible: el costo curado de 'ñ' (...) no se funde con su proxy mecanico (131): ... NO_CRUZA.
```

El mismo comando con `--lente linguistico` imprime **las mismas lineas de datos**; solo
cambian titulo, encabezados de columna y la nota. Un self-check interno aborta si los
lentes divergieran en los datos (seria agregar contenido al reencuadrar).

## Como activa cada operador

- **Precursor (precipitar).** Colisiona el espanol "marca" (sentido vivo doble:
  *mark/diacritico* Y *brand/marca comercial*) contra su propia glosa inglesa. La
  transmision inglesa de (+)5 en el prompt de esta tarea tradujo "marca" como *brand* y
  dejo caer el sentido *mark*. No se agrega contenido: la lista de colision son dos
  traducciones que YA existen en el repo, fechadas 12-jul-2026 (`marca -> mark` usada en
  todo `tilde_residuo.py`; `marca -> brand` usada en la glosa de la semilla). El umbral
  que baja: hace visible, sin argumento, que "curar el costo de un residuo" y "tasar el
  valor de una marca" tienen la misma forma verbal (asignar valor a un marcador de
  identidad). En un repo que ademas hace trabajo comercial de diseno, esa forma no es
  hipotetica.
- **Psicosis (sobre-narrar hasta la bifurcacion).** La pieza sostiene dos lecturas
  incompatibles de los MISMOS datos (la tabla, importada sin tocar): (A) lectura de
  cuidado linguistico -- la tabla es un acto privado y singular de juicio de un
  hispanohablante, no mercantilizable; (B) lectura de ficha-de-activo -- la misma tabla,
  bajo vocabulario de tasacion, es estructuralmente indistinguible de una hoja de valor
  que un flujo comercial podria extraer. La bifurcacion se para sobre la tabla misma: los
  dos lentes emiten valores identicos byte a byte; el codigo NO decide cual lectura es la
  correcta. El regularizador (Cultura) evita el delirio: hay un lector real comprometido
  (abajo).
- **Tilde (cosechar el residuo).** El residuo cosechado es exacto: entre "marca"
  (mark+brand, doble sentido vivo) y la glosa inglesa de esta semilla ("brand", solo
  brand), **lo que NO cruzo es el sentido "diacritico/mark"**, perdido en la misma frase
  que asigna esta tarea. Nombrado con precision: no es un residuo que la pieza produce; es
  un residuo que YA ocurrio, fechado 12-jul-2026, en el paso de `SEMILLAS.md` (+)5 a la
  parafrasis inglesa del prompt. La pieza solo lo nota y se niega a alisarlo.

## Por que el proxy es ORTOGONAL (no un test amanado)
El criterio de curaduria de `_COSTO_POR_CHAR` es semantico: perder esta marca, produce un
par minimo real donde el sentido cambia o se invierte? (ano/ano, papa/papa, aun/aun). El
**proxy mecanico** es `proxy_mecanico()`: la distancia de codepoint entre el caracter y su
forma plegada (`plegar()`). Es una propiedad formal de Unicode -- no sabe, no puede saber,
si el plegado produce un par minimo. Se eligio a proposito ORTOGONAL al criterio de
curaduria: si en cambio se derivara del mismo criterio semantico, la (+)5 quedaria
refutada por construccion en un sentido y confirmada en otro -- amanada. Ademas el proxy
resulta casi plano (todos los acentos caen ~128-135) mientras el costo humano varia
brutalmente (ano/ano catastrofico; hablo/hablo leve): esa planicie ES el argumento -- el
proxy formal no puede rankear el dolor.

## Limite duro (operational-overreach = violacion)
El lente "marca" es SOLO vocabulario (activo / valor curado / tasacion mecanica). El proxy
se rotula "distancia de codepoint (formal, no dinero)" en AMBOS lentes. NUNCA es una cifra
con signo monetario; NUNCA se conecta a `paquete-cotizacion`, `brief`, ni ningun flujo de
cotizacion. Un test guarda contra esto: si el modulo contuviera simbolos de moneda o
imports del flujo de cotizacion, falla. El Precursor toca cultura/estetica; nada operativo.

## Omega11 (declarada ANTES de producir, umbral FIJADO antes de cualquier test)
> Esta pieza pierde si el ranking del proxy mecanico coincide con un ranking de severidad
> hecho a ciegas por un lector NO-autor, con Spearman rho > 0.6 -- porque eso significaria
> que el costo "curado a mano" era de hecho recuperable de un proxy computable barato,
> refutando la afirmacion de (+)5 de que el costo de significado no cruza a codigo.

- **Umbral:** rho > 0.6 = la pieza pierde. Fijado AQUI, antes de correr el test. No se
  reinterpreta despues (regla #4 del MOTOR).
- **Quien evalua:** el artista (o cualquier hispanohablante que NO haya escrito
  `_COSTO_POR_CHAR`). Explicitamente NO el agente que construyo o curo la tabla.
- **Como:** (1) el lector rankea a ciegas los pares crudos (año/ano, papá/papa, aún/aun,
  pingüino/pinguino, perdida de ¿/¡) por "cuanto duele", SIN ver el texto curado ni el
  numero del proxy; (2) se calcula Spearman rho entre ese ranking y el ranking del proxy
  mecanico; (3) el umbral (0.6) ya esta fijo, asi que el veredicto no se discute despues.
- **Condicion de perdida secundaria (estructural, chequeable por cualquier lector de
  codigo sin el test a ciegas):** si los dos lentes difieren en los datos y no solo en los
  encabezados, la pieza estaria agregando contenido al reencuadrar -- rompe el limite del
  Precursor. El `_self_check()` interno y el test lo cubren.

## Regularizador (Cultura) -- comprometido, PENDIENTE
Ranking a ciegas de 5 minutos del artista (`galeriabase1`): mostrado solo los pares crudos,
sin texto curado ni numeros, rankeados de memoria por "cuanto duele", ANTES de ver ninguna
columna. Ese ranking, fechado, es el regularizador: un juicio de lector real que el codigo
no tuvo mientras corria, comprometido con plazo (antes de escribir el resultado de esta
pieza). **Estado: PENDIENTE.** No hay resultado todavia; no se fabrica. Cuando el lector lo
haga, su Spearman rho contra el proxy decide la Omega11, y se registra sin reinterpretar.

## Estatutos (regla de escritura #2 del MOTOR)
- **"proxy mecanico"**: PROCEDIMIENTO formal (distancia de codepoint via `plegar`). No mide
  significado; ortogonal al criterio de curaduria.
- **"lente"**: PROCEDIMIENTO de reencuadre de vocabulario. NUNCA agrega contenido (los dos
  lentes emiten los mismos valores; el self-check lo verifica).
- **"valor curado"**: la cadena de juicio importada de `_COSTO_POR_CHAR`, escrita a mano.
  El codigo la muestra; no la computa ni la recupera del proxy.

## Uso
```bash
py projects/cultura/marca_sin_precio.py                     # lente linguistico (default)
py projects/cultura/marca_sin_precio.py --lente marca       # mismo dato, vocabulario de activo
py -m pytest tests/test_marca_sin_precio.py -q
```

## Resultado (12-jul-2026)
Pendiente: la Omega11 no puede evaluarse hasta que el artista haga el ranking a ciegas
(regularizador comprometido, arriba). La condicion estructural secundaria (lentes
identicos en datos) queda cubierta por `_self_check()` y el test desde ya. Nada se
reinterpreta: cuando llegue la lectura humana, su rho decide y se registra fechado.
