# AIRDROP 2026-06-18 — flujo v0.31.0 — Proyecto satélite `plano`

**Tipo:** Proyecto nuevo "por desarrollar" (estilo `tapiz`). No toca el core.

## TL;DR
Agrega `projects/plano/`: un generador paramétrico de planos de stands para
eventos por **constantes de realidad** (sin AutoCAD), con rider derivado por
reglas. Incluye el generador radial de teatro original como referencia.

👉 Contexto: **`HANDOFF_2026-06-18_plano.md`** · Concepto: `projects/plano/README.md`.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_plano.md
├── README_AIRDROP.md
├── pyproject.toml                          # 0.30.2 → 0.31.0
├── src/flujo/version.py                     # 0.31.0 + changelog
└── projects/plano/
    ├── README.md
    ├── feedback.md
    ├── plano_stands.py                      # motor headless (prototipo)
    ├── referencia_plano_teatro.py           # generador radial original (referencia)
    └── ejemplos/evento_ejemplo.json
```

## Aplicar
```bash
flujo airdrop apply "v0.31.0 - proyecto plano (por desarrollar)"
py -m pip install -e .
flujo version            # 0.31.0
cd projects/plano && python plano_stands.py ejemplos/evento_ejemplo.json --rider
py -m pytest tests/ -q
```

## Compatibilidad
- No modifica nada del core. `plano_stands.py` es headless (stdlib).
- `referencia_plano_teatro.py` requiere customtkinter (solo si lo ejecutás; es referencia).
