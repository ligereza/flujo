# AIRDROP 2026-06-18 — flujo v0.24.0 — Fix crítico del sistema Airdrop

**Fecha:** 2026-06-18
**Versión objetivo:** 0.24.0
**Tipo:** Fix crítico (sin breaking changes en la API pública)

---

## TL;DR

El comando `flujo airdrop` (list / dry-run / apply) **estaba roto**: `cli.py`
llamaba a una API que `airdrop.py` ya no tenía. Este airdrop lo repara,
sincroniza la versión (estaba en 3 valores distintos) y agrega tests de
regresión + un script de limpieza seguro.

> 👉 Para el contexto completo y el handoff, lee **`HANDOFF_2026-06-18.md`**.

---

## Archivos incluidos

```
_airdrop/
├── HANDOFF_2026-06-18.md          # contexto completo para la próxima IA (LEER)
├── README_AIRDROP.md             # este archivo
├── pyproject.toml                # versión 0.16.0 → 0.24.0
├── src/flujo/
│   ├── cli.py                    # FIX: comandos airdrop + versión dinámica en --help
│   └── version.py                # 0.24.0 + changelog
├── tests/
│   └── test_airdrop.py           # NUEVO: 9 tests de regresión del airdrop
└── scripts/
    └── cleanup_safe.sh           # NUEVO: limpieza reversible de scripts legacy
```

## Aplicar

```bash
# Opción A — con la CLI (este fix la repara):
flujo airdrop apply "v0.24 - fix airdrop cli + version sync"

# Opción B — flujo manual (siempre funciona):
bash scripts/apply_airdrop.sh --dry-run
bash scripts/apply_airdrop.sh --apply

# Después, en ambos casos:
py -m pip install -e .
flujo version            # 0.24.0
flujo airdrop list       # ya no lanza ImportError
py -m pytest tests/ -q   # 69 passed, 1 skipped
```

## Limpieza opcional de legacy

```bash
bash scripts/cleanup_safe.sh           # dry-run
bash scripts/cleanup_safe.sh --apply   # archiva 10 scripts huérfanos en _archive/
```

## Compatibilidad

- **Sin breaking changes**: la firma pública de `airdrop.py` no cambió.
- **Dependencias**: ninguna nueva.
- **Python**: 3.10+ (sin cambios).
