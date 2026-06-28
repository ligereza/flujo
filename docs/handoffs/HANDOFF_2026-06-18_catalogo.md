# 🤝 Handoff 2026-06-18 — flujo v0.27.0 — Catálogo oficial de formatos (v2.0)

## Por qué este airdrop

El dueño entregó el mapa real de formatos que produce la ONG, dividido en dos
áreas (**Eventos** = info por correo, **Suplementos** = info por whatsapp). Lo
convertí en el **catálogo oficial** del sistema, con metadata que antes no
existía: **área, medio (impresión/digital) y herramienta (Illustrator/
Photoshop/Blender)** — operacionalizando la regla del dueño:

> **Illustrator = impresión real · Photoshop = digital · Blender = recursos
> (frasco de suplementos) y export de carteleras.**

## Qué incluye

| Archivo | Cambio |
|---|---|
| `tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json` | **Reescrito a schema v2.0.** 12 formatos reales con `area`, `medio`, `herramienta`, `parametrico`, `inferir`, `origen_info`. Los 6 viejos siguen (renombrados con prefijo `evt_`/`sup_` y conservando sus plantillas). |
| `src/flujo/render/formats.py` | `FormatInfo` extendido con la metadata nueva (retrocompatible); `load_index` la carga y tolera `template:null` y `canvas:0`; `list_formats(area, medio, herramienta)` con filtros; `__str__` no rompe con paramétricos; prop `has_template`. |
| `src/flujo/cli.py` | `flujo render formats` ahora acepta `-a/--area`, `-m/--medio`, `--herramienta`. |
| `tests/test_formats_catalogo.py` | **NUEVO.** 13 tests: existencia de formatos, metadata, filtros, regla impresión=Illustrator/digital≠Illustrator, paramétricos. |
| `schemas/intake.schema.json` | `pedido.area` (eventos/suplementos/comun) + `tipo_pieza` ampliado (cartelera, post, historia, brief, bandera). |
| `schemas/ejemplos/cartelera_evento.json`, `pendon_suplemento.json` | **NUEVOS** ejemplos. |
| `docs/CATALOGO_FORMATOS.md` | **NUEVO.** Catálogo explicado por área/medio/herramienta + gran formato + inferencia IG. |
| `docs/INTAKE_JSON.md`, `README.md`, `version.py`, `pyproject.toml` | Referencias + versión 0.27.0. |

## Medidas confirmadas con el dueño (importante)

- Cartelera digital: **1080×1920** (vertical 9:16).
- Post IG: **1080×1350** (vertical 4:5).
- Flyer físico evento: **10×14 cm** (vertical) — distinto del flyer 14×10
  horizontal que ya existía (ahora `sup_etiqueta_140x100` / etiquetas).
- Pendones/banderas: **paramétricos** (medida real por pedido). El dueño pidió
  separar **rectangular** (pendón/roller) y **poligonal** (bandera/stand).

## Inferencia desde Instagram (carteleras) — documentado, NO implementado

Las carteleras deben inferir `productora` (≈ @usuario de la imagen), `fecha`,
`venue` y `logo` (solo en la triple). El dueño aclaró que es **menos urgente**
(las productoras se repiten; la triple es poco frecuente). Los avisos de IG
(video en 1ª del carrusel / perfil privado) **ya existen** en
`src/flujo/intake/email_parser.py`. La cartelera **triple** aún no tiene droplet
de Photoshop (pendiente). Todo registrado en `docs/BLENDER_FLYERS.md`.

## Verificación hecha

```
✅ JSON del catálogo válido; 12 formatos cargan
✅ flujo render formats / -a / -m / --herramienta  → OK
✅ filtro impresion ⇒ todos llevan illustrator; digital ⇒ ninguno
✅ pytest tests/ → 99 passed, 1 skipped (eran 86; +13)
✅ compileall src/ → OK
✅ JSON Schema válido + 6 ejemplos validan + cartelera/pendón nuevos OK
```

## Cómo aplicar

```bash
flujo airdrop apply "v0.27.0 - catalogo oficial de formatos"
# o:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.27.0 - catalogo oficial de formatos"

py -m pip install -e .
flujo version                 # 0.27.0
flujo render formats          # 12 formatos
py -m pytest tests/ -q        # 99 passed, 1 skipped
```

## Próximos pasos sugeridos (para la siguiente IA)

1. **Plantillas `config.json` faltantes** para los formatos nuevos con
   `template:null` (cartelera, post, historia). Hoy existen en el catálogo pero
   sin plantilla base; al crear proyecto caen al generador proporcional.
2. **Editor Gradio** que cargue el catálogo (filtrable por área), muestre
   avisos de IG, y use `render rescale` como backend del slider proporción/DPI.
3. **Inferencia IG** (productora/fecha/venue/logo) para carteleras.
4. **Droplet triple** + pipeline Blender headless (ver `docs/BLENDER_FLYERS.md`).
5. **Motor de layout tipo CSS + auto-fit de texto** ("misma medida, distinto
   texto") + elemento `image` en el generador SVG.
