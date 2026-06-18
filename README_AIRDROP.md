# AIRDROP 2026-06-18 — flujo v0.30.0 — Auto-fit de texto + avisos IG + acuse de recibo

**Tipo:** Features (3). Con tests. Retrocompatible. Mantiene SVG puro (sin `image`).

## TL;DR
- **Auto-fit de texto:** el texto encoge para caber en la caja ("misma medida,
  distinto texto"); respeta campos `locked` (datos exactos) y `min_size`.
- **Pestaña INSTAGRAM** en el editor: avisos de perfil privado / video / sin links.
- **Pestaña ACUSE DE RECIBO:** correo prellenado (mailto/Gmail) con folio + resumen.

👉 Contexto completo: **`HANDOFF_2026-06-18_autofit.md`**.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_autofit.md
├── README_AIRDROP.md
├── pyproject.toml                         # 0.29.0 → 0.30.0
├── src/flujo/
│   ├── version.py                         # 0.30.0 + changelog
│   ├── render/autofit.py                  # NUEVO (motor de auto-fit)
│   └── web/
│       ├── svg_preview.py                 # autofit en preview
│       └── editor.py                      # pestañas IG + acuse + checkbox autofit
├── tools/piezas_vectoriales/scripts/
│   └── generar_desde_json.py             # autofit en el generador oficial
├── tests/
│   ├── test_autofit.py                    # 11 tests (NUEVO)
│   └── test_web_features.py              # 13 tests (NUEVO)
└── docs/
    └── AUTOFIT.md                         # NUEVO
```

## Aplicar
```bash
flujo airdrop apply "v0.30.0 - autofit + avisos IG + acuse de recibo"
py -m pip install -e .
flujo version            # 0.30.0
flujo serve              # 3 pestañas: EDITOR / INSTAGRAM / ACUSE DE RECIBO
py -m pytest tests/ -q   # 144 passed, 1 skipped
```

## Compatibilidad
- Retrocompatible: el autofit solo actúa si el elemento tiene `autofit: true`.
- Sin dependencias nuevas (gradio/matplotlib ya estaban).
