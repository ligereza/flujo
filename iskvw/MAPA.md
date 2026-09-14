# iskvw · qué hay acá

Mapa **factual**: qué archivo es qué, qué comando genera qué, y los números
medidos el 2026-07-27. La dirección artística NO está acá y no la escribe un
agente — eso ya se intentó y el usuario lo rechazó con razón (ver la decisión
"un loop no escribe documentos" en `context/LAST_HANDOFF.md`).

Si algo de este archivo no calza con lo que ves, confiá en el repo y corregilo
en el mismo PR que lo detecte.

## El sitio en vivo

El dominio visible → GitHub Pages de este repo, publicado por
`.github/workflows/publicar_iskvw.yml` en cada push a `main` que toque `iskvw/`.
Hoy el valor por defecto es `iskvw.cl`; la migración se prepara definiendo la
variable de repositorio `PUBLIC_DOMAIN`, sin tocar la piel ni los datos.
Sube **sólo `iskvw/`**: nada de RD, MAK ni xio. La raíz del sitio es la piel
`campo`.

## Los archivos

```
iskvw/
  CONTRATO.md          qué debe cumplir cualquier piel para no mentir
  ESQUEMA_ARCHIVO.md   la forma piezas+vínculos que sirve a las dos fuentes
  PROMPT_ESTETICA.md   lo que se le pasa a un agente externo para pedir una piel
  README.md            índice de esta carpeta
  MAPA.md              este archivo
  editor.html          el panel de curaduría: se abre, se edita, se descarga
  datos/
    ESQUEMA.md         qué campos tiene obras.json
    obras.json         8 piezas generativas del repo (VOLÁ, Campo, Cenefa…)
    campo.json         219 obras del archivo, con posición medida y capas
    curaduria.json     la mano del artista sobre lo percibido
    tablero.json       qué mejoras están encendidas, y el patch de efectos
  piel/
    campo/             la piel viva: el organismo. Es la raíz del sitio
    terminal/          piel anterior. Lee sólo obras.json (8 piezas)
    trazos/            208 SVG + _indice.json. La obra que puede viajar
    lib/               librerías vendorizadas: tsne, trazo, gestos, distancia
```

## Los números, medidos

| | |
|---|---|
| **piezas que publica el sitio** (`archivo.json`) | **446** — 219 `pieza_grafica`, 227 `obra` |
| **vínculos que publica el sitio** | **237** — 219 `manual`, 18 `etiqueta` |
| obras con posición medida (`campo.json`, el respaldo) | **219**, todas de `posts/` |
| con trazo publicado | **208** (las 11 restantes son video o sin contraste) |
| capas | `tilde` en 219, `trazo` en 208 |
| vecindad conservada | **48,6 %** — lo que la proyección puede afirmar |
| piezas de `obras.json` | 8, y son HERRAMIENTAS del repo, no obras |

Las dos primeras filas son lo que se ve hoy; la tercera es el respaldo. Hasta el
2026-08-01 esta tabla publicaba sólo el 219 y veinte líneas más abajo el 479, o
sea dos cifras del mismo campo en una página.

`vecindad_conservada` es el número que sostiene el campo: de los vecinos reales
de cada obra en 768 dimensiones, qué fracción sigue siendo vecina en el plano.
Si baja, lo que el campo afirma se debilita y hay que decirlo.

## El costo por frame de la piel, medido (2026-08-01)

`node tools/iskvw_piel_medir.mjs` corre las funciones REALES de la piel
publicada en node (misma técnica que el smoke), entra por el modelo de semilla
`#semilla=&centro=&escala=` y CUENTA el trabajo de cada frame. Los conteos son
deterministas y los fija `tests/test_iskvw_piel_medir.py`; los milisegundos son
de la máquina que midió y jamás se fijan.

Esta tabla quedó vieja dos veces sin que nadie la corrigiera: seguía diciendo
"217 gradientes + 434 arcos" y "30 segmentos" cuando `nodo_glifo` (#433) ya
había vuelto el nodo un glifo (0 gradientes, 0 arcos) y el propio
`tests/test_iskvw_piel_medir.py` tenía pineado 107 como peor caso, no 30. Re-
medida hoy, con dos cambios reales encima: el vínculo pasó a dibujarse como haz
de láser (halo ancho + núcleo fino, `globalCompositeOperation='lighter'`, pedido
del artista), así que cada segmento cuesta DOS trazos en vez de uno; y el nodo
perdió el piso que `E.despliegue` le ponía a la densidad del glifo, así que se
dibujan más caracteres por cuadro durante la navegación. Los dos mueven el
número; ninguno se acerca al techo.

| | |
|---|---|
| sustrato `archivo.json` (1976 piezas) | **5158 vínculos** indexados una vez (20632 entradas) |
| peor escenario de la grilla | **2492 segmentos por frame** (medio abierto) — el micelio ya llega al archivo público y el bloom láser pinta cada vínculo visible en dos pasadas |
| todos-contra-todos, la referencia | 23.871 pares (219 obras) / 1.951.300 (1976 piezas) por frame |
| sustrato `campo.json` (el respaldo vivo) | **0 segmentos** siempre: no publica vínculos |
| banda densa abierta, trabajo por nodo | el nodo es glifo desde #433 (0 gradientes, 0 arcos): **656 `fillText`** por cuadro sobre `archivo.json` (370 sobre el respaldo `campo.json`), incluye el halo del glifo cuando es lo bastante opaco para necesitarlo |
| techo fijado | 6000 segmentos por frame — 2,4× lo medido, 325× bajo el todos-contra-todos |

Lo que sigue sin medirse: cuadros por segundo en un teléfono. Eso lo mide el
usuario con el aparato en la mano; ahora tiene contra qué comparar.

## Los comandos

```bash
# el campo: posiciones medidas desde los embeddings del micelio (necesita MAK)
py tools/gen_campo_iskvw.py --vectores <v.json> --meta <m.json>

# el índice de trazos, para que la piel no pida lo que no existe
py tools/gen_campo_iskvw.py --indice-trazos iskvw/piel/trazos

# las capas: cada una mide algo y lo deja en el campo
py tools/gen_capas_iskvw.py            # correr las activas
py tools/gen_capas_iskvw.py --listar   # qué hay y qué corre

# el contrato unificado público: obras del repo + micelio de MAK, una sola forma
py tools/gen_archivo_iskvw.py --fuente todo

# vista explícita de research ilustrado: informes + conceptos + anexos SVG
py tools/gen_archivo_iskvw.py --fuente ensayos
py tools/gen_archivo_iskvw.py --fuente todo --incluir-ensayos

# las librerías de la piel, como módulos ESM sin CDN ni build
py tools/vendorizar_iskvw.py

# la curaduría, validada antes de entrar al portón: ids desconocidos o
# duplicados, campos inválidos, svg firmado ausente, diacríticos mutilados
py tools/validar_curaduria.py
py tools/validar_curaduria.py --curaduria <descarga>/curaduria.json
# el costo por frame de la piel, contado en node: determinista, sin red
node tools/iskvw_piel_medir.mjs
```

## Qué se edita a mano y qué se genera

**Se edita** (y por eso viaja en el repo):
`data/iskvw_campo_filtro.json` — qué obras entran, hoy `posts` y `reels`.
`data/iskvw_capas.json` — qué capas corren.
`data/iskvw_librerias.json` — qué librerías se vendorizan.

**Se edita a mano o con el panel**: `datos/curaduria.json` — la mano del
artista (título, mostrar, abstracción, svg firmado, régimen, y desde
2026-07-31 tres campos opcionales que no cambian nada hasta que se escriben:
**peso** — número > 0, cuánta materia tiene la pieza, desplaza al peso medido
del contrato—, **serie** —etiqueta de agrupación, viaja en `extra.serie`— y
**nota** —la nota del artista, en `extra.nota`, español correcto con tildes).
El panel es `iskvw/editor.html`: una página estática, sin build y sin servidor
propio. Se abre con el repo servido desde la raíz (`py -m http.server`, después
`/iskvw/editor.html`), lee `datos/archivo.json` y si no está `datos/campo.json`,
y su única salida es un **`curaduria.json` que se descarga**: no escribe en
disco, el archivo entra por el mismo portón que todo lo demás. Una pieza que no
se toca **no aparece** en ese archivo — cada id que sale es una decisión.

Tres protecciones del panel (2026-07-31): **importar** un `curaduria.json`
descargado y todavía no commiteado para seguir editándolo (botón en la
cabecera; sin eso, reabrir la página retomaba en silencio la copia vieja del
repo); el navegador **pregunta antes de cerrar** si hay ediciones que no se
descargaron (descargar es lo que marca el estado como a salvo); y un campo por
pieza que el panel **no entiende viaja intacto** en la salida — la misma regla
que el tablero declara para sus valores no booleanos. El circuito completo
—panel → validador → consumidor— está fijado por
`tests/test_curaduria_roundtrip.py`: lo que el panel exporta valida sin
errores y es exactamente lo que `aplicar_curaduria()` obedece.

La misma página tiene el **tablero de mejoras**: `datos/tablero.json`
(`{"version": 1, "mejoras": {…}}`), un interruptor por clave. Las claves las
agrega el agente que trae cada mejora; el editor **no conoce ninguna** y dibuja
las que encuentre, así que una mejora nueva aparece sola sin tocar la página. El
ciclo es **prender → descargar → subir**: hasta que el archivo no entra al repo,
no cambió nada. Cada archivo tiene su propio botón, porque son dos archivos
distintos y un botón único haría que apagar una mejora pareciera guardado
cuando lo que bajó fue la curaduría. Un valor que no es `true`/`false` se
muestra de sólo lectura y viaja de vuelta intacto: el editor no destruye un dato
que no entiende.

**Se genera** y no se toca a mano: `datos/campo.json`,
`piel/trazos/_indice.json`, `piel/lib/*.js`. `datos/archivo.json` se genera y
**no se versiona**.

**La piel pide el sustrato, y lo recibe** (medido 2026-08-01): `piel/campo` y
`piel/terminal` intentan `datos/archivo.json` primero —piezas **y** vínculos—
y si no está siguen con `campo.json` y `obras.json`.

`archivo.json` **no se versiona pero SÍ se publica**: el workflow lo genera con
`gen_archivo_iskvw.py --fuente todo` antes de subir, y recién después verifica
que exista. Desde el 2026-08-05 `todo` excluye ensayos por defecto: el sitio
publica 446 piezas y 237 vínculos del archivo de obra/taller. La vista de
research ilustrado sigue viva con `--fuente ensayos` o
`--fuente todo --incluir-ensayos`: 33 piezas y 32 vínculos adicionales en la
medición local de ese día.

Hasta el 2026-08-01 este párrafo decía lo contrario —"hoy el camino vivo es el
respaldo"— y era cierto sólo entre el 2026-07-30 18:40 y las 23:10 UTC del
MISMO día, cuando CI empezó a generarlo (PR #408). Cuatro horas y media de
vigencia, y sobrevivió a dos ediciones posteriores de este archivo. **Una frase
que describe un estado que dejó de existir es peor que ninguna: se lee como
medición.** El micelio de MAK, en cambio, NO entra en CI (el runner no ve la
caja: `no se pudo leer el micelio (Connection refused)`), así que sus vínculos
no llegan al sitio y eso sí sigue siendo cierto.

**La obra deforma el campo, y lo deforma con lo que ella mide** (2026-07-30):
la mejora `patch_efectos` del tablero, y su cableado vive en el mismo archivo
—`patch`, al lado de `mejoras`— como un patch de sintetizador modular. El
editor lo devuelve intacto: sólo toca las llaves, no el cableado.
Cada fila conecta una
**señal** de la pieza —sus marcas de tilde, los subtrazos de su vector, cuánto
de lo que se le percibió tiene tono, la etiqueta de quiebre, su materia— con un
**efecto** sobre lo que tiene alrededor: `pulso` (el tiempo de los glifos
vecinos se dilata y se contrae), `curvatura` (los vecinos giran alrededor de la
obra), `sangrado` (su color se corre sobre ellos), `desgarro` (los glifos se
cortan por filas) y `gravedad` (la lectura se apoya en la pieza pesada al
pasar). Si la obra no trae el dato, el efecto vale **cero**: un efecto es una
afirmación, y ninguna pieza afirma lo que no tiene.

La llave maestra es `mejoras.patch_efectos` y **se publica apagada**. Apagada,
la piel dibuja exactamente igual que antes —medido, no declarado: el
`tools/iskvw_piel_smoke.mjs` arranca la piel sin tablero y con el tablero
publicado y exige que las 7.647 marcas del dibujo sean idénticas. Encenderla es
decisión del artista, y se hace editando ese archivo, no la piel.

Bajo la maestra, **cada efecto tiene su propia llave** (`efectos` en el
tablero, todas publicadas encendidas): con la maestra prendida, un efecto en
`false` queda mudo —coeficiente exactamente cero, sus rutas se descartan al
compilar— y los demás siguen. También medido, efecto por efecto: el smoke corre
cada llave a solas y exige la firma que sólo ese efecto puede dejar (curvatura
desplaza sin tocar color, sangrado tiñe sin desplazar, desgarro corta sólo en
x, pulso altera la traza de glifos, gravedad desvía la lectura), y con las
cinco apagadas el tablero fuerte dibuja marca por marca igual que sin tablero.

**Los vínculos se dibujan siempre, tenues y por peso** (decisión del usuario,
2026-07-30): la opacidad sale del peso del vínculo, con techo bajo, y van
**debajo** de las obras — la relación es el sustrato, la obra es lo que se mira.
Se descarta todo vínculo que no tenga sus **dos** puntas en cuadro, y los vecinos
se indexan una vez al sembrar: el defecto de recorrer todos los pares en cada
frame está fijado por `tests/test_iskvw_vinculos.py`. Medido sobre las 219
piezas del campo: entre 207 y 615 segmentos por frame según dónde se lea, contra
23.871 pares que costaría el todos-contra-todos. Lo que NO se midió, y por eso
no se afirma: cuadros por segundo en un teléfono.

**Una sesión es una semilla** (2026-07-30, PROYECCION 6.2): el hash dejó de ser
sólo un ancla y ahora codifica la lectura completa,
`#semilla=<pieza>&centro=<y>&escala=<lateral>`, escrita con `replaceState` al
terminar un gesto. Misma semilla + mismo archivo = misma constelación, fijado
por `tests/test_iskvw_semilla.py` contra este mismo archivo. Un enlace viejo de
sólo id sigue funcionando.

## Lo que falta, y de quién es

- **La dirección**: qué es este archivo como obra. **Del usuario.**
- **Si los ensayos se publican en iskvw.cl.** Decidido por frontera, no por
  descarte: los ensayos y sus íconos son un producto válido del research, pero
  no entran al archivo público por defecto. Se publican sólo por opt-in explícito
  (`--incluir-ensayos`) o en una piel/vista separada de research.
- ~~Qué son las 8 piezas de `obras.json`~~ **CONTESTADO por el usuario**: son
  HERRAMIENTAS del repo (VOLÁ, Campo, Cenefa…), no obras. Siguió publicado como
  pregunta abierta hasta el 2026-08-01 aunque la respuesta estaba escrita — que
  es exactamente el defecto que el handoff existe para evitar.
- ~~La piel `terminal` sigue leyendo sólo `obras.json`~~ **HECHO 2026-08-01**:
  lee `archivo.json` con el mismo orden de respaldo que `campo`. Medido contra
  el sustrato público actual: 446 piezas, 53 etiquetas, 8 categorías.
- **Los vínculos del micelio no llegan al sitio**: el runner de CI no ve la caja
  MAK, así que `--fuente todo` los omite y lo dice en el log. Las 446 piezas
  salen del material público del repo; los ensayos ilustrados quedan en la vista
  explícita de research.
- 34 reels sin percibir en MAK. Ya están declarados en el filtro: entran solos.
