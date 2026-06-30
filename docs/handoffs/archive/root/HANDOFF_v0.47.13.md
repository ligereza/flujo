# HANDOFF v0.47.13 — Rider PDF alineado al editor + SVG Studio configurable real

Fecha: 2026-06-30

## Motivo

El usuario reporto problemas de direccion en v0.47.12:
- PDF del rider cambio demasiado el formato, se veia demasiado horizontal.
- La leyenda ya no correspondia al recuadro movible del editor.
- La leyenda no tenia iconos reales.
- El Config Editor seguia en demos y no cargaba realmente el SVG seleccionado.

## Cambios

### Plano/Rider PDF

- Se mantiene impresion directa por iframe oculto, sin descarga HTML.
- Se elimino el doble disparo de impresion dentro del HTML.
- Formato vuelve a A4 natural, no horizontal extremo.
- El mapa imprimible vuelve a `viewBox 2970x2100`, alineado al editor.
- La leyenda del PDF usa la posicion real `legendPos` del recuadro del editor.
- La leyenda recupera iconos tecnicos SVG simplificados por tipo, con color de cada simbolo.
- Zonas y simbolos preservan color.

### SVG Studio / Config Editor

- El boton **Configurar este SVG** ahora pasa estado directamente al editor, sin depender de evento global ambiguo.
- Config Editor acepta `pieceToLoad` y carga ese SVG como documento base.
- Config Editor tiene selector **SVGs repo** que lista SVGs reales cargables, no solo demos.
- Config Editor tiene boton **SVG local** para cargar un `.svg` directamente.
- Se agrego tipo `svg_image` para renderizar el SVG elegido dentro del canvas de configuracion.

## Revision

- `cd web && npm run typecheck`: OK.
- `cd web && npm run build:context`: OK.
- `python3 -m flujo verify`: OK.
- `scripts/validate_airdrop.py`: OK al empaquetar.

## Comando sugerido

```bash
py scripts/run_airdrop_checks.py "v0.47.13 - rider pdf editor legend and svg studio real config" --skip-push
```
