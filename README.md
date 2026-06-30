# flujo - operational agent workspace

`flujo` is a local-first workspace for requests, jobs, briefs, design operations, RD/suplementos work, Studio/eventos work, web hub, and agent-delivered patches.

This repository is optimized for agent continuity. The goal is operational clarity: read the handoff, make a minimal complete change, verify, and deliver through `_airdrop/` if there is no push access.

## Mandatory agent entry

Read in this order:

```txt
1. AGENTS.md
2. context/LAST_HANDOFF.md
3. docs/AGENT_AIRDROP_PROTOCOL.md
4. docs/REPO_MAP.md
5. The files related to the task
```

If there is a conflict, this order wins:

```txt
1. Direct user instruction
2. AGENTS.md
3. context/LAST_HANDOFF.md
4. Specific docs
5. README.md
```

## Environment

```txt
Primary user environment: Windows + Git Bash
User-facing Python command: py
Do not tell the user to run python
Keep context/LAST_HANDOFF.md ASCII-only
Do not store tokens, credentials, cookies, client secrets, or sensitive real data
Remote repo: https://github.com/ligereza/vibecodeine/
```

## Daily commands

```bash
py -m flujo app
py -m flujo app --desktop
py -m flujo verify
py -m flujo health
py -m flujo version
```

## Core workflow

```txt
request / email / issue
  -> intake
  -> job
  -> brief
  -> design / automation / review
  -> deliverable
  -> handoff
```

Useful commands:

```bash
py -m flujo job new "nombre pedido" --email inbox/correo.txt
py -m flujo job prepare jobs/<job>
py -m flujo intake json inbox/pedido.json
py -m flujo brief paquete-cotizacion jobs/<job>
```

## Operational areas

### RD / Suplementos

Institutional RD work: supplements, quotes, SVG labels/back covers, stand plans, rider/costs.

```bash
py -m flujo suplementos list
py -m flujo suplementos contraportada "Impulso" --output salida.svg
py -m flujo suplementos validate svg/suplementos_rd/04_contraportadas/generadas/*.svg
py -m flujo plano projects/plano/ejemplos/evento_ejemplo.json --validate
```

### Studio / Eventos

Personal/studio work: flyers, Instagram inputs, VJ/club workflow, Resolume/Chataigne automation.

```bash
py -m flujo eventos flyer-auto "https://www.instagram.com/p/XXXX/"
py -m flujo resolume automatizar jobs/<job_id>
```

Rule:

```txt
Use instaloader for Instagram. Do not use yt-dlp.
```

### Web hub

Source:

```txt
web/src/
```

Generated context HTML:

```txt
context/flujo_hub.html
context/plano_demo.html
context/svg_visualizer.html
```

Build:

```bash
cd web
npm run typecheck
npm run build:context
cd ..
```

## Airdrop protocol

Agents without push access must deliver a ZIP containing `_airdrop/` at the top level.

Correct:

```txt
_airdrop/HANDOFF_2026-06-30_description.md
_airdrop/context/LAST_HANDOFF.md
_airdrop/src/flujo/module.py
_airdrop/tests/test_module.py
_airdrop/docs/something.md
```

Incorrect:

```txt
airdrop/
_airdrop/_airdrop/
v0.48/_airdrop/
files outside _airdrop/
Markdown links instead of real files
```

Every airdrop must include:

```txt
HANDOFF_*.md or HOTFIX_*.md
context/LAST_HANDOFF.md updated
real files in final repo paths
verification report
```

Validate and apply:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "short message"
```

Resume if apply already happened but later checks failed:

```bash
py scripts/run_airdrop_checks.py --resume "short message"
```

If touching `src/flujo/airdrop.py`, explicit user approval is required:

```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "short message" --allow-airdrop-engine
```

## Verification

Python changes:

```bash
py -m compileall src/flujo
py -m pytest tests/ -q
py -m flujo verify
```

Web changes:

```bash
cd web
npm run typecheck
npm run build:context
cd ..
```

Airdrop changes:

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "short message"
```

Do not report success unless the relevant verification was actually run.

## Cleanup

Safe local cleanup:

```bash
rm -rf _airdrop
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
rm -rf .pytest_cache
rm -rf _logs
git status --short
```

Do not commit or include in airdrops:

```txt
__pycache__/
.pytest_cache/
node_modules/
dist/
build/
_airdrop/
_airdrop_backups/
_logs/
*.zip
*.db
credentials
heavy real assets
```

Historical docs should be archived, not deleted blindly.

## Repository map

```txt
src/flujo/        core Python package and CLI
web/              React/Vite local web hub
context/          current handoff and generated local HTML
tests/            pytest suite
scripts/          validation, airdrop, maintenance scripts
docs/             operational manuals
tools/            helper tools and external workflow specs
projects/         operational project folders and delegated work
jobs/             local jobs
schemas/          intake schemas
.github/          CI, issue templates, repo automation
knowledge/        versioned operational memory
```

## Agent final response format

Every agent delivery must include:

```txt
1. Files changed
2. Problem solved
3. How to use it with py commands
4. Real risks or pending work
5. Reporte Formal de Verificacion y Tolerancia Cero a Errores
```

Verification report format:

```txt
Reporte Formal de Verificacion y Tolerancia Cero a Errores
- py -m compileall src/flujo: OK/FALLO/no aplica
- py -m pytest tests/ -q: OK/FALLO/no aplica
- cd web && npm run build:context: OK/FALLO/no aplica
- py -m flujo verify: OK/FALLO/no aplica
- Observaciones: ...
```

## License

MIT
