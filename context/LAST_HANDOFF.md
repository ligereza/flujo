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
- Do not store tokens in repo. Use Google Apps Script Properties.

### v0.35.6 - README clean + PURPLE + suplementos RD
- Main README rewritten and simplified.
- Portal visual palette moved to PURPLE:
  - bg: #12001f
  - panel: #2b0a3d
  - main purple: #6d28d9
  - accent: #a855f7
  - paper: #f5e8ff
- Added `docs/BRIEF_SUPLEMENTOS_RD.md` from user brief.
- No cleanup deletion was applied yet. Cleanup candidates are listed below.

### v0.35.7 - ASCII handoff / Windows Git Bash encoding guard
- Rewrote this file as ASCII-only to avoid broken characters on Windows/Git Bash.
- Added explicit rule: owner uses `py`, not `python`.
- Added Windows encoding notes for future agents.
- Updated airdrop handoff to avoid accents and python commands.

### v0.35.8 - Gmail routing by area
- Gmail bridge added `GMAIL_ROUTES`.
- First version used area labels; v0.35.10 changed recommendation to subject routing.
- EVENTOS route: Instagram links, download with flujo/instaloader, then local Photoshop automation. If request asks for brief/plano/svg, create normal flujo job.
- SUPLEMENTOS route: new request, modification, or quote for flyer/label/pendon/post/stickers/stand/logo.
- Added `docs/FLUJO_AREAS_EVENTOS_SUPLEMENTOS.md`.

### v0.35.9 - Windows checkout and area issue templates hotfix
- Renamed three checkpoint files with too-long names that broke GitHub Actions Windows checkout.
- Removed old generic issue templates: `pedido_diseno.yml` and `pedido_impresion.yml`.
- Added area-specific templates: `pedido_eventos.yml` and `pedido_suplementos.yml`.
- Gmail bridge issue titles now use `[EVENTOS]` or `[SUPLEMENTOS]`.
- Added `scripts/cleanup_v0359_windows_paths.py` for airdrop users to remove old paths if needed.

### v0.35.10 - Gmail subject routing and agent-first README
- Gmail bridge no longer requires the word flujo in subjects.
- Default routing used grouped subject queries; v0.35.11 split them for reliability.
- `GMAIL_ROUTES` accepts full Gmail search queries, plus legacy `label:...` routes.
- README was simplified and now starts with the required agent manual reading order.
- Removed explicit supplements brief details from README; it only links to operational docs.

### v0.35.11 - Gmail hourly trigger and robust subject routes
- Apps Script setup now creates trigger every 1 hour.
- Added `GMAIL_LOOKBACK`, default `7d`, to avoid processing old email backlogs.
- Recommended routes are now separate: `subject:eventos`, `subject:evento`, `subject:suplementos`, `subject:suplemento`.
- This should catch subjects like `Suplementos - etiqueta Omega 3` more reliably than grouped Gmail search queries.

### v0.35.12 - EVENTOS flyer auto command
- Added `py -m flujo eventos flyer-auto <instagram_url>`.
- Downloads Instagram with instaloader and updates `C:\\rd\\AUTOMATIZACION\\input_ig.jpg`.
- Does not open Photoshop by default.
- To authorize Photoshop droplet: add `--run-droplet`; command asks for confirmation.
- Expected local files: `Droplet_Flyer.exe`, `historia.psd`, `input_ig.jpg`.

### v0.35.13 - EVENTOS palette and Blender preview
- Gmail Apps Script trigger changed to every 8 hours.
- `eventos flyer-auto` now writes `palette_ig.png` and `palette_ig.json`.
- Added `--render-blender` to render frame 1 of `cartelera.blend` into `preview_cartelera.png`.
- Added `--open-blender` to open `cartelera.blend` after confirmation.
- User will connect extracted colors/images inside Blender manually.

## Important Windows/Git Bash rules

- Use `py -m flujo ...`, not `python -m flujo ...`, in user-facing docs and handoff.
- Keep code identifiers, CLI option names, file names, and logs English/ASCII when possible.
- Markdown may be Spanish, but LAST_HANDOFF must stay ASCII-only.
- Avoid special symbols in terminal output when possible.
- If CLI prints Unicode, Windows stdout/stderr should be UTF-8 configured before Rich Console.
- Do not add BOM unless a specific Windows tool requires it.

## Current command examples

Install/editable:
```bash
py -m pip install -e .
```

Daily:
```bash
py -m flujo app
```

Verify:
```bash
py -m flujo verify
```

Portal:
```bash
py -m flujo portal --repo-url https://github.com/ligereza/vibecodeine
```

Gmail bridge setup is documented in:
```txt
docs/GMAIL_A_REPO_GRATIS.md
```

Supplements RD brief is in:
```txt
docs/BRIEF_SUPLEMENTOS_RD.md
```

## Cleanup candidates - not deleted yet

User asked to list before deleting. Do not delete until approved.

1. `projects/tapiz/vibecode.egg-info/`
   - Looks generated by Python packaging/build.
   - Recommendation: delete or move to archive.

2. `src/flujo.egg-info/`
   - Looks generated by editable install.
   - Recommendation: delete if not intentionally versioned.

3. `checkpoints/` old files
   - Historical snapshots. Some may be redundant now that LAST_HANDOFF is the source of truth.
   - Recommendation: archive or keep only latest important ones.

4. Legacy duplicated docs in `docs/`
   - Many guides overlap with README + LAST_HANDOFF.
   - Recommendation: review and archive, not blind delete.

5. `context/portal_jefe.html`
   - Generated by `py -m flujo portal`.
   - Included for immediate visual preview, but can be regenerated.

6. `.archive/`
   - Historical material.
   - Recommendation: do not delete unless owner confirms.

Recommended safe first cleanup: only egg-info folders.

## Next recommended feature

Implement:
```bash
py -m flujo issue import <number-or-url>
```

## New operational addition

Added a Creative Director delegation role for multi-agent workflow.
Use it when you need a premium launch strategy, brand narrative, and final review of specialist outputs.
Command example:
```bash
py -m flujo delegate creative-director "Pulir la identidad visual del hub para un lanzamiento premium"
```

Goal:
- Read a GitHub Issue created from Gmail or Issue Form.
- Convert to intake JSON or job.
- Avoid copy/paste from GitHub to flujo app.
- Apply privacy scan/sanitize before writing real request data into repo.

## Next agent handoff - ambitious direction

The current repo is no longer just a design workflow shell. It is becoming a compact operating system for creative production.
The next agent should look beyond the current hub/job flow and explore a new layer: productization and reuse.

Suggested direction:
- Turn the current workflow into a reusable creative engine for multiple verticals, not only eventos/suplementos.
- Create a modular system for templates, formats, and packaging so the same pipeline can serve flyers, labels, social posts, and future print products.
- Move from "tooling" to "system design": define reusable patterns, metadata, and output contracts that make new formats easy to add.
- Explore a more strategic area: AI-assisted review, brand compliance, and auto-generation quality gates.

Concrete opportunities:
- Add a generic format registry so the app can map a request to a template without hardcoding per area.
- Introduce a lightweight review layer that checks brand, margins, contrast, and export readiness before delivery.
- Build a bridge from jobs to reusable assets, so one job can produce multiple outputs from the same source brief.
- Investigate how datadrops can become training and validation material for future auto-generation, not just reference storage.

This is the moment to think bigger: the repo should feel like a creative operating platform, not only a set of scripts.
The next agent should be bold, but keep the implementation grounded in the existing CLI, jobs, hub, and export architecture.

Recommended first move:
- Create a generic format/template registry and wire one new format through the same job->export flow.
- Keep the implementation modular and reusable so future areas can plug in without rewriting the stack.

## Files added/changed in current airdrop line

Key files:
- `README.md`
- `context/LAST_HANDOFF.md`
- `context/portal_jefe.html`
- `docs/BRIEF_SUPLEMENTOS_RD.md`
- `docs/GMAIL_A_REPO_GRATIS.md`
- `docs/PORTAL_JEFE_GRATIS.md`
- `tools/gmail_to_github_issues.gs`
- `.github/ISSUE_TEMPLATE/pedido_eventos.yml`
- `.github/ISSUE_TEMPLATE/pedido_suplementos.yml`
- `.github/ISSUE_TEMPLATE/cambio_diseno.yml`
- `src/flujo/portal.py`
- `src/flujo/intake/json_parser.py`
- `src/flujo/cli.py`
- `src/flujo/version.py`
- `tests/test_intake_json_cli.py`
- `tests/test_portal_jefe.py`

## End rule

Before ending any future session:
1. Run `py -m flujo verify` on Windows if possible, otherwise note Linux-only verification.
2. Update this file in ASCII-only text.
3. Keep commands using `py` for the owner.
4. If delivering an airdrop, include a HANDOFF file that is also ASCII-only.

## Added pending airdrop - 2026-06-28 logo_clean_lab

This airdrop adds an unfinished experimental project:
```txt
projects/logo_clean_lab/
```

Purpose:
- Build a local Illustrator logo cleanup lab.
- Keep real logos private/local.
- Track tests and failures before changing rules again.

Main script:
```txt
tools/illustrator/scripts/logo_clean_master.jsx
```

Important lessons:
- Do not globally align word baseline/cap height automatically.
- Do not force diagonals to 45 degrees.
- Do not collapse all handles of a node.
- For straight segment p1 -> p2, collapse only p1.rightDirection and p2.leftDirection.
- Preserve neighboring curve handles in B/R/P/D.

Simple next tasks:
1. Test Illustrator script with mode A then W on one simple word.
2. Save 3 learning reports with notes.
3. If B/R/P/D lose curves, tune MIXED rules first.

Verification note:
- Windows: py scripts/validate_airdrop.py
- Windows: py scripts/run_airdrop_checks.py "logo clean lab experimental"

## Added pending hotfix - 2026-06-28 airdrop checkpoint timeout

Problem:
- `run_airdrop_checks.py` could appear stuck at `flujo.airdrop.run_auto_checkpoint()`.
- Likely cause: `git push` used captured output, no live prompt, and no timeout.

Changes:
- `src/flujo/airdrop.py` adds timeout/live output to git helper.
- `git push` now shows output and stops after 180 seconds.
- `run_auto_checkpoint(message, push=True)` can skip push.
- `scripts/run_airdrop_checks.py` adds `--skip-push`.
- Tests cover skip-push and static runner behavior.

## Added new guardrail - 2026-06-28 HERRAMIENTAS_VISUALES.md

Problem:
- Agents modified plano_demo.html and svg_visualizer.html without understanding their context/purpose.
- Confused RIDER RD EVENTOS (operational) with visor de diseños SUPLEMENTOS (gallery).
- No clear documentation on what each tool does, what references they use, what NOT to touch.

Solution:
- Created `docs/HERRAMIENTAS_VISUALES.md` — explicit guardrail document.
- Maps each tool to its reference (Propuesta_Reduciendo_Dano.txt vs BRIEF_SUPLEMENTOS_RD.md).
- Removed all BRAND references (was a tool, not for agent use).
- Added 5-question checklist: before modifying, must answer these or READ FIRST.
- Clear tables: what can modify, what NOT to touch.

Structure:
- `plano_demo.html` = RIDER RD EVENTOS (document, 2 pages: reqs + layout, for producers)
- `svg_visualizer.html` = Visor SUPLEMENTOS (gallery, search/filter/zoom, for designers)
- CSS internal only; paleta visual reference, not BRAND dependency

Next agent MUST:
1. Read docs/HERRAMIENTAS_VISUALES.md FIRST (before touching either HTML)
2. Answer 5 questions before modifying
3. Understand: RIDER != gallery. Context matters.

## Improved HTML tools - 2026-06-28 v0.36.1

Enhancements to visual tools based on guardrail analysis:

### plano_demo.html (RIDER RD EVENTOS)
- Expanded rider content: now includes full requerimientos operativos (espacio, infraestructura, coordinación)
- Rider text follows Propuesta_Reduciendo_Dano.txt structure (Stand Informativo, Testeo, Contención)
- Better section headers and professional formatting
- Includes detailed checklist for event producers

### svg_visualizer.html (Visor SUPLEMENTOS)
- Improved modal layout: side-by-side preview + info panel (responsive)
- Better SVG display with object-fit contain + smooth animations
- Enhanced metadata display: tags, categoría, metadatos clarity
- New functions: downloadMaterial(), copyPath() for better UX
- Modal title, description, and info areas reorganized for scannability

Both tools now aligned with their purpose:
- RIDER: operational/commercial document for producers
- VISUALIZER: professional gallery for designers/products

Status: ✅ Tested locally, responsive, professional presentation

## Agent communication guardrails - 2026-06-28 v0.36.2

Created two new guardrail documents to prevent future agent confusion:

### docs/AGENT_GUARDRAILS_VISUAL_TOOLS.md
- 5-question rule (mandatory before modifying HTML)
- Quick reference table (tool purpose / reference / no-touch)
- Red flags checklist (STOP conditions)
- Pre-commit quality checklist (navigation, responsive, console clean)
- Key URLs that should never change

### PARA_IA.md (rewritten)
- Bullet-based, enfático en guardrails
- Obligatory reading order (5 steps)
- Non-negotiable rules table
- Visual tools warning + links to guardrails
- Quick reference for common mistakes

Both documents aim to prevent:
- Modifying tools without understanding context
- Ignoring HERRAMIENTAS_VISUALES.md
- Committing untested HTML changes
- Confusing RIDER (document) with VISUALIZER (gallery)

Status: ✅ Ready for next agent

Recommended recovery if a previous run already applied files:
```bash
py scripts/run_airdrop_checks.py --resume "logo clean lab experimental" --skip-push
```

Then push manually when auth is ready:
```bash
git push
```

## Added pending airdrop - 2026-06-28 readme logo clean summary

Purpose:
- Return documentation to the normal simple airdrop flow.
- Clarify that the previous checkpoint issue was likely caused by a local heavy folder (`logo3d/`) accidentally inside the repo.
- Add summary and goal for `projects/logo_clean_lab/`.
- Update README with practical airdrop notes.

Normal airdrop commands:
```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "mensaje"
```

Only use `--allow-airdrop-engine` if an airdrop changes `src/flujo/airdrop.py`.

Before running auto-checkpoint:
```bash
git status --short
```

If local heavy folders appear, remove or ignore them first.

Simple next tasks:
1. Apply this airdrop with the two normal commands.
2. Test `logo_clean_master.jsx` in Illustrator with mode A then W.
3. Register good/bad results in the learning JSONL.
