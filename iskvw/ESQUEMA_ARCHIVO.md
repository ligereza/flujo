# El archivo, en una sola forma

> **Forma operativa, con contenido regenerable (verificada 2026-08-15).** La
> proyección local actual, construida con el snapshot MAK disponible, tiene
> 1.690 piezas y 4.729 vínculos. Esas cifras cambian cuando avanza el snapshot;
> no son parte del contrato y no deben copiarse a una piel como constantes.
>
> Se genera cuando se necesita. `iskvw/datos/archivo.json` NO se versiona; es
> un artefacto de runtime y su fuente es `obras.json` + micelio (live o
> snapshot), según la opción del generador.

Este documento es **el conector**. Define qué recibe una piel, sea lo que sea que
haya detrás.

Detrás hay dos familias que no se parecen en nada:

- **Las obras del artista**: pocas, con datos ricos —título, año, técnica,
  descripción— y **ninguna relación explícita**. Sólo etiquetas.
- **El micelio de MAK**: nodos de investigación y código con relaciones
  semánticas medidas; en el snapshot local son 1.530 piezas y 4.921 vínculos.

Una tenía que ver la otra y no podía. Cada piel terminaba escribiendo su propio
lector, y una piel nueva servía para una sola fuente. Con esta forma, una piel
pide *"dame las piezas y sus vínculos"* y siempre recibe lo mismo.

**Quien dibuja no necesita saber de dónde salió.** Ese es todo el punto.

---

## La forma

```json
{
  "version": 1,
  "fuente": "obras",
  "generado": "timestamp de generación",
  "piezas": [ ... ],
  "vinculos": [ ... ],
  "meta": { }
}
```

### Una pieza

```json
{
  "id": "tatuaje-romero",
  "titulo": "Tatuaje de ramas de romero",
  "clase": "obra",
  "fecha": "2020-11",
  "resumen": "Una o dos frases.",
  "etiquetas": ["botánico", "línea"],
  "peso": 3,
  "medio": { "tipo": "imagen", "src": "obras/romero.jpg" },
  "estado": "publicada",
  "extra": { }
}
```

| campo | obligatorio | qué es |
|---|---|---|
| `id` | **sí** | Identificador estable. Es lo que usan los vínculos |
| `titulo` | **sí** | Lo que se muestra. Con tildes y eñes |
| `clase` | **sí** | De qué familia es: `obra`, `informe`, `codigo`, `evento`… |
| `fecha` | no | `AAAA`, `AAAA-MM` o `AAAA-MM-DD`. **Ausente = no se sabe**, no es cero |
| `resumen` | no | Una o dos frases |
| `etiquetas` | no | Lista de textos. Puede venir vacía |
| `peso` | no | Cuánta materia tiene la pieza. Sirve para el tamaño. Por defecto 1 |
| `medio` | no | `{tipo, src, poster}`. `tipo`: `imagen`, `video`, `texto`, `ninguno` |
| `estado` | no | `publicada`, `anunciada`, `borrador`. **`anunciada` = todavía no existe** |
| `extra` | no | Cualquier cosa propia de la fuente. **Una piel que no lo entiende lo ignora** |

### Un vínculo

```json
{ "de": "tatuaje-romero", "a": "hoja-seca", "peso": 0.78, "clase": "semantico" }
```

| campo | obligatorio | qué es |
|---|---|---|
| `de`, `a` | **sí** | `id` de dos piezas |
| `peso` | **sí** | Entre 0 y 1. Cuán fuerte es el vínculo |
| `clase` | no | `semantico` (medido), `etiqueta` (comparten una), `manual` |

Los vínculos **no tienen dirección**: `de` y `a` son intercambiables.

---

## Las cinco reglas

Son las mismas del contrato y no se negocian. Repetidas acá porque quien escribe
una piel lee este archivo:

1. **Ninguna pieza afirma un dato que no tiene.** Sin fecha, no se inventa una.
   Un contador que dice doce muestra doce. Una barra que no mide nada no va.
2. **Todo lo visible en castellano correcto**, con tildes y eñes.
3. **Abre sin internet.** Sin CDN, sin fuentes remotas, sin analítica.
4. **Se ve en un teléfono.** No igual: visible.
5. **La piel se borra y se pone otra sin tocar los datos.**

Y una que sale de esta forma:

6. **Campo que no conocés, campo que ignorás.** Cuando la curatoría agregue
   conceptos y técnica por obra, van a llegar dentro de `extra`. Una piel vieja
   tiene que seguir funcionando el día que eso pase.

---

## Cómo se genera

```bash
py tools/gen_archivo_iskvw.py --fuente obras             # las obras del artista
py tools/gen_archivo_iskvw.py --fuente micelio            # lo que MAK relacionó, EN VIVO
py tools/gen_archivo_iskvw.py --fuente micelio_snapshot   # lo último que la caja empujó
py tools/gen_archivo_iskvw.py --fuente ensayos            # los ensayos y sus íconos
py tools/gen_archivo_iskvw.py --fuente todo               # archivo público, sin ensayos
py tools/gen_archivo_iskvw.py --fuente todo --incluir-ensayos
```

En esta verificación el micelio en vivo no fue alcanzable desde MAK (conexión
rechazada), por lo que `--fuente todo` cayó correctamente al snapshot
`iskvw/datos/micelio.json` —1.530 piezas y 4.921 vínculos— y produjo localmente
1.690 piezas y 4.729 vínculos. La promoción de cambios se revisa en `main`;
`source/*` conserva puntas históricas exactas y no es una fuente de runtime.
El mismo principio usa `campo.json` para las posiciones: snapshot regenerable,
no una promesa de conexión en vivo.

Sale a `iskvw/datos/archivo.json`. Una piel lee ESE archivo y nada más.

**La fuente `obras`** deriva los vínculos de las etiquetas compartidas: dos obras
con etiquetas en común quedan unidas, con peso según cuántas comparten. Esos
vínculos son `clase: "etiqueta"`, no `semantico`, porque nadie midió que se
parezcan — comparten una palabra.

**La fuente `micelio`** trae los vínculos que MAK midió de verdad, por cercanía
entre los textos. Ahí `clase` sí es `semantico`; el snapshot actual aporta la
mayor parte del grafo público.

**La fuente `ensayos`** (2026-07-30) trae los ensayos curados de
`docs/cultura/ensayos/` con su anexo iconográfico: el ensayo entra como una
pieza `informe`, cada **concepto nombrable** como una pieza `concepto` colgada
de él, y cada ícono que existe en disco como una `pieza_grafica` colgada de su
concepto. Es el tramo que hace que el research tenga garantía visual: si MAK
dice que entendió un tema, el anexo prueba si puede volverlo sistema
representativo (post, semilla SVG/laser, animación, pieza ASCII como
VIBE-CODEINE). No es basura ni decoración.

Desde el 2026-08-05 esa fuente es **opt-in**: `--fuente ensayos` la mira sola y
`--fuente todo --incluir-ensayos` la mezcla deliberadamente. `--fuente todo`
sin flag publica el archivo de obra/taller y no mezcla informes ni conceptos
de investigación por accidente.

Tres cosas de esa fuente, porque son las reglas y no detalles:

- sus vínculos son `clase: "manual"`, **nunca** `semantico`: los declara un
  manifiesto, nadie midió una distancia;
- un ícono declarado en el manifiesto y **ausente del disco no produce pieza**
  — una pieza que afirma un archivo que no está es la mentira que la regla 1
  prohíbe;
- `extra.declara_animacion` dice que el SVG **tiene keyframes**, que es un dato
  que el archivo codifica y cualquiera puede verificar sin rasterizar. Que se
  mueva de forma perceptible es otra pregunta y se mide aparte contando cuadros
  distintos (`py tools/iconos_conjunto.py animar`). Medido el 2026-07-30 sobre
  los dieciséis: todos dan 10 de 10 cuadros distintos.

Cada clase de pieza lleva su prefijo en el id (`ensayo-`, `concepto-`,
`icono-`) para que un ensayo y una obra del artista no puedan colisionar: dos
piezas distintas con el mismo id se fusionarían al unir las fuentes y una
desaparecería.

Cuando la percepción del archivo termine, las obras van a tener las dos cosas:
sus datos y sus vínculos medidos. Cuando el research necesite verse, entra por
su propia puerta.
