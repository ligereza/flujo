# Checkpoint — fix: rider requirements restore 17 items + icons + layer ordering + export - v0.43.3

Fecha: 2026-06-28_20-43

## Estado

# LAST_HANDOFF - flujo continuation state

IMPORTANT: This file is intentionally ASCII-only to avoid mojibake on Windows + Git Bash/cp1252.
Do not use accents, enye, emoji, smart quotes, or special arrows here.
Daily commands for owner on Windows/Git Bash must use `py`, not `python`.

Date: 2026-06-28
Current version: 0.43.3
Main daily entry: `py -m flujo app`
Desktop entry: `py -m flujo app --desktop`
Verify on Windows: `py -m flujo verify`
Airdrop check on Windows: `py scripts/validate_airdrop.py` then `py scripts/run_airdrop_checks.py "message"`

## Current state

The repo is healthy after the v0.40 hub airdrop, v0.41.0 unified React hub, v0.42.1 example ingest templates, and the new v0.43.3 release that restores and repairs the 17-item Rider Checklist with procedural Lucide icons (no emojis), persistent checkbox printing, layer reordering (bring to front on select), and checklist Markdown exports.

Real package CLI:
- `py -m flujo health`
- `py -m flujo doctor`
- `py -m flujo verify`
- `py -m flujo app`
- `py -m flujo hub serve --open`
- `py -m flujo hub index ...`
- `py -m flujo hub route ...`

## Recent completed work

### v0.43.3 - Rider requirements restore 17 items + icons + layer ordering + export
- Restored `web/src/components/PlanoTool.tsx` to the clean base of `312f1d9` (v0.41.1) and expanded the checklist to the exact 17 items in 4 categories.
- Added procedural Lucide icons for all 17 requirements, completely replacing emojis.
- Enabled checklist persistence: each item is clickable, persistent in `checkedItems`, and rendered as marked/empty on print preview.
- Improved layer rendering: SVG zones have fillOpacity 0.7, layer reordering buttons (subir/bajar) are fully functional, and clicking any element brings it to the front immediately.
- Integrated color picker: works for both zones and symbols.
- Added Export options: Text checklist can be downloaded as a Markdown (.md) file, and Plano layout can be exported as a clean SVG.
- Fixed the navigation bu
... (truncado para checkpoint)

## Cambios realizados

-

## Próximo paso

-
