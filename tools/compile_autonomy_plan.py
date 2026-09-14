#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from flujo.knowledge.autonomy_plan import compile_autonomy_plan, load_json

def main(argv=None):
    parser = argparse.ArgumentParser()
    for name in ("plan", "dossier", "application", "evidence_return"):
        parser.add_argument(name)
    parser.add_argument("--learning")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    learning = load_json(args.learning) if args.learning else None
    result = compile_autonomy_plan(*(load_json(getattr(args, name)) for name in ("plan", "dossier", "application", "evidence_return")), learning)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output: args.output.write_text(rendered, encoding="utf-8")
    else: sys.stdout.write(rendered)
    return 0

if __name__ == "__main__": raise SystemExit(main())
