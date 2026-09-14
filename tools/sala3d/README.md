# sala flujo - galeria 3D conceptual del portafolio cultura

Galeria navegable a oscuras (las piezas dan la luz): pasillo del telar
(4 piezas curadas colgadas como runners), ROTONDA-ZOOTROPO cauce (el
visitante entra al centro de un tambor giratorio con el poema-loop en
letras grandes; modo estrobo con 24 ranuras fijas anima la enye por fases,
zootropo real), sala ecosistema (esporas exhumables del dataset --demo),
alcoba tilde (caja de luz vacia + pares minimos, corpus en acumulacion) y
muro final con marcos vacios (psicosis / precursor, por empezar).

Tecnica: hibrido Three.js r149 (WebGL: espacio, niebla, halos, tambor) +
CSS3DRenderer (las piezas SVG viven como DOM, su animacion SMIL sigue
VIVA en 3D, nada es captura). Todo inline: la salida es un solo .html
autocontenido apto para CSP estricta (artifact web).

## Build

```bash
py tools/compete_engine.py --demo     # dataset del ecosistema (si no existe)
node tools/sala3d/build.js            # -> tools/dist/sala3d.html
```

La primera corrida descarga three.js r149 pinneado de unpkg y lo cachea en
`tools/sala3d/.cache/` (gitignored). Las piezas se leen de
`projects/tapiz/piezas_curadas/` (versionadas; regenerarlas = comandos en su
README).

## Artifact publicado

https://claude.ai/code/artifact/af6411d3-c149-4c4a-8abf-3dcc20e53311
(favicon del tab: edificio clasico). Para actualizar EN LA MISMA URL desde
otra sesion Claude: publicar `tools/dist/sala3d.html` con el tool Artifact
pasando `url` = la URL de arriba.

## Reglas para mejorar la galeria

- Tema unico oscuro es decision de diseno (bioluminiscencia), no omision.
- Letras y botones GRANDES (pedido explicito del usuario 2026-07-11).
- Rotulos de sala citan los significados reales (MOTIF_CITATIONS de
  loom.py, CAUCE_CITATION de cauce.py); no inventar copy curatorial.
- CSP del artifact: cero requests externos; inline todo (fonts del sistema).
- Los limites del departamento cultura aplican: psicosis/precursor solo
  como marcos vacios + placa descriptiva; nada operativo.
