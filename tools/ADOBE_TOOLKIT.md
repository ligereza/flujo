# Vibo Adobe Toolkit

Conjunto de herramientas de automatizacion para Adobe (Illustrator, Photoshop,
After Effects) + un panel CEP que las lanza con un clic.

## Herramientas (scripts .jsx)

| App | Script | Que hace |
|-----|--------|----------|
| Illustrator | `illustrator/scripts/titles_to_photos.jsx` | Bloque de texto -> exporta cada linea como PNG/JPG individual (conserva fuente/color). |
| Illustrator | `illustrator/scripts/logo_revector_extrude.jsx` | Logo JPEG de baja calidad -> vector (trazado) + extrusion 3D vectorial -> exporta vector (SVG/EPS/PDF) + PNG. |
| Illustrator | `illustrator/scripts/logo_revector_batch.jsx` | Lo mismo pero por LOTES: procesa una carpeta entera de imagenes de una vez. |
| Illustrator | `illustrator/scripts/logo_clean_master.jsx` | Limpieza de nodos/segmentos de un logo ya vectorizado (ya existente en el repo). |
| Photoshop | `photoshop/scripts/layers_to_photos.jsx` | Cada capa (o solo capas de texto) -> PNG individual recortado con transparencia. |
| After Effects | `after_effects/scripts/titles_to_comps.jsx` | Bloque de texto -> una composicion por titulo, centrada y con fundido. |
| After Effects | `after_effects/scripts/auto_titles_mixer_ae.jsx` | Igual, pero cada comp lleva ecualizador (Audio Spectrum) + el titulo que late con el volumen (reactivo al audio). |

## Como ejecutar un script suelto

- **Illustrator / Photoshop:** `Archivo > Secuencias de comandos > Explorar...`
  (File > Scripts > Browse/Other Script...) y elige el `.jsx`.
- **After Effects:** `Archivo > Secuencias de comandos > Ejecutar archivo...`
  (File > Scripts > Run Script File...).

Todos preguntan sus opciones al vuelo (formato, escala, carpeta de salida, etc.)
y no modifican tu documento original: exportan desde documentos/duplicados
temporales.

## Panel (addon) CEP

Un solo panel acoplable para las tres apps. Ver `tools/adobe_panel/README.md` para la
instalacion (activar PlayerDebugMode + copiar a la carpeta de extensiones CEP).
El panel muestra distintos botones segun la app activa y ejecuta los mismos
`.jsx` de arriba (fuente unica, sin duplicar).

## Diseno / decisiones

- **ExtendScript (.jsx)** como base: sin compilacion, corre en las tres apps y
  sigue el patron que ya usa el repo en `tools/illustrator/`.
- **CEP** para el panel: unica tecnologia que cubre AI + PS + AE con un solo
  bundle hoy. Se puede complementar con UXP mas adelante.
- **Extrusion 3D vectorial** (copias apiladas y oscurecidas) en vez de efectos
  vivos 3D fragiles/dependientes de version: exporta limpio a SVG y PNG. Para 3D
  foto-realista, aplicar `Efecto > 3D y materiales` manualmente sobre el vector.

## Regla de oro del repo

Illustrator local del usuario es el QA visual real. Estos scripts corren dentro
de tu Illustrator/Photoshop/AE, asi que la revision final la haces tu en la app.
