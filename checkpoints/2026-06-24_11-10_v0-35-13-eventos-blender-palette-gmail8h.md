# Checkpoint — v0.35.13 - eventos blender palette gmail8h

Fecha: 2026-06-24_11-10

## Estado

# LAST_HANDOFF - flujo continuation state

IMPORTANT: This file is intentionally ASCII-only to avoid mojibake on Windows + Git Bash/cp1252.
Do not use accents, enye, emoji, smart quotes, or special arrows here.
Daily commands for owner on Windows/Git Bash must use `py`, not `python`.

Date: 2026-06-24
Current version: 0.35.13
Main daily entry: `py -m flujo app`
Desktop entry: `py -m flujo app --desktop`
Verify on Windows: `py -m flujo verify`
Airdrop check on Windows: `py scripts/validate_airdrop.py` then `py scripts/run_airdrop_checks.py "message"`

## Current direction

flujo is now focused on a free request/work-status flow without monday.com:

Gmail / WhatsApp / GitHub Issue
  -> ordered request
  -> flujo job / brief or IG download
  -> design / review / delivery
  -> visual portal for boss/client

Recommended free stack:
- Gmail routing by subject: `eventos` -> EVENTOS, `suplementos` -> SUPLEMENTOS.
- Google Apps Script bridge: `tools/gmail_to_github_issues.gs`.
- GitHub Issues: request/change inbox with area labels.
- GitHub Projects: visual kanban for boss.
- `py -m flujo portal`: static HTML status portal.
- `py -m flujo app`: daily hub for operator.

## Recent completed work

### v0.35.3 - intake JSON end-to-end
- Added `py -m flujo intake json <file.json>`.
- Validates `schemas/intake.schema.json`.
- Creates `jobs/<folio>/brief.yaml`, `estado.md`, and `resultado.md`.
- Maps suggested format and dimensions to local catalog when possible.
- Keeps modification/rescale information and suggested commands.

### v0.35.4 - free boss portal / monday.com replacement
- Added `py -m flujo portal`.
- Exports `context/portal_jefe.html`.
- Added GitHub Issue Forms for design request and change request.
- Added `docs/PORTAL_JEFE_GRATIS.md`.

### v0.35.5 - Gmail to GitHub Issues
- Added `tools/gmail_to_github_issues.gs` for Google Apps Script.
- Added `docs/GMAIL_A_REPO_GRATIS.md`.
- Initial flow used Gmail labels; later v0.35.10 changed recommendation to subject routing.
... (truncado para checkpoint)

## Cambios realizados

-

## Próximo paso

-
