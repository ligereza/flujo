# Símbolos propios del plano

## Lo normal: agregarlos desde la app

Abrí **Plano / Rider**, andá al bloque **Símbolos Técnicos** y apretá
**+ Agregar**. Ponés el nombre, elegís el color y la zona, seleccionás el
archivo `.svg`, y queda listo: aparece al toque en la paleta, con su dibujo.

No hace falta tocar ningún archivo a mano para esto.

**Truco de diseño:** si en el SVG usás `currentColor` en lugar de un color fijo,
el ícono toma el color que elijas en la app, y así el mismo archivo se ve bien
en el plano oscuro y en el blanco.

El ícono se reescala solo para calzar en su casilla, respetando su proporción.
No hace falta exportarlo a un tamaño determinado.

## Qué queda guardado acá

Los `.svg` que subís se guardan en esta carpeta, y quedan declarados en
`data/plano_simbolos.json`. Podés editar ese archivo a mano si preferís —por
ejemplo para cambiarle el nombre o el color a varios de una— pero es opcional.
Ese archivo también permite dos cosas que la app todavía no ofrece: elegir en
qué eventos aparece cada símbolo (`cuando`) y renombrar o recolorear uno de los
17 que vienen de fábrica.

Si algún dato está mal, el programa **avisa por pantalla** y sigue con el resto
del plano. Un ícono nunca desaparece en silencio.

## El archivo de ejemplo

`_ejemplo_hidratacion.svg` está acá sólo como referencia de cómo se ve un SVG
que funciona (fijate en `currentColor`). **No está declarado**, o sea que no
aparece en ningún plano: no es un símbolo real de la operación, es una muestra
para copiar.
