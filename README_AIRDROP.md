# AIRDROP 2026-06-18 — flujo v0.28.0 — Editor visual Gradio

**Tipo:** Feature (módulo nuevo `src/flujo/web/` + editor). Con tests. Retrocompatible.

## TL;DR
Primer editor visual funcional: `flujo serve` abre un editor en el navegador para
elegir formato del catálogo, editar datos y proporción/DPI, ver **preview SVG en
vivo** y **exportar SVG + config**. Reemplaza al `scripts/app.py` legacy
(disponible con `--legacy`).

👉 Contexto completo: **`HANDOFF_2026-06-18_editor.md`**.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_editor.md
├── README_AIRDROP.md
├── README.md                          # sección app + v0.28.0
├── pyproject.toml                     # 0.27.0 → 0.28.0
├── src/flujo/
│   ├── version.py                     # 0.28.0 + changelog
│   ├── cli.py                         # serve usa editor nuevo (--port/--host/--legacy)
│   └── web/
│       ├── __init__.py                # NUEVO
│       ├── svg_preview.py             # NUEVO (preview SVG sin deps)
│       └── editor.py                  # NUEVO (lógica pura + UI Gradio)
├── tests/
│   └── test_web_editor.py            # 17 tests (NUEVO)
└── docs/
    └── EDITOR_WEB.md                  # NUEVO
```

## Aplicar
```bash
flujo airdrop apply "v0.28.0 - editor visual gradio"
# o manual:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.28.0 - editor visual gradio"

py -m pip install -e .
flujo version            # 0.28.0
flujo serve              # http://127.0.0.1:7860
py -m pytest tests/ -q   # 116 passed, 1 skipped
```

## Compatibilidad
- Gradio 6.x (probado con 6.19). No agrega dependencias (gradio ya estaba).
- El script legacy `scripts/app.py` sigue disponible con `flujo serve --legacy`.
