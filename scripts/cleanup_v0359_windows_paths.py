"""Cleanup for v0.35.9 Windows checkout hotfix.

Run from repo root on Windows/Git Bash:

    py scripts/cleanup_v0359_windows_paths.py

Why:
- GitHub Actions Windows checkout failed because old checkpoint filenames were too long.
- Old generic issue templates were also confusing after area split.

This script deletes old long/generic paths if they still exist after applying an airdrop.
It is safe to run more than once.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DELETE_PATHS = [
    ".github/ISSUE_TEMPLATE/pedido_diseno.yml",
    ".github/ISSUE_TEMPLATE/pedido_impresion.yml",
    "checkpoints/2026-06-22_15-56_v0-35-1-version-suprema-utf-8-windows-swatches-adobe-layout-flow-blender-4-5-canva-api-receptor-imap-auto-compiler-cloud-github-actions-y-blindaje-sockets-10053.md",
    "checkpoints/2026-06-22_16-03_v0-35-1-version-suprema-utf-8-windows-swatches-adobe-layout-flow-blender-4-5-canva-api-receptor-imap-auto-compiler-cloud-github-actions-blindaje-sockets-10053-y-servidor-multihilo-threadinghttpserver.md",
    "checkpoints/2026-06-23_18-16_v0-35-1-version-suprema-utf-8-windows-swatches-adobe-layout-flow-blender-4-5-canva-api-receptor-imap-auto-compiler-cloud-github-actions-blindaje-sockets-10053-y-servidor-multihilo-threadinghttpserver.md",
]


def main() -> int:
    removed = 0
    for rel in DELETE_PATHS:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            removed += 1
            print(f"removed: {rel}")
        else:
            print(f"missing: {rel}")
    print(f"cleanup complete. removed={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
