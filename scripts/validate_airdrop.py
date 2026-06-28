#!/usr/bin/env python3
"""Valida _airdrop/ antes de aplicar cambios.

Este script es deliberadamente conservador: evita ZIPs vacíos, archivos generados,
rutas deformadas por Markdown/autolink y cambios peligrosos al motor de airdrop.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
}

FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".db-journal",
    ".sqlite",
    ".sqlite3",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".psd",
    ".psb",
    ".ai",
    ".indd",
    ".aep",
    ".blend",
    ".zip",
    ".rar",
    ".7z",
}

FORBIDDEN_EXACT = {
    "_delete.txt",
    "src/_airdrop/docs/FASE1_LIMPIEZA.md",
    "src/_airdrop/scripts/cleanup_structural.sh",
}

FORBIDDEN_PREFIXES = (
    "_airdrop/",
    "_airdrop_backups/",
    "data/",
    "context/DAILY",
    "context/dashboard",
)

MARKDOWN_PATH_TOKENS = ("[", "]", "(http", "http://", "https://")


@dataclass
class Finding:
    level: str
    path: str
    message: str


def _rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _is_handoff(rel: str) -> bool:
    name = Path(rel).name
    return (name.startswith("HANDOFF_") or name.startswith("HOTFIX_")) and name.endswith(".md")


def validate_airdrop(base: Path, allow_airdrop_engine: bool = False) -> tuple[list[str], list[Finding]]:
    findings: list[Finding] = []
    if not base.exists():
        return [], [Finding("ERROR", "_airdrop", "No existe la carpeta _airdrop/")]
    if not base.is_dir():
        return [], [Finding("ERROR", "_airdrop", "_airdrop existe pero no es carpeta")]

    files = sorted([p for p in base.rglob("*") if p.is_file()], key=lambda p: p.as_posix())
    rels = [_rel(p, base) for p in files]

    if not files:
        findings.append(Finding("ERROR", "_airdrop", "No contiene archivos: posible ZIP vacío"))
        return rels, findings

    if not any(_is_handoff(r) for r in rels):
        findings.append(Finding("ERROR", "_airdrop", "Falta HANDOFF_*.md o HOTFIX_*.md obligatorio"))

    for path, rel in zip(files, rels):
        parts = set(path.relative_to(base).parts)
        suffix = path.suffix.lower()
        size = path.stat().st_size

        if size == 0:
            findings.append(Finding("ERROR", rel, "Archivo de 0 bytes"))

        if any(token in rel for token in MARKDOWN_PATH_TOKENS):
            findings.append(Finding("ERROR", rel, "Ruta parece deformada por Markdown/autolink"))

        if rel in FORBIDDEN_EXACT:
            findings.append(Finding("ERROR", rel, "Ruta explícitamente prohibida"))

        if any(part in FORBIDDEN_PARTS for part in parts):
            findings.append(Finding("ERROR", rel, "Incluye carpeta/cache generada prohibida"))

        if any(part.endswith(".egg-info") for part in parts):
            findings.append(Finding("ERROR", rel, "Incluye metadata .egg-info generada"))

        if suffix in FORBIDDEN_SUFFIXES:
            findings.append(Finding("ERROR", rel, f"Extensión generada/pesada prohibida: {suffix}"))

        if rel.startswith(FORBIDDEN_PREFIXES):
            findings.append(Finding("ERROR", rel, "Prefijo local/generado prohibido"))

        if rel == "src/flujo/airdrop.py" and not allow_airdrop_engine:
            findings.append(
                Finding(
                    "ERROR",
                    rel,
                    "Toca el motor de airdrop; requiere autorización explícita y --allow-airdrop-engine",
                )
            )

    return rels, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida _airdrop/ antes de aplicar")
    parser.add_argument("--airdrop-dir", default="_airdrop", help="Ruta de _airdrop/ (default: _airdrop)")
    parser.add_argument(
        "--allow-airdrop-engine",
        action="store_true",
        help="Permite modificar src/flujo/airdrop.py (solo con autorización explícita)",
    )
    args = parser.parse_args(argv)

    base = Path(args.airdrop_dir)
    rels, findings = validate_airdrop(base, allow_airdrop_engine=args.allow_airdrop_engine)

    print("Validando _airdrop/")
    print(f"Archivos detectados: {len(rels)}")
    for rel in rels:
        size = (base / rel).stat().st_size
        print(f"  {size:>8}  {rel}")

    if findings:
        print("\nHallazgos:")
        for f in findings:
            print(f"  [{f.level}] {f.path}: {f.message}")

    errors = [f for f in findings if f.level == "ERROR"]
    if errors:
        print("\nVALIDACIÓN FALLÓ. No apliques este airdrop.")
        return 1

    print("\nVALIDACIÓN OK. Puedes continuar con dry-run/apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
