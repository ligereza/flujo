# flujo web

React/Vite UI layer for flujo.

This is local/free development tooling. Daily operation still starts with:

```bash
py -m flujo app
```

Node is only required when rebuilding the UI.

## Current web app

Source:

```txt
web/src/App.tsx
web/src/components/AppShell.tsx
web/src/components/HubDashboard.tsx
web/src/components/JobsPanel.tsx
web/src/components/IntakePanel.tsx
web/src/components/CommandPanel.tsx
web/src/components/PlanoTool.tsx
web/src/components/SvgVisualizer.tsx
web/src/data/svgIndex.ts
```

Build and copy the single-file HTML into the Python-served context:

```bash
cd web
npm ci
npm run build:context
```

Outputs:

```txt
context/flujo_hub.html
context/plano_demo.html
context/svg_visualizer.html
```

The same single-file React app is copied to both paths. Initial view is selected by URL pathname:

- `flujo_hub.html` -> Hub operativo
- `plano_demo.html` -> Plano/Rider
- `svg_visualizer.html` -> SVG Visualizer

Rules:

- Do not commit `node_modules/` or `web/dist/`.
- Keep generated HTML offline-friendly.
- Backend integration should use local APIs served by `py -m flujo app`, for example `/api/plano/render`.

Compatibility alias:

```bash
npm run build:plano
```

`build:plano` calls `build:context` for older handoffs.
