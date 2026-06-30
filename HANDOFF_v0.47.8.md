# HANDOFF v0.47.8 — Plano/Rider integrado desde repo web remoto

Fecha: 2026-06-30

## Base revisada

- Repo remoto clonado fresco desde `https://github.com/ligereza/vibecodeine`.
- HEAD remoto al iniciar: `a8ba2c8` (`checkpoint: v0.47.3 - plano rider disposition alignment legend`).
- Version remota detectada antes del cambio: `0.47.0`.
- Este airdrop integra los hotfixes pendientes sobre ese estado remoto y bumpea a `0.47.8`.

## Cambios principales

- Plano/Rider:
  - seleccionar elementos ya no cambia el orden de capas;
  - agrega prioridad base de capas: zonas/rectangulos abajo, simbolos tecnicos encima, entrada/top labels arriba;
  - agrega boton `Orden capas` en toolbar y `Ordenar capas base` en panel;
  - `Auto ordenar` aplica prioridad base y distribuye simbolos en grilla de 3 columnas;
  - zonas superpuestas usan `mixBlendMode: screen` + menor opacidad para evitar acumulacion oscura/opaca;
  - checklist y mapa sincronizan en ambos sentidos;
  - marcar requerimientos vuelve visible el simbolo existente o crea el `req-*` faltante;
  - ocultar/eliminar simbolos tecnicos actualiza checklist;
  - simbolos preservan color, posicion y tamano;
  - selector de color agrega colores extra para simbolos;
  - export Markdown ya no duplica la linea Evento;
  - render de simbolos en impresion queda sin handlers interactivos.

- PDF/impresion:
  - SVG imprimible usa `viewBox="0 0 2970 2400"`;
  - marco seguro visual queda en 2870x1800;
  - leyenda tecnica se mueve debajo del mapa y usa 4 columnas para no tapar posiciones;
  - titulo del plano queda debajo de la leyenda.

- Knowledge base:
  - agrega `docs/KNOWLEDGE_SCHEMA_OPERATIVO.md`;
  - extiende productoras `thegrid` y `creamfields` con relacion, trato, contacto, servicio preferente y branding;
  - extiende venue `espacio_riesco` con defaults operativos y servicio recomendado.

- Version:
  - `src/flujo/version.py` y `pyproject.toml` pasan a `0.47.8`.

## Revision realizada

- `npm run build:context` desde `web/`: OK.
- `python3 -m flujo verify`: OK.
- `scripts/validate_airdrop.py`: OK al empaquetar.
- Revision funcional por codigo sobre `web/src/components/PlanoTool.tsx`:
  - se verifico que `selectElementAndBringToFront` solo selecciona;
  - se verifico que `Orden capas` llama ordenamiento por prioridad;
  - se verifico que `autoArrangePlano` termina ordenando por prioridad;
  - se verifico que render de rectangulos usa mezcla `screen`;
  - se verifico que leyenda visible usa simbolos visibles reales;
  - se verifico que PDF/print renderiza con viewBox extendido y leyenda debajo.

## Limitacion honesta

No se pudo validar el dialogo real de imprimir/PDF de Windows desde este entorno. La estructura React/SVG y el build fueron revisados, pero el preview final de Chrome/Edge en Windows debe revisarlo el usuario.

## Aplicacion sugerida

Desde la raiz del repo local, despues de descomprimir el ZIP:

```bash
py scripts/run_airdrop_checks.py "v0.47.8 - plano rider integrated web repo review" --skip-push
```

Luego revisar: seleccion no reordena capas, boton Orden capas, mezcla de zonas solapadas, sync checklist/mapa y preview PDF.
