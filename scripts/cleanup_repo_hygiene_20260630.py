#!/usr/bin/env python3
"""Safe repo hygiene helper for the post-agent cleanup phase.

Default mode is dry-run. Use --apply only after the agent airdrops are applied
and checks are green. The script focuses on the issues raised in the external
repo review: root handoff clutter, duplicate root briefs, and obvious legacy
root prototypes. It does not touch source code, web code, jobs, credentials or
tracked release assets.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TODAY = datetime.now().strftime("%Y-%m-%d")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def move_file(src: Path, dst: Path, apply: bool, actions: list[str]) -> None:
    actions.append(f"MOVE {rel(src)} -> {rel(dst)}")
    if not apply:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Destino ya existe: {dst}")
    shutil.move(str(src), str(dst))


def delete_file(src: Path, apply: bool, actions: list[str]) -> None:
    actions.append(f"DELETE {rel(src)}")
    if apply:
        src.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Limpieza segura post-airdrop para flujo")
    parser.add_argument("--apply", action="store_true", help="aplicar cambios; por defecto solo muestra dry-run")
    args = parser.parse_args()

    actions: list[str] = []

    # 1) Root handoff clutter -> docs/handoffs/archive/root/
    handoff_dest = ROOT / "docs" / "handoffs" / "archive" / "root"
    for src in sorted(ROOT.glob("HANDOFF_v*.md")):
        move_file(src, handoff_dest / src.name, args.apply, actions)

    # 2) Duplicate brief with spaces/parentheses.
    canonical = ROOT / "brief_suplementos_rd_encargado.md"
    duplicate = ROOT / "brief_suplementos_rd_encargado (1).md"
    briefs_dest = ROOT / "docs" / "briefs"
    if duplicate.exists() and canonical.exists():
        if filecmp.cmp(canonical, duplicate, shallow=False):
            delete_file(duplicate, args.apply, actions)
        else:
            move_file(canonical, briefs_dest / "brief_suplementos_rd_encargado.md", args.apply, actions)
            move_file(duplicate, briefs_dest / "brief_suplementos_rd_encargado_v2.md", args.apply, actions)
    elif duplicate.exists():
        move_file(duplicate, briefs_dest / "brief_suplementos_rd_encargado_v2.md", args.apply, actions)

    # 3) Obvious root legacy/prototype files -> .archive/root_legacy/<date>/
    legacy_dest = ROOT / ".archive" / "root_legacy" / TODAY
    for name in ("studio_prototipo.html", "aplicar_fix.py"):
        src = ROOT / name
        if src.exists():
            move_file(src, legacy_dest / name, args.apply, actions)

    # 4) Local-only generated clutter. These are intentionally not archived.
    for path in [ROOT / ".pytest_cache", ROOT / "_airdrop_backups", ROOT / "_logs"]:
        if path.exists():
            actions.append(f"PRUNE LOCAL {rel(path)}")
            if args.apply:
                shutil.rmtree(path, ignore_errors=True)
    for cache in ROOT.rglob("__pycache__"):
        if ".git" in cache.parts:
            continue
        actions.append(f"PRUNE LOCAL {rel(cache)}")
        if args.apply:
            shutil.rmtree(cache, ignore_errors=True)

    if not actions:
        print("No hygiene actions detected.")
        return 0

    print("Repo hygiene actions:" + (" APPLY" if args.apply else " DRY-RUN"))
    for item in actions:
        print(f"- {item}")
    if not args.apply:
        print("\nDry-run only. To apply: py scripts/cleanup_repo_hygiene_20260630.py --apply")
    else:
        print("\nApplied. Review with: git status --short")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
