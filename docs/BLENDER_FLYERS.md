# Notas: flujos de flyers y Blender (para automatizar más adelante)

> Documento de captura. Describe el proceso REAL del dueño para no perder el
> contexto cuando se aborde la automatización de Blender / Photoshop droplets.
> **Aún no implementado.** Es la base para un futuro airdrop.

## Tipos de flyer que maneja la ONG (al 2026-06-18)

Hay **dos** tipos de flyer, con destinos distintos:

### 1. Flyer para imprimir
- Medida: **14 × 10 cm**.
- Formato ya en el catálogo: `flyer_horizontal_minimo` (2800 × 2000 px).
- Pieza vectorial → flujo SVG actual (`flujo render`). Aquí no entra Blender.

### 2. Cartelera para historias de Instagram (digital)
- Usa la **foto descargada de Instagram** (vía `instaloader`) como base.
- La foto se **enmarca en Blender** para crear la cartelera (mockup/encuadre 3D
  o composición). Salida digital, vertical (formato historia).
- Hay **dos variantes = dos proyectos de Photoshop distintos**:
  - **Individual** (un solo evento): **ya tiene** un *droplet* de Photoshop que
    reemplaza la imagen y exporta automáticamente.
  - **Triple** (cartelera con tres eventos): **todavía NO** tiene droplet; es el
    pendiente.

## Estado de automatización

| Pieza | Herramienta | Estado |
|---|---|---|
| Flyer impresión 14×10 | SVG (`flujo render`) | ✅ cubierto por el flujo vectorial |
| Cartelera IG individual | Blender (encuadre) + PS droplet | ✅ droplet existente (reemplaza + exporta) |
| Cartelera IG triple | Blender + PS | ❌ pendiente (sin droplet) |

## Ideas para automatizar (a discutir con el dueño)

1. **Cartelera IG triple — droplet PS:** replicar la lógica del droplet
   individual pero con 3 smart objects (un evento por slot). Reusa el patrón de
   `src/flujo/templates/compose.jsx` (coloca imagen como Smart Object).
2. **Blender headless:** el enmarcado podría correr por
   `blender --background --python script.py` recibiendo la(s) foto(s) y
   exportando el render, sin abrir la UI. Requiere fijar la escena `.blend`
   plantilla y los nombres de los objetos imagen.
3. **Encadenar con el intake:** un pedido de cartelera (JSON o links IG) →
   descarga IG (avisando si la 1ª del carrusel es video o el perfil es privado,
   ya detectado por `intake/email_parser.py`) → Blender enmarca → PS droplet
   exporta. Todo orquestado por un comando `flujo cartelera`.

## Avisos ya disponibles (reutilizar)
`src/flujo/intake/email_parser.py` ya detecta:
- `detect_private_account()` → perfil privado / requiere login.
- `detect_video_in_carousel()` → la primera del carrusel es video.
- `generate_warnings()` → arma los ⚠️ para mostrar en UI.

> **Decisión pendiente del dueño:** alcance exacto y si se prioriza el droplet
> triple o el pipeline Blender headless. Mientras tanto, esto queda registrado.
