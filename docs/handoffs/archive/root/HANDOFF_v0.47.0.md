# HANDOFF v0.47.0 - QA operativo Eventos/Suplementos

## Key Changes

- Added EVENTOS preflight command: `py -m flujo plano <evento.json> --validate`. It checks required fields, numeric ranges, supported layout modes, testeo requirements, massive event containment zone, table counts and calculated dimensions before rider/plano export.
- Expanded Plano/Rider technical symbols: every one of the 17 checklist requirements now maps to a real procedural SVG symbol, plus core testeo/contencion symbols.
- Fixed checklist sync: checking/unchecking individual items, "Marcar todo" and "Ir al Plano" now consistently add/remove requirement symbols.
- Made screen and print/PDF technical legends dynamic so they list the actual visible symbols instead of a hardcoded incomplete subset.
- Rebuilt `context/flujo_hub.html`, `context/plano_demo.html` and `context/svg_visualizer.html` from React.
- Added SUPLEMENTOS SVG preflight command: `py -m flujo suplementos validate <svg...>`. It detects invalid SVG/XML, unexpected contraportada size (`1181x1654 px`), unreplaced placeholders and missing editable text/group structure.
- Added `docs/QA_EVENTOS_SUPLEMENTOS.md` with Windows-first commands for rider/plano and supplement SVG QA.
- Added tests for plano validation and supplement SVG validation.
- Bumped system version to 0.47.0 in `src/flujo/version.py` and `pyproject.toml`.

## Apply / Verify

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "v0.47.0 - qa eventos suplementos"
py -m flujo verify
py -m flujo plano projects/plano/ejemplos/evento_ejemplo.json --validate
cd web && npm run build:context && cd ..
py -m flujo suplementos contraportada "Impulso" --output exports/qa_impulso.svg
py -m flujo suplementos validate exports/qa_impulso.svg
```

## Notes

- This is mechanical preflight, not a replacement for final visual QA in Illustrator/browser.
- Handoffs remain ASCII-safe except existing repo docs that already include accents.
