# HANDOFF v0.47.3 - Plano/Rider disposition and alignment hotfix

## Key Changes

- Added `Auto ordenar` for Plano/Rider layout disposition.
- Auto-arrange places:
  - entrance centered at top;
  - rectangular zones in the left/main operational area;
  - technical symbols in a clean right-side grid;
  - legend reset to a safe top-right position.
- Added/kept selected-element alignment buttons:
  - left, center, right;
  - top, middle, bottom.
- Improved screen legend to 2 columns and clamped height.
- Improved print/PDF legend to 3 columns, safer position, and shortened labels to reduce clipping.
- Keeps previous live color and live requirement legend fixes.
- Rebuilt `context/flujo_hub.html`, `context/plano_demo.html` and `context/svg_visualizer.html` from React.

## Verify

```bash
py scripts/run_airdrop_checks.py "v0.47.3 - plano rider disposition alignment legend" --skip-push
py -m flujo app
```

## Manual UI check

1. Mark many requirements.
2. Click `Auto ordenar`.
3. Select an item and use alignment buttons.
4. Reset legend if needed.
5. Print/PDF preview and confirm legend is inside the page.
