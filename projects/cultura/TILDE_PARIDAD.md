# TILDE_PARIDAD -- el medidor en el banco (FLAT CURRENCY)

Pieza generada con el protocolo `motor-omega` el 12-jul-2026, tras ignicion por
pedido real del artista (orden directa, valido como arranque segun
`puente/README.md`).

## Semilla
**(+)3** (`puente/SEMILLAS.md`, 12-jul-2026): "tilde_meter mide tokens = dialecto
Omega degradado. La Tilde NO es ahorro de tokens, es residuo intraducible."
Origen: `desktop/tilde_meter.py`.

## Caveat de reflexividad (arriba, no al final)
El "costo" con que el lado honesto rankea sale de `_COSTO_POR_CHAR`, la tabla
curada a mano de `tilde_residuo.py` -- **mismo linaje que esta pieza**. Esta pieza
prueba un script contra su hermano, no contra una nocion de costo independiente
del autor. Que un residuo sea "filoso" se deriva LEYENDO el string de costo que ya
existe en esa tabla (contiene la flecha `->` de una palabra que se vuelve otra:
`ano -> ano`, `papa -> papa`), no agregando juicio nuevo. El regularizador humano
(abajo) existe justo para corregir este sesgo desde afuera.

## Que hace
`projects/cultura/tilde_paridad.py` NO reemplaza al medidor -- eso ya lo hizo
`tilde_residuo.py`, que construyo la alternativa honesta. Esta pieza **pone al
medidor en el banco**: corre el instrumento acusado (`tilde_meter.measure`) y el
honesto (`tilde_residuo.cosechar`) sobre el **mismo texto real y no curado** (los
asuntos de commit de este repo, `git log --format=%s`, SOLO `%s`: nunca el autor)
y cosecha donde sus veredictos sobre "cuanto se degrado" se **invierten**.

Diferencia con `tilde_residuo.py`: aquella pieza construyo el instrumento honesto
sin tocar nunca la salida del acusado. Esta lo audita. Es un acto distinto:
**auditoria**, no cosecha nueva -- Precursor aplicado a dos codigos que ya existen
colisionando entre si, no un instrumento nuevo que reemplaza a otro. Tambien
responde a **(+)5** (el residuo que `tilde_residuo.py` genero: "el costo no cruza a
codigo, se cura a mano") REUSANDO esa misma tabla curada como verdad-terreno fija,
sin agregar curacion.

## Como activa cada operador
- **Precursor** (precipitar): colisiona `tilde_meter.measure` contra
  `tilde_residuo.cosechar`, alimentando a los dos el MISMO plegado
  (`tilde_residuo.plegar(texto)` es el "compressed" que `measure` espera). No se
  agrega contenido: ni plegado nuevo, ni tabla nueva, ni texto inventado. El
  umbral que baja: nadie habia mirado las dos salidas lado a lado. El corpus es
  `git log` real, multi-sesion, multi-autor, no escrito para esta pieza.
- **Psicosis** (sobre-narrar hasta la bifurcacion): la pieza sostiene dos lecturas
  incompatibles sin colapsar. (A) "el escalar del medidor es un proxy barato pero
  legitimo del residuo"; (B) "el medidor engana: paga 1 por marca sin mirar
  denominacion, asi que un monton de acentos leves (mas, esta, cafe) pesa mas que
  una sola virgulilla que invierte el sentido (ano/ano)". La bifurcacion se para en
  el escalar que se use para rankear. Regularizador obligatorio: el lector humano
  designado abajo (Psicosis nunca corre sin regularizador).
- **Tilde** (cosechar el residuo): el residuo NO esta dentro de ningun texto -- es
  el desacuerdo entre dos RANKINGS del mismo corpus. Nombrado con precision: par
  (X, Y) donde el medidor dice "X se perdio menos que Y" (menos marcas contadas)
  pero el honesto dice "X cuesta mas que Y" (X carga un residuo de inversion de
  sentido, Y no). Lo que no cruza: del dialecto del conteo al dialecto del costo.

## Hallazgo de mecanismo (verificado, no adivinado)
Al alimentar al medidor el plegado completo, `measure` devuelve **survival = 0.0
para TODO texto con marcas** -- el plegado mata todas las marcas. El numero de
cabecera del medidor no puede rankear: todo empata en 0.0 (**primer
aplanamiento**, la "tasa plana" del titulo). Para rankear, el medidor cae a su
unico escalar que varia: el **conteo** de marcas perdidas. Ese conteo es el
dialecto degradado que (+)3 acusa. El **segundo aplanamiento** -- la inversion que
la pieza cosecha -- es que ese ranking-por-conteo se invierte contra el
ranking-por-costo del instrumento honesto.

### Desviacion respecto de la propuesta (declarada, no escondida)
La propuesta original de esta pieza enuncio la Omega11 sobre un "umbral de
survival". Correr el codigo real mostro que survival degenera a 0.0 bajo el
plegado honesto, asi que el escalar operativo es el CONTEO de marcas, no un umbral
de survival. La Omega11 se reescribio para ese mecanismo real (abajo). La
desviacion es una correccion forzada por el API real (verificar contra dato, no
adivinar), no un cambio de intencion: sigue siendo "conteo vs costo se invierten".
De hecho la degeneracion de survival es un hallazgo mas fuerte (el numero de
cabecera del medidor ni siquiera rankea).

## Omega11 (declarada ANTES de exponer)
> Esta pieza pierde si los dos rankings NUNCA se invierten sobre el corpus real --
> es decir, si en todo el corpus mas marcas perdidas (dialecto del medidor) siempre
> acompana el costo mas filoso (dialecto honesto), de modo que conteo y costo
> coinciden y la afirmacion de (+)3 (que contar tergiversa el residuo) no tiene
> mordida empirica aca. Si eso pasa, la pieza es decoracion disfrazada de auditoria.

**Evaluable por (NO el autor):** un lector hispanohablante usuario del repo que no
sea autor de esta pieza.
**Como:** (1) lee los asuntos de commit crudos de los pares marcados INVERSION
(no el marco de la pieza) y confirma o rechaza que el residuo nombrado sea una
perdida de sentido real que un hispanohablante reconoce (p.ej. ano/ano); (2) vuelve
a correr la pieza sobre un corpus distinto o con otro criterio de "filoso" y
verifica que las inversiones no sean un artefacto de una sola eleccion del autor.
Este segundo paso es el punto mas debil de la pieza (ver Riesgos) y por eso es
parte del protocolo de evaluacion, no opcional.

## Regularizador (comprometido, PENDIENTE)
Dos elementos fuera de control del autor:
1. **Material no curado:** el corpus es `git log` del repo real -- frases que nadie
   escribio ni eligio para esta pieza.
2. **Lector humano designado (PENDIENTE):** un hispanohablante no-autor re-corre la
   pieza con otro criterio/corpus y juzga las inversiones. **Este paso esta
   comprometido pero AUN NO ejecutado.** No se fabrica su resultado: OBRA_02 enseno
   que una Omega11 sin su lector queda en suspenso, y asi queda esta hasta que el
   lector aparezca.

## Resultado
**PENDIENTE de evaluacion humana.** La pieza corre y produce el detalle por caso y
los pares invertidos, pero el veredicto de la Omega11 no es del autor. No se
reinterpreta ni se adelanta aca (regla de escritura #4 del MOTOR: lo fechado no se
reinterpreta; y aun no hay fecha de evaluacion que registrar).

## Riesgos (autocritica adversaria)
1. **Reflexividad:** la verdad-terreno de costo es de la misma tabla/linaje. La
   pieza prueba un script contra su hermano, no contra un afuera. Divulgado arriba;
   el lector humano lo corrige.
2. **Corpus flaco:** los asuntos de flujo tienden a ASCII/ingles ("chore:",
   "Merge"). Si hay < 2 textos con marcas, la pieza NO inventa: imprime
   `[ruido] insufficient signal` y para (restriccion tipo Davidson).
3. **Criterio de "filoso" fragil:** derivarlo de la flecha `->` en el string es
   leer la tabla, no juzgar de nuevo -- pero es una eleccion. Por eso el lector
   humano debe re-correr con otro criterio.
4. **Recaer en el pecado:** si la salida colapsara a un unico "N inversiones", la
   pieza seria el dialecto degradado que audita. Por eso el detalle por caso queda
   primario y el conteo es marco secundario, nunca el resultado.

## Uso
```bash
py projects/cultura/tilde_paridad.py                     # corpus = git log real
py projects/cultura/tilde_paridad.py --file corpus.txt   # corpus portable
py -m pytest tests/test_tilde_paridad.py -q
```
