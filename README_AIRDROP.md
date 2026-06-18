# AIRDROP 2026-06-18 — flujo v0.26.0 — Render rescale + bloque `modificacion`

**Tipo:** Feature (comando nuevo + extensión del contrato JSON). Con tests.

## TL;DR
Responde a "¿y si me piden cambiar proporción o pixelado?": nuevo comando
`flujo render rescale` (DPI o medida cm) y bloque `modificacion` en el intake
JSON para recibir pedidos de cambio sobre piezas existentes.

👉 Contexto completo: **`HANDOFF_2026-06-18_rescale.md`**.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_rescale.md
├── README_AIRDROP.md
├── README.md                          # + comando rescale, v0.26.0
├── pyproject.toml                     # 0.25.0 → 0.26.0
├── src/flujo/
│   ├── version.py                     # 0.26.0 + changelog
│   ├── cli.py                         # comando 'render rescale'
│   └── render/rescale.py              # motor de reescalado (NUEVO)
├── tests/
│   └── test_render_rescale.py         # 17 tests (NUEVO)
├── docs/
│   ├── INTAKE_JSON.md                 # sección 3.7 modificacion + rescale
│   └── BLENDER_FLYERS.md              # notas del flujo de flyers/Blender (NUEVO)
└── schemas/
    ├── intake.schema.json             # + bloque modificacion
    └── ejemplos/modificacion_etiqueta.json   # NUEVO
```

## Aplicar
```bash
flujo airdrop apply "v0.26.0 - render rescale + modificacion"
# o manual:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.26.0 - render rescale + modificacion"

py -m pip install -e .
flujo version               # 0.26.0
py -m pytest tests/ -q      # 86 passed, 1 skipped
```

## Compatibilidad
- Sin breaking changes. No agrega dependencias en runtime (jsonschema solo si se
  valida el JSON en código, opcional).
