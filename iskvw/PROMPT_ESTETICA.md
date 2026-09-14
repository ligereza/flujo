# Prompt para pedir una estética nueva

Copiá todo lo que está bajo la línea y pegalo en Arena, en Google AI Studio o en
el agente que uses, **junto con** `cultura/mak_plataforma/contrato_archivo.py`
y `ESQUEMA_ARCHIVO.md`. Ese módulo es el contrato ejecutable compartido; no
existe un `CONTRATO.md` separado en este repo.

Los tres recursos tienen que decir lo MISMO. Esta versión separa el catálogo
manual `obras.json`, la proyección `archivo.json` y el contrato ejecutable; los
ensayos ilustrados de research tampoco entran al archivo público por defecto.
Un modelo web que reciba instrucciones contradictorias escribe una piel para
datos que no existen, y eso no se descubre hasta publicarla.

Lo que devuelva va a `piel/<nombre>/` y no toca nada más.

---

Necesito la **cara visible** de un archivo de obra digital. Se llama **ISKVW**.
No es un portafolio de agencia ni un currículum: es el archivo de un artista, y
lo que importa es dejar ver la obra, no venderla.

**Leé primero los recursos que te paso**: `cultura/mak_plataforma/contrato_archivo.py`
define la conversión compartida, y `ESQUEMA_ARCHIVO.md` define exactamente qué
datos vas a recibir. Todo lo que muestres tiene que salir de ahí.

Lo que recibís es **un solo archivo**, `iskvw/datos/archivo.json`, con dos listas:
**piezas** y **vínculos entre piezas**. No importa qué hay detrás — obras del
artista, piezas gráficas derivadas del taller, código — todo llega con la misma
forma. Los informes y conceptos de research existen como vista explícita, pero
no entran al archivo público por defecto. Eso es a propósito: tu piel no tiene que saber de dónde salió, y el día
que aparezca un tipo de pieza nuevo, tu piel sigue funcionando sin tocarla.

En la proyección local actual son **1.690 piezas y 4.729 vínculos** (snapshot
MAK, 2026-08-15). Se reparten en 104 `codigo` y 1.586 `obra`; los vínculos son
4.711 `semantico` y 18 `etiqueta`. Estas cifras son una medición del snapshot,
no un contrato fijo: al cambiar la fuente, el contador debe regenerarse.

Cada pieza trae: `id`, `titulo`, `clase`, `fecha`, `resumen`, `etiquetas`,
`peso`, `medio`, `estado` y `extra`. Cada vínculo trae `de`, `a`, `peso` y
`clase`. La proyección actual añade `posicion` solo a las 219 piezas con
coordenadas medidas en `campo.json`; una piel debe tolerar que falte y nunca
inventarla.

Los vínculos traen **peso**, y su `clase` dice de qué están hechos: `manual` es
una relación declarada, `etiqueta` sólo dice que dos piezas comparten una
palabra. **Si tu propuesta dibuja cercanía, distinguí las clases**: tratar una
coincidencia de palabra como si fuera parentesco medido es exactamente el tipo
de mentira que este archivo no admite. Si aparece una clase que no conocés,
dibujala como la más débil y decilo, no la asimiles a la más fuerte.

## Lo que NO quiero, y es lo más importante

No quiero un sitio convencional. Concretamente:

- **Nada de título arriba + menú + secciones apiladas.** Ese formato ya está
  descartado.
- Nada de "hero" con una frase grande y un botón.
- Nada de grilla de tarjetas con sombra y hover que levanta.
- Nada de scroll narrativo con animaciones de aparición.

Si tu propuesta se puede describir como "un sitio de portafolio bien hecho",
está mal. Empezá de nuevo.

## Lo que sí busco

**La interfaz puede ser parte de la obra.** La referencia que me gusta es un
instrumento corriendo, no un documento: un lienzo generativo vivo de fondo
—reacción-difusión, redes de nodos, grillas que pulsan—, secciones que se
conmutan en vez de apilarse, una barra de estado que reporta lo que realmente
está pasando, y controles que el visitante puede mover para alterar lo que ve.

No copies esa referencia: **entendé el principio**. El principio es que el
visitante entra a algo que está funcionando, no a algo que está publicado.

Otras direcciones que servirían igual, para que veas el rango: un archivo que se
explora como un mapa y no como una lista; una interfaz que se comporta como una
herramienta de trabajo real; algo que responda al gesto del visitante y cambie
según lo que toca. Cualquier cosa donde **mirar la obra sea hacer algo**, no
desplazarse.

## Reglas que no se negocian

1. **Ningún elemento puede afirmar un dato que no tiene.** Si mostrás un
   contador, que cuente de verdad. Si una obra no tiene año, no le inventes uno.
   Un número decorativo que finge medir algo es el peor error posible acá.
2. **Todo el texto visible en español correcto, con acentos y eñes.**
3. **Tiene que abrir sin internet**: sin CDN, sin fuentes remotas, sin analytics.
   Todo lo que necesite va adentro.
4. **Tiene que poder verse en un teléfono.** No igual, pero sí visible.
5. **No modifiques los datos.** Si necesitás un campo que no existe, decilo en
   tu respuesta en vez de inventarlo.

## Qué entregar

Una carpeta autocontenida con un `index.html` que lea **`iskvw/datos/archivo.json`**
—el mismo que se describe arriba— con rutas relativas desde `piel/<nombre>/`, o
sea `../../datos/archivo.json`. Si usás librerías, que viajen adentro.

`iskvw/datos/obras.json` contiene 8 entradas y son HERRAMIENTAS del repo, no el
archivo público completo. Una piel escrita contra ese archivo mostraría 8 cosas
en lugar de la proyección actual; por eso la entrada obligatoria es
`iskvw/datos/archivo.json`.

Y aparte, en tu respuesta: **tres o cuatro líneas explicando cuál es la idea**.
Qué es esto, por qué esta forma y no otra, y qué hace el visitante. Si no podés
explicarlo en cuatro líneas, probablemente sea decoración.
