# Repo Hygiene Action Plan - 2026-06-30

This plan responds to the external repo review without disrupting active agent work.

## Confirmed issues

- Root contains many `HANDOFF_v*.md` files.
- Root contains duplicate/unsafe names such as `brief_suplementos_rd_encargado (1).md`.
- Root contains legacy/prototype files such as `studio_prototipo.html` and `aplicar_fix.py`.
- Git versions exist in files/commits but there are no Git tags yet.
- The repo has tests and CI, but README should make that more visible.

## Conservative cleanup policy

Do not split the repo yet. Keep the local-first monorepo while clarifying boundaries:

- `src/flujo/` for Python core and CLI.
- `src/flujo/resolume/` for Studio Resolume automation.
- `src/flujo/eventos/` for Studio event automation.
- `src/flujo/comercial/` for RD/supplements.
- `web/` for React/Vite.
- `tools/` for helper automators/specs.
- `context/` for current continuity.
- `docs/` for human docs and archived handoffs.

## Safe helper script

Dry-run:

```bash
py scripts/cleanup_repo_hygiene_20260630.py
```

Apply after all agent airdrops and checks are green:

```bash
py scripts/cleanup_repo_hygiene_20260630.py --apply
git status --short
py -m flujo verify
```

## Tag recommendation

After Agent 1 and Agent 2 are integrated and green, create a real tag:

```bash
git tag -a v0.48.0 -m "v0.48.0 - dual web workspace and resolume automator tests"
git push origin v0.48.0
```

If tagging the pre-agent-hygiene state instead, use:

```bash
git tag -a v0.47.13 -m "v0.47.13 - stable agent3 dual docs and resolume base"
git push origin v0.47.13
```
