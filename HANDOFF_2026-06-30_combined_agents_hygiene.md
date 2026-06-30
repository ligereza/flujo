# HANDOFF 2026-06-30 - Combined agents + repo hygiene

## Summary

This airdrop combines the useful parts of Agente 1 and Agente 2 and adds a safe repo hygiene path based on the external repository review.

It intentionally does NOT replace these files from Agente 1 because doing so would remove existing functionality:

- web/package.json
- web/package-lock.json
- web/src/index.css
- web/src/components/SvgVisualizer.tsx
- web/src/data/svgIndex.ts

## Included changes

### Resolume / Chataigne

- `src/flujo/resolume/automator.py`
- `tests/test_resolume_automator.py`

The XML remains a parseable pre-flight descriptor for Chataigne/OSC. It is not a verified native `.noisette` session.

### Web dual workspace

- `web/src/App.tsx`
- `web/src/components/AppShell.tsx`
- `web/src/components/EventsPanel.tsx`
- `web/src/components/ResolumePanel.tsx`
- `web/src/components/CommandPanel.tsx`
- `web/src/components/HubDashboard.tsx`
- rebuilt `context/flujo_hub.html`
- rebuilt `context/plano_demo.html`
- rebuilt `context/svg_visualizer.html`

### Repo hygiene

- `scripts/cleanup_repo_hygiene_20260630.py`
- `docs/REPO_HYGIENE_ACTION_PLAN_2026-06-30.md`

The hygiene script is dry-run by default. It does not run automatically during airdrop apply.

## Verification already run in sandbox

```bash
python3 -m compileall src/flujo/resolume scripts/cleanup_repo_hygiene_20260630.py
PYTHONPATH=src python3 -m pytest tests/test_resolume_automator.py -q
cd web && npm run build:context
python3 scripts/validate_airdrop.py
```

All OK.

## Windows / Git Bash verification after apply

```bash
py -m compileall src/flujo/resolume scripts/cleanup_repo_hygiene_20260630.py
py -m pytest tests/test_resolume_automator.py -q
cd web
npm run build:context
cd ..
py -m flujo verify
```

## Hygiene after green checks

First inspect dry-run:

```bash
py scripts/cleanup_repo_hygiene_20260630.py
```

If the listed moves/deletes are correct:

```bash
py scripts/cleanup_repo_hygiene_20260630.py --apply
git status --short
py -m flujo verify
```

## Real tag recommendation

After this package is green and pushed:

```bash
git tag -a v0.48.0 -m "v0.48.0 - dual web workspace and resolume automator tests"
git push origin v0.48.0
```
