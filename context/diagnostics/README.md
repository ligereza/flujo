# Context routing and diagnostic reports

This directory is the small context surface for an agent working from a Git
clone. `domains.json` routes an idea to one primary domain and optional support
domains without loading the whole repository or the raw WIN archive.

Commands:

```text
python3 tools/route_idea.py "quiero investigar manuales de cultivo para una obra 3D"
python3 -m flujo diagnose --area research --error "..." --command "..."
```

The diagnostic report is read-only, bounded and sanitized. It contains paths,
hash/branch state and validation candidates, not secrets, full databases,
private media or historical WIN contents.

`context/diagnostics/contracts/` contains domain contracts. It is not a second
global handoff and it does not override `agents.md` or `context/LAST_HANDOFF.md`.
