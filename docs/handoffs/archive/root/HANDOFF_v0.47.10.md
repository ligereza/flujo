# HANDOFF v0.47.10 — Fix SVG previews reales + PDF Plano/Rider multipagina

Fecha: 2026-06-30

## Base

- El usuario indico que no hizo push de v0.47.9.
- Se trabajo sobre el clon local `repo_after_push` que ya contiene la integracion v0.47.9 pendiente.
- Este airdrop reemplaza el anterior pendiente: usar solo v0.47.10.

## Errores corregidos

### SVG Studio

Problema observado/reportado:
- En SVG Studio las tarjetas mostraban icono de documento porque la API entrega `path` hacia archivos SVG reales, pero el frontend solo renderizaba `svgContent` inline.

Correccion:
- `web/src/data/svgIndex.ts` ahora, al cargar `/api/list-svg-works`, toma `item.path`, hace `fetch('/' + path)` y guarda el contenido real en `svgContent`.
- Si el fetch falla, guarda `svgUrl` y la UI usa `<img>` como fallback.
- `SvgVisualizer.tsx` ahora renderiza `svgContent` o `svgUrl`, evitando el icono generico cuando existen SVGs reales.
- Se agrego boton **Actualizar repo** para refrescar `/api/list-svg-works`.
- Se agrego boton **Carpeta local** para seleccionar una carpeta/varios `.svg` desde el navegador y previsualizarlos sin depender de la API.

### Plano/Rider PDF

Problema observado/reportado:
- Export/impresion PDF generaba una sola hoja, se recortaba y no respetaba bien el contenido.

Correccion:
- Se reorganizo el print markup en paginas explicitas:
  1. portada + antecedentes + checklist;
  2. mapa/plano;
  3. detalle de elementos.
- `web/src/index.css` agrega reglas `@media print` con:
  - `@page { size: A4 landscape; margin: 8mm; }`;
  - `.rider-print-page` con `break-after: page`;
  - mapa con `max-height: 166mm` y `overflow: hidden` controlado para escalar dentro de la hoja.
- Se corrigio badge duplicado de version en Plano/Rider.

## Revision realizada

- `cd web && npm run typecheck`: OK.
- `cd web && npm run build:context`: OK.
- `python3 -m flujo verify`: OK.
- `scripts/validate_airdrop.py`: OK al empaquetar.
- Revision funcional por codigo:
  - `loadFromApi()` ahora convierte `groups`/`pieces`/`works` a piezas con `svgContent` real o `svgUrl` fallback.
  - `SvgVisualizer` tiene botones `Actualizar repo` y `Carpeta local`.
  - tarjetas, lista y modal renderizan SVG real o imagen fallback.
  - print de Plano/Rider usa paginas separadas y CSS de impresion.

## Limitacion honesta

No puedo validar el dialogo final de imprimir/PDF de Chrome/Edge en Windows desde este entorno. Lo que si se valido: compilacion, typecheck, verify, smoke del hub y estructura de CSS/markup para forzar paginas.

## Comando sugerido

```bash
py scripts/run_airdrop_checks.py "v0.47.10 - fix svg previews and plano rider pdf" --skip-push
```
