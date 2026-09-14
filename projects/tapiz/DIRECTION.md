# Tapiz - direccion de arte (del artista, 2026-07-10)

Registro fiel de la direccion dictada por el usuario. Manda sobre lecturas
anteriores del proyecto (que lo trataban solo como visualizador de codigo).

## Concepto

- Tapiz = visualizacion de patron visual como en un viaje psicodelico.
  Cultura, diseno y sensacion de hogar calido (el tapiz/alfombra como objeto
  cultural domestico). El patron es la obra.
- El nombre del repo es la clave: vibecodeine = vibe + codeine. El icono
  moderno es el DOUBLE CUP (vaso doble), simbolo contemporaneo de droga.
- El tapiz es una animacion de arte ASCII con significado de DIGESTION:
  el patron metaboliza los glifos, el codigo se digiere como una sustancia.

## La pieza: README del repo como SVG animado

Doble invisibilidad:
1. Casi invisible al humano: contraste al umbral de percepcion, movimiento
   lentisimo. Hay que saber que esta para verlo.
2. Invisible al agente LLM: el agente lee markup estatico; la animacion solo
   existe en el tiempo, que el agente no habita. El <desc> del SVG le cuenta
   al agente lo que nunca podra percibir -- eso es parte de la obra.

## Relacion con el codigo existente

- projects/tapiz/vibecode/ (reconciliado 2026-07-10) es el TELAR: motor de
  patrones en espacio negativo para terminal. Infraestructura, no la obra.
- La obra vive en tapiz_readme.svg (SMIL/CSS, autocontenido, sin JS --
  GitHub solo anima SVG via <img> si no depende de scripts).
- El DOUBLE CUP ya existia como arte-ascii-readme.svg en la raiz del repo
  (vaso doble ASCII con liquido purpura, animacion CSS levitate) -- es la
  cabecera del README. El tapiz va DEBAJO: el vaso arriba, la digestion
  abajo. No reemplazar el vaso.

## Limites

Iconografia y cultura de la sustancia: SI (capa descriptiva/estetica,
permitida por hard limits del director). Nada generativo/sintesis: NO.

## Verificacion

Como todo lo visual del repo: con numeros o screenshots, no a ciegas.
Umbral de invisibilidad: delta de luminancia medio del patron vs fondo
menor a ~5% en el frame estatico (medido con screenshot headless + PIL).
