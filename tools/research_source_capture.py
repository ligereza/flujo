"""Plan or explicitly record one bounded public-source capture.

Discovery and capture stay separate.  The default command is a plan and makes
no network call; ``--record`` writes one capture receipt to the selected local
``SourceCorpusStore``.  It never crawls a list or turns a snippet into truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.source_pipeline import (  # noqa: E402
    SourceCorpusStore,
    available_backends,
    canonical_url,
    capture_url,
)


SCHEMA = "flujo-source-capture-gate-v1"


def capture_one(
    url: str,
    *,
    root: str | Path,
    backend: str = "auto",
    record: bool = False,
    timeout: int = 45,
    capture: Callable[..., dict[str, Any]] = capture_url,
) -> dict[str, Any]:
    """Return a plan or one provenance-bound local capture receipt."""
    normalized = canonical_url(url)
    if not normalized:
        return {"schema": SCHEMA, "decision": "abstain", "reason": "invalid_public_url", "url": str(url or "")}
    plan = {
        "schema": SCHEMA,
        "decision": "record" if record else "plan",
        "url": normalized,
        "backend": backend,
        "root": str(Path(root).expanduser()),
        "available_backends": available_backends(),
        "network_called": False,
    }
    if not record:
        plan["next_action"] = "review_url_license_then_rerun_with_record"
        return plan
    result = capture(normalized, backend=backend, timeout=timeout)
    store = SourceCorpusStore(root)
    receipt = store.record_capture(result, requested_backend=backend)
    return {
        **plan,
        "network_called": True,
        "capture": {
            "status": result.get("status"),
            "used_backend": result.get("backend"),
            "attempts": result.get("attempts", []),
            "error": result.get("error", ""),
        },
        "receipt": receipt,
        "store_summary": store.summary(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--backend", choices=("auto", "firecrawl", "crawl4ai", "urllib"), default="auto")
    parser.add_argument("--root", type=Path, default=Path("data/source_corpus"))
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--record", action="store_true", help="perform one capture and write its receipt")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = capture_one(args.url, root=args.root, backend=args.backend, record=args.record, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "decision": "error", "reason": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("decision") != "abstain" else 1


if __name__ == "__main__":
    raise SystemExit(main())
