# Qué hay dentro de `obras.json`

> Este archivo describe el catálogo manual de 8 herramientas/obras declaradas.
> No es el archivo público completo. Para la proyección que consume la piel,
> usa `../ESQUEMA_ARCHIVO.md` y `archivo.json`.

Es una lista de obras. Cada obra es un objeto con estos campos.

Lo importante para quien dibuja: **algunos campos pueden venir vacíos o en
`null`, y eso significa que el dato no existe — no que valga cero.** Una obra sin
año no se muestra con un año inventado: se muestra sin año.

| campo | tipo | siempre está | qué es |
|---|---|---|---|
| `id` | texto | sí | identificador estable; sirve para enlazar a la obra |
| `title` | texto | sí | el título, tal como se muestra. Lleva acentos |
| `category` | texto | sí | Animación, Generative, Dibujo, 3D… |
| `year` | número | puede faltar | año de la obra |
| `description` | texto | sí | una o dos frases |
| `descriptionLong` | texto | puede faltar | el texto largo, si existe |
| `technique` | texto | puede faltar | cómo está hecha |
| `tags` | lista de textos | puede venir vacía | etiquetas; sirven para relacionar obras entre sí |
| `image` | ruta | puede faltar | imagen principal |
| `gallery` | lista de rutas | puede venir vacía | imágenes adicionales |
| `video` | ruta | puede ser `null` | video, si la obra es audiovisual |
| `mediaType` | texto | sí | qué tipo de medio es |
| `src` | ruta | puede faltar | el archivo principal |
| `poster` | ruta | puede ser `null` | cuadro de portada de un video |
| `createdAt` | fecha ISO | puede faltar | cuándo se registró |
| `placeholder` | booleano | sí | **`true` = la obra está anunciada pero el archivo no está** |
| `template` | texto | puede faltar | plantilla con la que se generó |

## Dos campos que importan más de lo que parecen

**`placeholder`.** Si es `true`, esa entrada no tiene obra detrás todavía.
Mostrarla como si estuviera terminada es exactamente el tipo de mentira que el
contrato prohíbe. Se puede mostrar igual —el archivo también es lo que falta—
pero tiene que verse que falta.

**`tags`.** Es lo único que relaciona una obra con otra. Si tu propuesta arma un
mapa, una red o una vecindad, sale de acá. No hay otro campo de relación.

## Cómo crece

Hoy son 8 obras cargadas a mano. El archivo va a crecer desde la curatoría
automática del archivo de Instagram, que agrega `conceptos`, `tecnica` y
`materiales` por obra. Cuando eso llegue, se agregan columnas acá y las pieles
que no las usen siguen funcionando igual: **campo que no conocés, campo que
ignorás.**
