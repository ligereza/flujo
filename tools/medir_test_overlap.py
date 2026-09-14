#!/usr/bin/env python3
"""Find structural test-shape clusters without declaring them duplicates.

The detector parses test functions, replaces literal values with one stable
placeholder, and groups the remaining AST shape. A cluster is only a review
candidate: two tests can share a shape while protecting different contracts.
No test or production file is modified.

Usage::

    python3 tools/medir_test_overlap.py
    python3 tools/medir_test_overlap.py --top 20 --min-size 3
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"


class _LiteralNormalizer(ast.NodeTransformer):
    """Keep operations and names, but remove values from the comparison."""

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.copy_location(ast.Name(id="_LITERAL", ctx=ast.Load()), node)


@dataclass(frozen=True)
class TestShape:
    path: str
    name: str
    signature: str


class _ShapeCollector(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.classes: list[str] = []
        self.shapes: list[TestShape] = []
        self.normalizer = _LiteralNormalizer()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def _visit_test_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.name.startswith("test_"):
            return
        body = [self.normalizer.visit(ast.fix_missing_locations(stmt)) for stmt in node.body]
        module = ast.Module(body=body, type_ignores=[])
        qualified = ".".join((*self.classes, node.name))
        self.shapes.append(TestShape(
            self.path, qualified,
            ast.dump(module, annotate_fields=False, include_attributes=False),
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_test_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_test_function(node)


def iter_shapes() -> list[TestShape]:
    shapes: list[TestShape] = []
    for path in sorted(TESTS.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        collector = _ShapeCollector(str(path.relative_to(REPO)))
        collector.visit(tree)
        shapes.extend(collector.shapes)
    return shapes


def report(shapes: list[TestShape], *, min_size: int, top: int,
           cross_file: bool = False) -> None:
    groups: dict[str, list[TestShape]] = defaultdict(list)
    for shape in shapes:
        groups[shape.signature].append(shape)
    candidates = [items for items in groups.values()
                  if len(items) >= min_size
                  and (not cross_file or len({item.path for item in items}) > 1)]
    candidates.sort(key=lambda items: (-len(items), items[0].path, items[0].name))

    print(f"test functions parsed: {len(shapes)}")
    print(f"normalized shapes: {len(groups)}")
    scope = "; cross-file only" if cross_file else ""
    print(f"candidate groups (size >= {min_size}{scope}): {len(candidates)}")
    print("literal values are ignored; names, calls, operators and control flow remain")
    for number, items in enumerate(candidates[:top], start=1):
        print(f"\nGROUP {number}  size={len(items)}")
        for item in items:
            print(f"  {item.path}:{item.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-size", type=int, default=2,
                        help="minimum functions in a candidate group (default: 2)")
    parser.add_argument("--top", type=int, default=30,
                        help="number of groups to print (default: 30)")
    parser.add_argument("--cross-file", action="store_true",
                        help="only show shapes shared by different test files")
    args = parser.parse_args()
    if args.min_size < 2 or args.top < 1:
        parser.error("--min-size must be >= 2 and --top must be >= 1")
    report(iter_shapes(), min_size=args.min_size, top=args.top,
           cross_file=args.cross_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
