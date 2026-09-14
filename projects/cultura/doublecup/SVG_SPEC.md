# SVG_SPEC — doublecup_v2_3d.svg (espejo exacto del archivo)

Spec de continuación: todo lo que hay dentro del SVG, número por número.
Leer esto = poder editar el archivo sin ingeniería inversa.

## Identidad

- Archivo: `projects/cultura/doublecup/doublecup_v2_3d.svg` (~80 KB).
- Derivado de `arte-ascii-readme.svg` (v1, raíz del repo, SOLO LECTURA):
  material (texto) y máscara de forma copiados VERBATIM; talla nueva.
- `viewBox="0 0 676 904"`, `width/height="100%"` (escala al contenedor).
- Grilla: 72 filas × ~100 columnas; monospace `10px`; interlínea `dy=12`;
  origen del bloque `x=10 y=20`. Cada carácter ≈ 6px de ancho.

## Árbol del documento (orden exacto de pintado)

```
svg
├─ title            "double cup v2 -- parallax 3d"
├─ desc             (explicación para agentes; parte de la obra)
├─ defs
│   ├─ linearGradient #sheen   horizontal; stops: 0.45 (blanco a=0),
│   │                          0.50 (blanco a=0.16), 0.55 (blanco a=0)
│   └─ radialGradient #pozo    stops: 0 (#9333ea a=.9), 0.6 (#7e22ce a=.35),
│                              1 (#7e22ce a=0)
├─ style            (todo el CSS; abajo)
├─ rect.bg-rect     100%x100%, fill var(--canvas)  ← la "noche propia"
├─ ellipse.reflejo  cx=338 cy=866 rx=175 ry=12, fill url(#pozo)
└─ g.levitador
    ├─ g.capa.capa-fondo    > text (bloque COMPLETO, 72 tspan-línea)
    ├─ g.capa.capa-vidrio   > text (copia idéntica del bloque)
    └─ g.capa.capa-liquido  > text (copia idéntica del bloque)
└─ rect.brillo      676x904, fill url(#sheen)      ← barrido especular
```

Cada tspan-línea: `<tspan x="10" dy="12">` conteniendo tspans internos SIN
posición, solo clase: `<tspan class="b|g|l">texto</tspan>`. El `<text>` lleva
`xml:space="preserve"`; el CSS lleva `white-space: pre`. Ese par sostiene la
grilla — romperlo colapsa los espacios y destruye la silueta.

## Paleta (`:root`)

| var | valor | rol |
|---|---|---|
| `--canvas` | `#0b0a09` | fondo abisal propio |
| `--bg-text-color` | `#1e293b` | sustrato `.b` (con `opacity:.35`) |
| `--glass-color` | `#f8fafc` | vidrio `.g` |
| `--l1/--l2/--l3` | `#c084fc / #e879f9 / #9333ea` | ciclo del líquido `.l` |
| `--lh` | `#d8b4fe` | highlight del glow del líquido |

## Sistema de capas (cómo 3 copias no rompen la grilla)

Cada copia muestra SOLO su clase; las ajenas quedan invisibles pero SIGUEN
OCUPANDO sus celdas (layout por métricas de fuente, no por pintura):

```css
.capa-fondo .g, .capa-fondo .l,
.capa-vidrio .b, .capa-vidrio .l,
.capa-liquido .b, .capa-liquido .g { opacity:0; animation:none; text-shadow:none; }
```

## Tabla de animaciones (todas las que existen en el archivo)

| keyframes | objetivo | propiedad | dur | timing | extremos |
|---|---|---|---|---|---|
| `levitate` | `.levitador` | translateY | 6s | ease-in-out infinite both | 0 → -8px → 0 |
| `orb-f` | `.capa-fondo` | perspective(900px) rotateY/rotateX | 14s | alternate both | -4°/+1° → +4°/-1° |
| `orb-v` | `.capa-vidrio` | idem | 14s | alternate both | -7°/+1.5° → +7°/-1.5° |
| `orb-l` | `.capa-liquido` | idem | 14s | alternate both | -9°/+2° → +9°/-2° |
| `glass-shine` | `.capa-vidrio .g` | opacity + text-shadow | 4s | alternate | .7/1px → 1/5px blanco |
| `liquid-pulse` | `.capa-liquido .l` | fill + text-shadow | 3s | alternate | l1 → l2(glow 8px lh) → l3 |
| `reflejo` | `.reflejo` | scaleX + opacity | 6s | ease-in-out both | 1/.55 → .82/.3 → 1/.55 |
| `sweep` | `.brillo` | translateX + skewX(-12°) | 9s | ease-in-out both | -700px → +700px |

Detalles no negociables ya cableados:

- `transform-box: fill-box; transform-origin: center;` en TODO elemento con
  transform (`.levitador`, `.capa`, `.reflejo`). Sin fill-box el origen es la
  esquina del viewBox y la rotación expulsa el contenido del cuadro.
- Dos animaciones de transform NUNCA en el mismo elemento → por eso levitación
  (padre) y rotación (hijas) viven en grupos anidados.
- `reflejo` está en contrafase con `levitate` POR CONSTRUCCIÓN: misma duración
  (6s) y keyframes espejados (vaso arriba = reflejo chico y tenue).
- `.capa-fondo` lleva además `filter: blur(.35px)` (perspectiva atmosférica).
- `.reflejo` y `.brillo` usan `mix-blend-mode: screen` (solo aclaran, no pueden
  borrar texto). `.brillo` lleva `pointer-events: none`.
- Períodos 6/9/14s: conmensurables pero distintos → el estado global casi nunca
  se repite de forma visible.
- Última regla del CSS: `@media (prefers-reduced-motion: reduce) { * {
  animation: none !important; } }` — cortesía real, PERO el headless nuevo de
  Chromium matchea `reduce` por defecto: para screenshots de prueba, quitarla
  en una COPIA (nunca del archivo).

## Perillas de ajuste (dónde tocar qué)

- Intensidad 3D: los grados en `orb-f/v/l` (mantener fondo < vidrio < líquido;
  el diferencial ES el parallax) y `perspective(900px)` (menor = más agresivo;
  <500px deforma el texto).
- Velocidad global: las duraciones 6/9/14 — conservar la no-coincidencia.
- Glow: los `text-shadow` en `glass-shine`/`liquid-pulse` (Chromium-only;
  Firefox los ignora — la obra degrada a color plano, aceptado).
- Reflejo: posición `cx/cy/rx/ry` de la ellipse; intensidad en los stops de
  `#pozo`; difusión en `filter: blur(8px)`.
- Sheen: casi invisible a propósito (`stop-opacity 0.16`); la diagonal es el
  `skewX(-12deg)` DENTRO de los keyframes `sweep`.

## Verificación pendiente (Ω11 del archivo)

Pierde si, abierto en navegador real, las 3 capas no muestran movimiento
diferencial (parallax) — o si el vaso no se reconoce sobre fondo blanco.

Estado de evidencia: transforms 3D ESTÁTICOS probados OK en SVG (Chromium);
transforms ANIMADOS jamás cruzaron a una captura headless (falso negativo de
compositor — no prueba fallo). Falta 1 doble click humano.

## Fallback diseñado (si el navegador real NO anima 3D en SVG)

Reemplazar SOLO los tres bloques `orb-*` por parallax 2D — drop-in:

```css
@keyframes orb-f { 0%{transform:translateX(-2px)} 100%{transform:translateX(2px)} }
@keyframes orb-v { 0%{transform:translateX(-5px) scaleX(.997)} 100%{transform:translateX(5px) scaleX(.997)} }
@keyframes orb-l { 0%{transform:translateX(-8px)} 100%{transform:translateX(8px)} }
```

Mismos selectores, mismas duraciones 14s alternate both. El diferencial
(2/5/8px) conserva la ilusión de profundidad; todo 2D, soporte universal.

## Re-tejer con texto nuevo (material vigente)

`telar_vaso.py` genera el bloque desde cualquier texto usando la máscara de v1
(72 filas, 621 runs; digestión: vidrio/líquido pierden espacios):

```bash
py projects/cultura/doublecup/telar_vaso.py --v1 arte-ascii-readme.svg \
   --texto README.md --salida bloque_nuevo.svg
```

Hoy emite talla v1 (una capa). Para montarlo en ESTA talla 3D: tomar sus 72
`<tspan x="10" dy="12">…</tspan>` y pegarlos idénticos dentro de los TRES
`<text>` de este archivo. La estructura de arriba no cambia.

## Contexto de despliegue (GitHub README)

Se monta con `<img src="..." width="936">`: CSS corre completo, JS no existe,
links inertes, `prefers-color-scheme` responde al OS del espectador (no al tema
de GitHub) — irrelevante aquí: este archivo no usa media query de color, viaja
con su propia noche.
