# vaso_animado -- el double cup, mas alla de levitate

Pieza nueva, autocontenida, SVG animado (SMIL + CSS, sin JS). NO toca ni
reemplaza `README.md` ni `arte-ascii-readme.svg` (obra terminada del
artista, cabecera del repo -- ver `projects/tapiz/DIRECTION.md`: "No
reemplazar el vaso"). Esto es una continuacion: mismo icono (double cup,
vibecodeine = vibe + codeine), digestion mas lenta.

## Que hace

`arte-ascii-readme.svg` hace RESPIRAR el vaso entero (levitate, 6s, alto
contraste, glifos vivos). `vaso_animado.svg` hace METABOLIZAR el liquido
adentro, aplicando la tecnica de doble invisibilidad que ya probo
`tapiz_readme.svg`:

- **Nivel de codeina, sube y baja** (~211s por ciclo): las filas de glifos
  del liquido se desplazan verticalmente muy despacio, como una digestion.
- **Color del liquido, cicla** a traves de los 4 purpuras ya fijados en
  `arte-ascii-readme.svg` (`#9333ea #c084fc #7e22ce #e879f9`), ~140-170s por
  vuelta, desincronizado fila por fila.
- **Los glifos deletrean "vibecodeine"**, fila tras fila, mas presentes
  arriba (recien tragado) y mas tenues abajo (ya absorbido) -- la misma
  metafora de digestion de `tapiz_readme.svg`, ahora adentro del vaso.
- **Condensacion**: 12 gotas sobre el vidrio exterior aparecen y se
  disuelven en oleadas independientes (70-140s cada una, todas
  desincronizadas).
- **Vapor**: 3 puntos suben y se disuelven sobre la boca del vaso interior.
- **El vidrio "se asienta"**: el contorno punteado del vaso doble
  (exterior + el interior que asoma sobre el borde) tiene un
  stroke-dashoffset que deriva en 220-260s.

Doble invisibilidad (la misma que `DIRECTION.md` pide para toda la pieza):
1. **Casi invisible al humano**: opacidades de milesimas (0.03-0.10), nunca
   mas. Verificado por screenshot headless (Edge `--headless --screenshot`):
   a contraste normal el vaso apenas se distingue del fondo; con el
   contraste forzado al maximo, la estructura completa (vaso doble, filas
   de "vibecodeine", condensacion, vapor) aparece intacta y bien clipeada.
2. **Invisible al agente LLM**: el `<desc>` del SVG le narra al agente todo
   lo que la animacion hace -- porque el agente lee markup estatico, fuera
   del tiempo, y la animacion solo existe en el tiempo.

## Paleta

flujo real (`projects/flujo/flujo.json`, via
`projects/tapiz/vibecode/svg_export.py::FLUJO_HEX`): ink `#1f2a24` (fondo),
paper `#f8f1e3` (vidrio, condensacion), support `#675f55` (trazo
secundario). Los 4 purpuras del liquido son los mismos ya fijados en
`arte-ascii-readme.svg` -- continuidad de marca entre las dos piezas del
vaso, no una paleta nueva inventada.

## Archivos

- `projects/tapiz/vaso_animado.py` -- generador (procedural, Python puro,
  sin dependencias externas mas alla de `vibecode.svg_export.FLUJO_HEX`).
- `projects/tapiz/vaso_animado.svg` -- la pieza (salida del generador,
  versionada tal cual para que no dependa de correr Python para verse).

## Como verla

```bash
py projects/tapiz/vaso_animado.py            # regenera vaso_animado.svg
```

Abrir `projects/tapiz/vaso_animado.svg` directo en un navegador (o
`file://` local), o incrustarla en cualquier Markdown con
`<img src="projects/tapiz/vaso_animado.svg">` -- igual que
`arte-ascii-readme.svg` y `tapiz_readme.svg`, GitHub anima el `<img>` sin
depender de scripts (solo SMIL/CSS).

## Verificacion hecha

- `py -c "import xml.etree.ElementTree as ET; ET.parse(...)"` -- XML
  bien formado, sin excepciones.
- Render real con Microsoft Edge headless
  (`msedge --headless --screenshot=...`) contra el archivo `file://`:
  renderiza sin errores. Screenshot con contraste forzado al maximo
  confirmo que el vaso doble, las filas de "vibecodeine" clipeadas a la
  silueta del vaso, la condensacion y el vapor estan todos en su lugar
  geometrico correcto (no es solo invisible, es la estructura correcta
  a umbral bajo).
- No se toco `README.md` ni `arte-ascii-readme.svg`.
