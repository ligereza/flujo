# Checkpoint — v0.47.1 - plano rider live legend colors

Fecha: 2026-06-29_23-23

## Estado

# LAST_HANDOFF - flujo continuation state

IMPORTANT: This file is intentionally ASCII-only to avoid mojibake on Windows + Git Bash/cp1252.
Do not use accents, enye, emoji, smart quotes, or special arrows here.
Daily commands for owner on Windows/Git Bash must use `py`, not `python`.

Date: 2026-06-28
Current version: 0.47.0
Main daily entry: `py -m flujo app`
Desktop entry: `py -m flujo app --desktop`
Verify on Windows: `py -m flujo verify`
Airdrop check on Windows: `py scripts/validate_airdrop.py` then `py scripts/run_airdrop_checks.py "message"`

## Current state

The repo is healthy after the v0.40 hub airdrop, v0.41.0 unified React hub, v0.42.1 example ingest templates, and the new v0.46.0 release that integrates Post Fiesta individual content and renders 8 full high-contrast, master-compiled flyers.

Real package CLI:
- `py -m flujo health`
- `py -m flujo doctor`
- `py -m flujo verify`
- `py -m flujo app`
- `py -m flujo hub serve --open`
- `py -m flujo hub index ...`
- `py -m flujo hub route ...`

## Recent completed work

### v0.47.0 - QA operativo para Eventos y Suplementos

- Added `py -m flujo plano <evento.json> --validate` to preflight rider/plano inputs before print/export.
- Expanded Plano/Rider technical symbol catalog to cover all 17 checklist requirements plus testeo/contencion, with procedural no-emoji SVG glyphs.
- Fixed checklist-to-map sync: checking, unchecking, "Marcar todo" and "Ir al Plano" now add/remove the mapped symbols consistently.
- Made screen and print/PDF technical legends dynamic, based on currently visible symbols instead of hardcoded 4-5 items.
- Rebuilt `context/flujo_hub.html`, `context/plano_demo.html` and `context/svg_visualizer.html` from React.
- Added `py -m flujo suplementos validate <svg...>` to detect invalid SVG/XML, wrong contraportada size and unreplaced placeholders.
- Added docs in `docs/QA_EVENTOS_SUPLEMENTOS.md` and tests for both validators.

### v0.46.0 - Post Fiesta Flyer, Live Visualizer & 8-Flyer Master Gen
... (truncado para checkpoint)

## Cambios realizados

-

## Próximo paso

-
