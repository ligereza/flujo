"""Resolve the local RD projection without creating a second authority.

The repository-local ``data/rd.db`` is the portable default.  A host that
keeps the canonical projection outside this checkout may set ``FLUJO_RD_DB``;
this is how MAK and field XIO share one reviewed file without copying it into
the standalone FLUJO repository.
"""

from __future__ import annotations

import os
from pathlib import Path


def rd_db_path(root: str | Path) -> Path:
    """Return the configured RD projection path for *root*.

    ``FLUJO_RD_DB`` is deliberately opt-in.  A clean clone remains portable
    and uses its own ignored ``data/rd.db``; a host installation can point all
    readers/writers at its one canonical projection explicitly.
    """
    configured = os.environ.get("FLUJO_RD_DB", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = Path(root).expanduser() / candidate
        return candidate.resolve()
    return Path(root).expanduser().resolve() / "data" / "rd.db"


__all__ = ["rd_db_path"]
