# HANDOFF v0.47.1 - Plano/Rider live legend and symbol colors hotfix

## Key Changes

- Fixed technical symbols color editing: the symbol glyph and label now use the element live color (`el.color`) instead of the static catalog color.
- Fixed live technical legend: screen and print/PDF legends now derive from visible symbol elements in the current canvas, including current label and color state.
- Fixed requirement sync edge case: checklist-generated symbols use stable `req-*` ids, so checking/unchecking requirements reliably updates the canvas and legend.
- Removed default electricity/extinguisher symbols from the base canvas so requirements drive those symbols instead of leaving stale legend entries.
- Rebuilt `context/flujo_hub.html`, `context/plano_demo.html` and `context/svg_visualizer.html` from React.

## Verify

```bash
py scripts/validate_airdrop.py
py scripts/run_airdrop_checks.py "v0.47.1 - plano rider live legend colors" --skip-push
py -m flujo verify
py -m flujo app
```

## Manual UI check

1. Open `py -m flujo app`.
2. Go to Plano/Rider.
3. Mark/unmark requirements.
4. Confirm the legend updates immediately.
5. Select a symbol, change its color, and confirm the symbol and legend color update live.
6. Print/PDF preview should show the visible symbol list, not a hardcoded subset.
