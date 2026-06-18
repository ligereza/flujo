# AIRDROP 2026-06-18 — flujo v0.29.0 — Fix auto-checkpoint (Windows/bash)

**Tipo:** Fix crítico. Con tests. Sin breaking changes.

## TL;DR
Arregla el error `execvpe(/bin/bash) failed` que impedía que
`flujo airdrop apply` hiciera el push automático en Windows. Ahora el
auto-checkpoint usa **git directo (Python puro), sin bash**.

👉 Contexto completo: **`HANDOFF_2026-06-18_fix_checkpoint.md`**.

> Importante: este apply también empuja el **editor 0.28.0** que quedó local sin
> pushear (el push había fallado por este mismo bug). Un solo apply deja el
> remoto en 0.29.0 con el editor incluido.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_fix_checkpoint.md
├── README_AIRDROP.md
├── pyproject.toml                       # 0.27.0 → 0.29.0
├── src/flujo/
│   ├── version.py                       # 0.29.0 + changelog
│   └── airdrop.py                       # run_auto_checkpoint en Python puro
└── tests/
    └── test_airdrop_checkpoint.py       # 4 tests (NUEVO)
```

## Aplicar
```bash
flujo airdrop apply "v0.29.0 - fix auto-checkpoint sin bash"
py -m pip install -e .
flujo version            # 0.29.0
py -m pytest tests/ -q   # 103 passed, 1 skipped
```

Debería terminar con `✓ Checkpoint creado y cambios subidos al servidor.`
(sin el error de WSL/bash).

## Compatibilidad
- Funciona en Windows / Linux / macOS (no usa bash).
- `scripts/checkpoint.sh` sigue para uso manual; el airdrop ya no lo necesita.
