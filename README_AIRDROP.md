# AIRDROP 2026-06-18 — flujo v0.25.0 — README maestro + Intake JSON

**Tipo:** Documentación + contrato de datos (sin cambios de lógica ejecutable).

## TL;DR
Reescribe el `README.md` como guía definitiva para que cualquier IA sepa cómo
trabajar aquí (sobre todo el sistema de airdrops/ZIPs), y establece la
**estructura JSON** con la que los colegas entregarán pedidos por formato.

👉 Contexto completo: **`HANDOFF_2026-06-18_docs.md`**.

## Archivos
```
_airdrop/
├── HANDOFF_2026-06-18_docs.md      # contexto para la próxima IA (LEER)
├── README_AIRDROP.md              # este archivo
├── README.md                      # guía maestra reescrita
├── PARA_IA_CONTEXT.md             # handover corto v0.25.0
├── pyproject.toml                 # 0.24.1 → 0.25.0
├── src/flujo/version.py           # 0.25.0 + changelog
├── docs/INTAKE_JSON.md            # spec de intake por JSON
└── schemas/
    ├── intake.schema.json         # JSON Schema draft-07 (validable)
    └── ejemplos/
        ├── etiqueta_miel.json
        ├── flyer_evento.json
        └── carrusel_ig.json
```

## Aplicar
```bash
flujo airdrop apply "v0.25.0 - README maestro + intake JSON"
# o manual:
bash scripts/apply_airdrop.sh --apply
bash scripts/checkpoint.sh "v0.25.0 - README maestro + intake JSON"

py -m pip install -e .      # para refrescar la versión
flujo version               # 0.25.0
py -m pytest tests/ -q      # 69 passed, 1 skipped
```

## Compatibilidad
- Sin breaking changes. No agrega dependencias en runtime.
- `jsonschema` solo se necesita si más adelante se valida el JSON en código (no
  requerido por este airdrop).
