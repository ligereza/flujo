# LAST_HANDOFF - flujo continuation state

IMPORTANT: This file is intentionally ASCII-only to avoid mojibake on Windows + Git Bash/cp1252.
Do not use accents, enye, emoji, smart quotes, or special arrows here.
Daily commands for owner on Windows/Git Bash must use `py`, not `python`.

Date: 2026-06-28
Current version: 0.41.0
Main daily entry: `py -m flujo app`
Desktop entry: `py -m flujo app --desktop`
Verify on Windows: `py -m flujo verify`
Airdrop check on Windows: `py scripts/validate_airdrop.py` then `py scripts/run_airdrop_checks.py "message"`

## Current state

The repo is healthy after the v0.40 hub airdrop, v0.40.1 dispatcher fix, v0.40.2 Plano/Rider vanilla integration, and v0.40.3 React/Vite web layer for Plano Pro, and v0.40.4 React SVG Visualizer integration, and v0.40.5 real SVG API integration, and v0.41.0 unified React hub.

Real package CLI:
- `py -m flujo health`
- `py -m flujo doctor`
- `py -m flujo verify`
- `py -m flujo app`
- `py -m flujo hub serve --open`
- `py -m flujo hub index <build|stats|find|versions|dupes|cleanup|agent-brief> ...`
- `py -m flujo hub route <where|cuna|doctor> ...`

Important: `index` and `route` from the v0.40 local hub are namespaced under `hub` so they do not hide the existing Typer CLI commands.
Do not document them as top-level `py -m flujo index` or `py -m flujo route` unless aliases are intentionally added later.

## Recent completed work

### v0.40.0 - local hub, serve, index and route
- Added the local hub server and APIs under `src/flujo/serve`.
- Added route resolver under `src/flujo/route`.
- Added local index tooling under `src/flujo/index`.
- Added hub HTML/data improvements in `context/`.
- Initial airdrop replaced `src/flujo/__main__.py` with a custom dispatcher, which hid existing CLI commands.

### v0.40.1 - dispatcher fix and hub addons
- Restored `src/flujo/__main__.py` to delegate to `flujo.cli:app`.
- Added `src/flujo/cli_addons.py`.
- Registered the new local-hub commands under `py -m flujo hub ...`.
- Kept existing commands alive: health, doctor, job, eventos, airdrop, app, verify, etc.
- Archived root handoffs into `docs/handoffs/archive/root/`.
- Synchronized package version and active handoff to 0.40.1.

### v0.40.2 - Plano/Rider Pro vanilla integration
- Rebuilt `context/plano_demo.html` into a useful operational tool.
- Integrated the good ideas from the React PlanoTool proposal without adding Node/React to runtime.
- Added modes: requirements checklist, editable layout, and rider/cost/json outputs.
- Added draggable SVG zones, layers, add-zone buttons, property editor, zoom, grid, legend, export SVG, print, copy rider/costs, and JSON export.
- Keeps backend integration with `POST /api/plano/render`; double click still works in demo mode.

### v0.40.3 - React/Vite web layer for Plano Pro
- Decision changed: Node is accepted as a local/free UI development layer.
- Added `web/` with React + Vite + TypeScript + Tailwind.
- `npm run build:plano` generates a single-file HTML and copies it to `context/plano_demo.html`.
- Daily use remains `py -m flujo app`; Node is only needed to develop/rebuild the UI.
- The generated Plano page includes the React PlanoTool proposal and a `Motor Python` button for `/api/plano/render`.

### v0.40.4 - React SVG Visualizer integration
- Added `web/src/components/SvgVisualizer.tsx`.
- Added `web/src/data/svgIndex.ts` demo/index data based on the proposed SVG visualizer.
- `web/src/App.tsx` now has React navigation between Plano and SVG Visualizer.
- `npm run build:plano` copies the same single-file app to both `context/plano_demo.html` and `context/svg_visualizer.html`; initial view is selected by pathname.
- This keeps the UI fast to iterate while staying local/free and served by `py -m flujo app`.

### v0.40.5 - real SVG API integration
- `SvgVisualizer` now tries `/api/list-svg-works` and fetches real SVG files from `/svg/...`.
- If the backend is unavailable, it falls back to `MOCK_SVG_INDEX`.
- Added `/api/svg-index` as an alias in the main web hub.
- Added `/api/list-svg-works`, `/api/svg-index`, and `/svg/...` static serving to `src/flujo/serve/server.py`.
- Renamed the main web build command to `npm run build:context`; `npm run build:plano` remains as compatibility alias.
- CI now installs Node 20, runs `npm ci`, `npm run typecheck`, and `npm run build:context` before `py -m flujo verify`.

### v0.41.0 - unified React hub
- `context/flujo_hub.html` is now generated from the React app too.
- Added `AppShell`, `HubDashboard`, `JobsPanel`, `IntakePanel`, `CommandPanel`, and `api/flujoApi.ts`.
- Dashboard reads ping/jobs/SVG summary with demo fallback.
- Jobs panel reads `/api/list-jobs`.
- Intake panel uses `/api/parse-real-pedido` and `/api/create-job-draft` when served by `py -m flujo app`.
- `src/flujo/serve/server.py` gained light `/api/list-jobs`, `/api/dashboard-summary`, `/api/parse-real-pedido`, and read-only `/api/create-job-draft` response for compatibility.

## Airdrop model - keep this intact

Airdrop is the safe patch delivery path for agents without direct push.

Expected package:
- A ZIP containing `_airdrop/` at the top level.
- Files inside `_airdrop/` mirror their final repo paths.
- Include a `HANDOFF_*.md` or `HOTFIX_*.md` in the airdrop.
- Do not include caches, build output, credentials, binaries, or generated local data.

Apply path:
```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "short message"
```

If the airdrop modifies `src/flujo/airdrop.py`, explicit review is required:
```bash
py scripts/validate_airdrop.py --allow-airdrop-engine
py scripts/run_airdrop_checks.py "short message" --allow-airdrop-engine
```

Runner behavior:
- validates `_airdrop/`;
- performs dry-run using `flujo.airdrop.scan_airdrop()`;
- applies with backup and manifest;
- installs editable dev package;
- runs compileall, pytest, health, version, changelog check and hub smoke when available;
- only then writes checkpoint/commit/push unless skipped.

## Daily operating direction

flujo is focused on a free local-first request/work-status flow:

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

## Important Windows/Git Bash rules

- Use `py -m flujo ...`, not `python -m flujo ...`, in user-facing docs and handoff.
- Keep this file ASCII-only.
- Avoid special symbols in terminal output when possible.
- Do not store tokens, credentials or sensitive client data.
- Privacy scan/sanitize before sending real request data to external AI.

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

Hub server:
```bash
py -m flujo hub serve --open
```

Hub route:
```bash
py -m flujo hub route where --area eventos --pieza flyer
```

Hub index:
```bash
py -m flujo hub index agent-brief "etiqueta creatina"
```

## Cleanup policy

Safe to remove locally but do not include in airdrops:
- `__pycache__/`
- `.pytest_cache/`
- `src/flujo.egg-info/`
- `_airdrop/`
- `_airdrop_backups/`
- `_logs/`

Historical material should be archived, not deleted blindly.

## Next recommended changes

1. Decide whether to add top-level aliases for `route` and hub `index`, or keep them under `hub` only.
2. Update older docs that still mention pre-v0.40 paths or command shapes.
3. Consider splitting the very large `src/flujo/cli.py` into submodules later.
4. Build/rebuild the local index on the owner's Windows machine if needed.
