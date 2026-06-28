# Feedback — proyecto `plano`

> Notas de dirección para seguir desarrollando este proyecto satélite.
> Estado actual: **prototipo funcional headless** (`plano_stands.py`) + base de
> referencia radial (`referencia_plano_teatro.py`). Falta editor visual y afinar
> constantes con medidas reales.

## Lo que ya funciona (v0 prototipo)
- **Constantes de realidad** (`CONSTANTES`): mesa, silla, toldos 3×3/3×4.5/6×3, pasillo.
- **Reglas operativas** (`reglas_rider`): >4h colación, >5h alimentación,
  +1 mesa por cada 5 voluntarios, testeo → +stand, masivo → zona contención.
- **Layout** (`solve_layout`): coloca stands en fila con pasillo; mesas y sillas
  dentro de cada stand (n.º sillas ≈ n.º voluntarios).
- **Render SVG** a escala (1 m = N px) + **rider de texto** derivado por reglas.
- Probado con `ejemplos/evento_ejemplo.json` (6h, 7 voluntarios, masivo, testeo).

## Qué refinar (próxima IA / dueño)

### 1. Constantes reales
Confirmar con el dueño las medidas reales: tamaño de toldos que usa RD, mesas
(¿2,0×0,7?), sillas, ancho de pasillo exigido por producción. Hoy son supuestos
razonables.

### 2. Reglas operativas completas
Pasar TODAS las reglas del brief a `REGLAS` (hoy hay 5). Ej.: ratio
voluntarios/asistentes, n.º de test por aforo, requerimiento eléctrico por stand,
agua/insumos por hora, etc. Idealmente las reglas viven en el JSON (editables sin
tocar código).

### 3. Layout más realista
- Posicionar respecto a **escenario / accesos / baños / zona médica** (no solo
  fila). Reusar la idea radial de `referencia_plano_teatro.py` cuando aplique.
- Evitar solapamientos con un solver simple (grid o packing).
- Cotas/medidas dibujadas (estilo plano arquitectónico).

### 4. Editor visual (estilo flujo)
Un `plano_editor.html` autocontenido (como los editores de flujo): sliders para
duración/voluntarios/asistentes/testeo → recalcula plano + rider en vivo →
exporta SVG/PDF en **PC horizontal** y **móvil vertical** (mismo requisito del
brief para productoras).

### 5. Integración
- Conectar con `data_brief_intervencion_terreno.json`: el plano + rider se
  insertan como página(s) del brief (read-only para productoras).
- A futuro: comando `flujo plano <evento.json>`.

### 6. Costos (ala de cotización)
El dueño pidió recordar que **la cotización aumenta con cada cambio**. El plano
podría emitir también un **desglose de costos** derivado de las mismas reglas
(personal × horas, testeo sí/no, alimentación si >5h, etc.). Ver pendiente de
cotización en `backlog_suplementos.md`.

## Nota sobre `referencia_plano_teatro.py`
Es el generador original del dueño (teatro SCD Plaza Egaña): GUI customtkinter +
matplotlib, geometría **radial** con fórmula de la sagita
`radio = (sagita² + (ancho/2)²) / (2·sagita)`, bloques de butacas con alineación
radial y balcón. Requiere `customtkinter` (no es headless). Se conserva como
**referencia matemática**; el motor nuevo (`plano_stands.py`) es headless y
generaliza el enfoque a stands.
