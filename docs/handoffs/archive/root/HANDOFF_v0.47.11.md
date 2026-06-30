# HANDOFF v0.47.11 — Hotfix PDF Plano/Rider ventana aislada

Fecha: 2026-06-30

## Motivo

El usuario reporto que el hotfix v0.47.10 rompio mas el PDF: el plano ya ni se veia. Se reemplazo el enfoque de imprimir el DOM React/Tailwind por una ventana HTML aislada y controlada.

## Cambio principal

- `printRider()` ya no llama directo a `window.print()` sobre la app.
- Ahora construye un HTML completo en una ventana nueva con CSS minimo y controlado.
- El HTML tiene 3 paginas A4 horizontal:
  1. antecedentes + checklist;
  2. plano/mapa;
  3. tabla de detalle.
- El plano se genera como SVG autonomo dentro del HTML imprimible, usando posiciones actuales de `elements`.
- Para evitar que desaparezcan iconos por dependencias React, los simbolos de impresion usan circulos y texto tecnico corto, no componentes React.
- Si el navegador bloquea popup, descarga un `.html` imprimible como fallback.

## Se conserva

- Fix de SVG Studio v0.47.10:
  - carga contenido real de `/svg/...`;
  - fallback `svgUrl`;
  - boton `Actualizar repo`;
  - boton `Carpeta local`.

## Revision

- `cd web && npm run typecheck`: OK.
- `cd web && npm run build:context`: OK.
- `python3 -m flujo verify`: OK.
- `scripts/validate_airdrop.py`: OK al empaquetar.

## Limitacion

No puedo abrir el dialogo real de PDF de Windows desde este entorno. Esta vez el mapa no depende del DOM de la app ni de Tailwind print; se genera en un documento aislado para reducir el riesgo de recorte/desaparicion.

## Comando sugerido

```bash
py scripts/run_airdrop_checks.py "v0.47.11 - hotfix isolated plano rider pdf" --skip-push
```
