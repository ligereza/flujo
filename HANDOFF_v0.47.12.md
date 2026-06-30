# HANDOFF v0.47.12 — PDF directo con color + Galeria→Config SVG

Fecha: 2026-06-30

## Motivo

El usuario reporto que v0.47.11 no era aceptable: perdio color en el plano, no imprimia directo y descargaba HTML. Tambien pidio que desde la galeria SVG exista un boton para pasar el SVG abierto al area de configuracion.

## Cambios

### Plano/Rider PDF

- `Imprimir Rider` ya no descarga HTML ni abre ventana visible.
- Usa un `iframe` oculto y dispara `print()` directo, conservando flujo de impresion.
- El mapa imprimible recupera color:
  - zonas con `fill` del color del elemento y opacidad controlada;
  - simbolos con color propio en borde/texto/fondo suave.
- Mantiene layout aislado de 3 paginas para evitar recorte:
  1. antecedentes + checklist;
  2. mapa;
  3. detalle.

### SVG Studio

- En modal de galeria se agrega boton **Configurar este SVG**.
- Ese boton cambia al tab Config Editor y carga el SVG seleccionado como documento base.
- Config Editor ahora soporta elemento `svg_image` para mostrar el SVG importado dentro del canvas.
- Se mantienen:
  - `Actualizar repo`;
  - `Carpeta local`;
  - carga de SVGs reales desde `/svg/...`.

## Revision

- `cd web && npm run typecheck`: OK.
- `cd web && npm run build:context`: OK.
- `python3 -m flujo verify`: OK.
- `scripts/validate_airdrop.py`: OK al empaquetar.

## Nota honesta

No se pudo abrir el dialogo real de impresion de Windows desde este entorno. Se corrigio el flujo para que sea impresion directa por iframe y no descarga HTML.

## Comando sugerido

```bash
py scripts/run_airdrop_checks.py "v0.47.12 - direct color pdf and svg configure bridge" --skip-push
```
