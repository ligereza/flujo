# LASER TOOLKIT — ÍNDICE

Documento de enrutado para `docs/laser/toolkit.html`. Léeme primero; abre el HTML solo
si necesitas el detalle de una sección concreta.

---

## CONTEXTO FIJO DEL USUARIO

| Ítem | Estado |
|---|---|
| Proyectores | 2× Pangolin, **entradas ILDA DB25 libres** |
| Interfaz | FB3-QS (USB, 1 salida ILDA) |
| Software láser | **QuickShow — SIN licencia BEYOND** |
| TouchDesigner | **Commercial comprada en 2023** (perpetua + 12 meses de updates) |
| Hardware extra | Red y cables · interfaz USB-DMX o nodo Art-Net (modelo sin confirmar) |
| DAC alternativo | **No tiene** |
| Setup anterior | iPad → ethernet → PC → TouchDesigner → BEYOND (dibujo en vivo) |

### Datos pendientes de confirmar
- Velocidad de los escáneres (kpps) → define el presupuesto de puntos exacto
- Si la interfaz USB-DMX es un **Enttec DMX USB Pro** (QuickShow no acepta ninguna otra)
- Fecha exacta de compra de la licencia TD → define el build tope
- Una o dos FB3-QS

---

## LAS 4 RUTAS

```
A  Imagen BMP/JPG/GIF → QuickTrace (modo Centerline) → Cue Grid          [cero herramientas externas]
B  SVG → vpype → Modulaser|msvg2ild → .ild → import QuickShow            [control real del resultado]
C  Blender Line Art/Freestyle → secuencia SVG → vpype → .ild multiframe  [animación seria]
D  iPad → TD → Laser CHOP → Laser Device CHOP → Helios → ILDA in         [dibujo en vivo, sin Pangolin]
```

---

## ÍNDICE DE SECCIONES

| § | Título | Contiene |
|---|---|---|
| 01 | Veredicto de la licencia | Historia de builds del Laser CHOP y Laser Device CHOP; política de updates de TD; restricción Pangolin CHOP |
| 02 | Las cuatro rutas | Diagramas de pipeline A/B/C/D |
| 03 | Conversión SVG → ILDA | Modulaser, msvg2ild, ILD Render, LaserShowGen, LaserBoy, ilda-viewer + callejones sin salida |
| 04 | vpype | Comandos core y plugins (hatched, flow-imager, occult, ttf) |
| 05 | Código generativo | vsketch, p5.js-svg, ofxLaser, librería Ilda de Processing, awesome-plotters, DrawingBots |
| 06 | 3D a línea | Blender Line Art, Freestyle SVG Exporter, Rhino Make2D, Trace SOP |
| 07 | Imagen y video a línea | Contorno vs centerline, Inkscape, QuickTrace, TSP art/StippleGen, vtracer, Recraft |
| 08 | Animación vectorial | Cavalry, Glaxnimate, SVGator, Rive, Synfig/Manim + cómo muestrear SMIL |
| 09 | Tipografía de trazo único | Hershey Text, SingleLineFonts, Laser fonts de QuickShow |
| 10 | DACs | Tabla Helios/EtherDream/ShowNET/LaserCube/Moncha + audio DC-coupled |
| 11 | Contenido ya hecho | Pangolin Cloud, animated-lines, Photonlexicon, Discord |
| 12 | QuickShow nativo | ~2000 cues, Parametric Image Editor, QuickText/Shape/Targets/FX, multi-zona |
| 13 | Referencia técnica | **Presupuesto de puntos · reglas de diseño SVG · tabla DMX 16ch · atajos de teclado · MIDI/DMX** |
| 14 | El plan | Pasos para mañana y para después del show |

---

## RESTRICCIONES DURAS (no las re-investigues)

1. **QuickShow no tiene entrada de geometría en vivo.** No hay OSC, ni API de frames,
   ni stream ILDA por red. Eso es exactamente lo que se compra con BEYOND.
2. **La demo de BEYOND no emite al láser.** No sirve como parche.
3. **QuickShow no exporta ILDA.** La importación es de un solo sentido.
4. **QuickShow acepta SOLO el Enttec DMX USB Pro** como entrada DMX. La daughter board
   del FB3-SE no sirve. Sin Art-Net ni sACN nativos (eso es BEYOND).
5. **QuickShow no importa SVG.** Solo `.ILD .LDA .LDB .LDS .LPC`, y bitmaps vía QuickTrace.
6. **ILDA no tiene rellenos, grosor de trazo, gradientes, opacidad, máscaras ni texto.**
   Solo puntos con color y un bit de blanking. → usar **vpype-hatched** para simular relleno.
7. **No existe plugin ILDA para vpype**, ni extensión de Inkscape que exporte ILDA,
   ni conversor SVG→ILDA online funcional, ni paquete de ILDA en PyPI.
   *Sigue siendo cierto para herramientas externas. Desde 2026-07-31 el repo trae
   el suyo: `flujo laser ild pieza.svg` escribe ILDA Type 5 (RGB, nunca paleta),
   verifica el archivo releyéndolo, y `flujo laser lote --ild` lo hace por lote —
   la ruta B se cierra sin Modulaser ni msvg2ild.*
8. **Toda la línea Lasershow Converter de Pangolin** exige LD2000 o BEYOND.
9. **Pangolin CHOP** habla con BEYOND por DLL local (mensajes de Windows): misma máquina,
   solo Windows, sin red. Y TD no-comercial solo funciona con BEYOND demo.
10. **No confundir con láser de corte:** LightBurn, LaserGRBL, `svg2gcode` son gcode, no ILDA.

---

## NÚMEROS CLAVE

- **Presupuesto: 600–1000 puntos por frame** (a 30 kpps buscando 30–40 fps). Un SVG medio
  aplanado da 15.000–20.000 → la simplificación es obligatoria, no opcional.
- Cada salto en negro consume puntos (más sus puntos de reposo). 10 subtrazos ≈ 150 puntos
  gastados sin dibujar nada.
- Helios **USD 114** · Ether Dream 4 **USD 289** · updates TD Commercial **USD 300/año**
- QuickShow: hasta **9 FB3**, **30 zonas**, **60 cues/página**, **32 páginas**

---

## REGLAS DE ORO OPERATIVAS

- **Exportar siempre ILDA Type 5 (RGB)**, nunca con tabla de paleta → esquiva el bug
  histórico del botón "Details" del importador de QuickShow 4.x.
- SVG para láser: solo `stroke`, `fill:none`, color plano, texto ya en curvas,
  <8 subtrazos, viewBox cuadrado, sin detalle fino.
- Color: el blanco necesita los 3 canales; el azul saturado se ve mucho más apagado
  que en pantalla → para tonos celestes usar **cian y blanco**, no azul puro.
- Texto: usar **fuentes de trazo único** (Hershey / Laser fonts de QuickShow), nunca
  TrueType convertida a curvas (da contornos dobles).
- Verificar todo .ild en **ilda-viewer** antes de llegar al venue.

---

## ENRUTADO RÁPIDO

| Si el usuario pregunta por… | Ir a |
|---|---|
| Convertir un SVG a .ild | `flujo laser ild pieza.svg` (en el repo) · externas: §03 + §04 |
| Que una figura rellena no salga hueca | §04 (vpype-hatched) |
| Animación de verdad | §06 (Blender) o §08 |
| Recuperar el dibujo en vivo del iPad | §01 + §10 (Helios) |
| Contenido sin fabricarlo | §11 + §12 |
| Controlar QuickShow desde TD | §13 (tabla DMX, atajos, MIDI) |
| Foto o logo a trazos | §07 |
| Escribir código generativo | §05 |
| Texto en el láser | §09 |
| "¿esto se ve bien en láser?" | §13 (presupuesto de puntos + reglas de diseño) |

---

## ADVERTENCIA DE SEGURIDAD

Con DAC externo se pierden las protecciones de scan-fail de Pangolin. Armar siempre
con el haz bloqueado y subir potencia solo con geometría estable en pantalla.
Parada de emergencia física obligatoria. `ESC` = blackout en QuickShow.
