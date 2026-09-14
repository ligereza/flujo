#!/usr/bin/env python3
"""Consolidate approved static duplicate files without touching Git or protected roots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/mak")
ARCHIVE_ROOT = ROOT / "_archive" / "orden-limpieza-20260828"
REASON = "duplicado-exacto-consolidado"
ARCHIVE_DIR = ARCHIVE_ROOT / "por-razon" / REASON
RETIREMENT_MAP = ARCHIVE_ROOT / "mapa-de-retiro.csv"
ACTION_LOG = ROOT / "indexes" / "mak-consolidation-20260829" / "applied-actions.json"

PROTECTED_TOPS = {"WIN", "curatoria_inbox", "GoogleDrive", "OneDrive"}
GIT_TOPS = {"flujo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_action_log(action_log: list[dict]) -> None:
    payload = {
        "schema": "mak-static-duplicate-consolidation-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "protected_roots_untouched": sorted(PROTECTED_TOPS),
        "git_roots_untouched": sorted(GIT_TOPS),
        "action_count": len(action_log),
        "actions": action_log,
    }
    ACTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    ACTION_LOG.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def check_path(path: Path) -> None:
    if path.is_absolute() and path != ROOT and ROOT not in path.parents:
        raise RuntimeError(f"path outside MAK: {path}")
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(f"path outside MAK: {path}") from exc
    top = relative.parts[0] if relative.parts else ""
    if top in PROTECTED_TOPS:
        raise RuntimeError(f"protected root: {path}")
    if top in GIT_TOPS:
        raise RuntimeError(f"Git root: {path}")
    if ".git" in relative.parts:
        raise RuntimeError(f"Git internals: {path}")


def validate_file(path: Path) -> None:
    check_path(path)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"expected regular file: {path}")


def append_retirement_row(destination: Path, original: Path, why: str) -> None:
    fields = ["razon", "ahora_en", "ruta_original", "por_que"]
    if not RETIREMENT_MAP.exists():
        raise RuntimeError(f"retirement map missing: {RETIREMENT_MAP}")
    row = [REASON, str(destination.relative_to(ARCHIVE_ROOT)), str(original), why]
    with RETIREMENT_MAP.open("r", encoding="utf-8", newline="") as handle:
        if any(existing == row for existing in csv.reader(handle)):
            return
    with RETIREMENT_MAP.open("a", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerow(row)


def move_to_archive(path: Path, action_log: list[dict], note: str) -> Path:
    destination = ARCHIVE_DIR / path.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() and destination.is_file():
        action_log.append(
            {
                "operation": "archive_already_applied",
                "original": str(path),
                "archive": str(destination),
                "sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
                "note": note,
            }
        )
        return destination
    validate_file(path)
    digest = sha256(path)
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"archive destination already exists: {destination}")
    shutil.move(str(path), str(destination))
    if not destination.is_file() or sha256(destination) != digest:
        raise RuntimeError(f"archive verification failed: {destination}")
    append_retirement_row(
        destination,
        path,
        f"sha256={digest}; {note}",
    )
    action_log.append(
        {
            "operation": "archive",
            "original": str(path),
            "archive": str(destination),
            "sha256": digest,
            "size_bytes": destination.stat().st_size,
            "note": note,
        }
    )
    return destination


def move_canonical(source: Path, destination: Path, action_log: list[dict], note: str) -> None:
    if source.is_symlink() and destination.is_file() and source.is_file():
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"canonical alias verification failed: {source}")
        action_log.append(
            {
                "operation": "rename_already_applied",
                "original": str(source),
                "canonical": str(destination),
                "sha256": sha256(destination),
                "size_bytes": destination.stat().st_size,
                "note": note,
            }
        )
        return
    validate_file(source)
    check_path(destination)
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"canonical destination already exists: {destination}")
    digest = sha256(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    if not destination.is_file() or sha256(destination) != digest:
        raise RuntimeError(f"canonical move verification failed: {destination}")
    action_log.append(
        {
            "operation": "rename_canonical",
            "original": str(source),
            "canonical": str(destination),
            "sha256": digest,
            "size_bytes": destination.stat().st_size,
            "note": note,
        }
    )


def symlink_alias(alias: Path, canonical: Path, action_log: list[dict], note: str) -> None:
    check_path(alias)
    check_path(canonical)
    if alias.is_symlink() and alias.is_file() and canonical.is_file():
        if sha256(alias) != sha256(canonical):
            raise RuntimeError(f"existing alias verification failed: {alias}")
        action_log.append(
            {
                "operation": "compatibility_symlink_already_applied",
                "alias": str(alias),
                "canonical": str(canonical),
                "sha256": sha256(canonical),
                "note": note,
            }
        )
        return
    if alias.exists() or alias.is_symlink():
        raise RuntimeError(f"alias already exists: {alias}")
    if not canonical.is_file() or canonical.is_symlink():
        raise RuntimeError(f"canonical is not a regular file: {canonical}")
    relative_target = os.path.relpath(canonical, alias.parent)
    alias.symlink_to(relative_target)
    if not alias.is_file() or sha256(alias) != sha256(canonical):
        alias.unlink(missing_ok=True)
        raise RuntimeError(f"alias verification failed: {alias}")
    action_log.append(
        {
            "operation": "compatibility_symlink",
            "alias": str(alias),
            "canonical": str(canonical),
            "sha256": sha256(canonical),
            "note": note,
        }
    )


def consolidate_pair(
    canonical: Path,
    duplicate: Path,
    action_log: list[dict],
    note: str,
) -> None:
    if duplicate.is_symlink() and duplicate.is_file() and canonical.is_file():
        if sha256(duplicate) != sha256(canonical):
            raise RuntimeError(f"existing duplicate alias verification failed: {duplicate}")
        archive = ARCHIVE_DIR / duplicate.relative_to(ROOT)
        if not archive.is_file() or sha256(archive) != sha256(canonical):
            raise RuntimeError(f"missing or invalid archived duplicate: {archive}")
        action_log.append(
            {
                "operation": "pair_already_applied",
                "duplicate": str(duplicate),
                "canonical": str(canonical),
                "archive": str(archive),
                "sha256": sha256(canonical),
                "note": note,
            }
        )
        return
    validate_file(canonical)
    validate_file(duplicate)
    canonical_hash = sha256(canonical)
    duplicate_hash = sha256(duplicate)
    if canonical_hash != duplicate_hash:
        raise RuntimeError(f"hash mismatch: {canonical} != {duplicate}")
    move_to_archive(duplicate, action_log, f"canonical={canonical}; {note}")
    symlink_alias(duplicate, canonical, action_log, note)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("dry-run only; use --apply to execute the approved write set")
        return 0
    if ACTION_LOG.exists():
        existing = json.loads(ACTION_LOG.read_text(encoding="utf-8"))
        if existing.get("schema") == "mak-static-duplicate-consolidation-v2":
            print(json.dumps({"status": "already_applied", "action_log": str(ACTION_LOG)}, sort_keys=True))
            return 0

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    action_log: list[dict] = []

    # Stable root-level duplicate with a clear generated suffix.
    consolidate_pair(
        ROOT / "Descargas/cotizaciones(3).html",
        ROOT / "Descargas/cotizaciones(3)(1).html",
        action_log,
        "suffix copy has no measured consumer",
    )

    # The script itself defines ~/kvm-linux.sh as its canonical daily path.
    move_canonical(
        ROOT / "Escritorio/kvm-linux.sh",
        ROOT / "kvm-linux.sh",
        action_log,
        "script declares ~/kvm-linux.sh as the daily path",
    )
    move_to_archive(
        ROOT / "Descargas/kvm-linux(1).sh",
        action_log,
        "duplicate of the canonical KVM script; no consumer at Downloads",
    )
    symlink_alias(
        ROOT / "Escritorio/kvm-linux.sh",
        ROOT / "kvm-linux.sh",
        action_log,
        "compatibility path for the former Desktop location",
    )

    # RD static documents: one descriptive canonical file, old paths retained as aliases.
    rd_same_name = [
        "MAPA_RD_por_secciones.json",
        "packs_servicios_rd.json",
        "packs_servicios_rd_dark.pdf",
        "packs_servicios_rd_gris.pdf",
        "packs_servicios_rd_gris.svg",
        "plano_rider_dark.pdf",
        "plano_rider_gris.pdf",
    ]
    for name in rd_same_name:
        consolidate_pair(
            ROOT / f"RD/{name}",
            ROOT / f"RD/New Folder/assets/{name}",
            action_log,
            "same basename and same SHA-256; root RD path is canonical",
        )

    rd_renames = [
        (
            "RD/REFERENCIA_VALORES.pdf",
            "RD/brief_packs_plano_dark.pdf",
            "RD/New Folder/assets/brief_packs_plano_dark.pdf",
        ),
        (
            "RD/R.pdf",
            "RD/brief_packs_plano_gris.pdf",
            "RD/New Folder/assets/brief_packs_plano_gris.pdf",
        ),
        (
            "RD/referenciaprecios.svg",
            "RD/packs_servicios_rd_dark.svg",
            "RD/New Folder/assets/packs_servicios_rd_dark.svg",
        ),
    ]
    for old_name, canonical_name, duplicate_name in rd_renames:
        old_path = ROOT / old_name
        canonical_path = ROOT / canonical_name
        duplicate_path = ROOT / duplicate_name
        if old_path.is_symlink() and canonical_path.is_file() and duplicate_path.is_symlink():
            if sha256(old_path) != sha256(canonical_path) or sha256(duplicate_path) != sha256(canonical_path):
                raise RuntimeError(f"existing RD alias verification failed: {old_path}")
            action_log.append(
                {
                    "operation": "rd_rename_already_applied",
                    "old_path": str(old_path),
                    "canonical": str(canonical_path),
                    "duplicate": str(duplicate_path),
                    "sha256": sha256(canonical_path),
                    "note": "resume after a previously verified partial run",
                }
            )
            continue
        validate_file(old_path)
        validate_file(duplicate_path)
        if sha256(old_path) != sha256(duplicate_path):
            raise RuntimeError(f"hash mismatch in RD rename: {old_path} != {duplicate_path}")
        move_canonical(
            old_path,
            canonical_path,
            action_log,
            "descriptive name chosen after comparing identical PDF/SVG bytes",
        )
        move_to_archive(
            duplicate_path,
            action_log,
            f"canonical={canonical_path}; old staging copy",
        )
        symlink_alias(old_path, canonical_path, action_log, "legacy RD path")
        symlink_alias(duplicate_path, canonical_path, action_log, "legacy RD staging path")

    # Shared RD asset copies: canonical asset library paths, old project paths retained.
    shared_assets = [
        (
            "RD/AUTOMATIZACION/assets/materials/nacre-n-car_b8578b5d-7676-4518-a3d3-7915e5bc4502/nacre-n-car_4c0f7f89-c6c6-4141-93f2-1ccc5ef73c82.blend",
            "RD/assets/materials/nacre-n-car_b8578b5d-7676-4518-a3d3-7915e5bc4502/nacre-n-car_4c0f7f89-c6c6-4141-93f2-1ccc5ef73c82.blend",
            "RD/New Folder/assets/materials/nacre-n-car_b8578b5d-7676-4518-a3d3-7915e5bc4502/nacre-n-car_4c0f7f89-c6c6-4141-93f2-1ccc5ef73c82.blend",
        ),
        (
            "RD/assets/materials/white-plastic_e7ec0db5-ed39-42d5-a2ab-46166e05293c/white-plastic_2K_55554620-1413-4c1a-b06e-7502f5328d0f.blend",
            "RD/assets/materials/white-plastic_e7ec0db5-ed39-42d5-a2ab-46166e05293c/white-plastic_2K_55554620-1413-4c1a-b06e-7502f5328d0f.blend",
            "RD/New Folder/assets/materials/white-plastic_e7ec0db5-ed39-42d5-a2ab-46166e05293c/white-plastic_2K_55554620-1413-4c1a-b06e-7502f5328d0f.blend",
        ),
    ]
    for source_name, canonical_name, duplicate_name in shared_assets:
        source = ROOT / source_name
        canonical = ROOT / canonical_name
        duplicate = ROOT / duplicate_name
        if source != canonical and source.is_symlink() and canonical.is_file() and duplicate.is_symlink():
            if sha256(source) != sha256(canonical) or sha256(duplicate) != sha256(canonical):
                raise RuntimeError(f"existing shared asset alias verification failed: {source}")
            action_log.append(
                {
                    "operation": "shared_asset_already_applied",
                    "source": str(source),
                    "canonical": str(canonical),
                    "duplicate": str(duplicate),
                    "sha256": sha256(canonical),
                    "note": "resume after a previously verified partial run",
                }
            )
            continue
        if source != canonical:
            validate_file(source)
            validate_file(duplicate)
            if sha256(source) != sha256(duplicate):
                raise RuntimeError(f"hash mismatch in shared asset: {source} != {duplicate}")
            move_canonical(source, canonical, action_log, "shared asset library path")
            symlink_alias(source, canonical, action_log, "legacy automation asset path")
        validate_file(canonical)
        validate_file(duplicate)
        consolidate_pair(canonical, duplicate, action_log, "shared RD asset library canonical")

    # The same logo is a shared asset used by two RD project trees.
    logo_source = ROOT / "RD/AUTOMATIZACION/CUIDARTE 01- BLANCO@LOGO.png"
    logo_duplicate = ROOT / "RD/CREAMFIELDS/CUIDARTE 01- BLANCO@LOGO.png"
    logo_canonical = ROOT / "RD/assets/shared/CUIDARTE 01- BLANCO@LOGO.png"
    if logo_source.is_symlink() and logo_canonical.is_file() and logo_duplicate.is_symlink():
        if sha256(logo_source) != sha256(logo_canonical) or sha256(logo_duplicate) != sha256(logo_canonical):
            raise RuntimeError("existing shared logo alias verification failed")
        action_log.append(
            {
                "operation": "shared_logo_already_applied",
                "source": str(logo_source),
                "canonical": str(logo_canonical),
                "duplicate": str(logo_duplicate),
                "sha256": sha256(logo_canonical),
                "note": "resume after a previously verified partial run",
            }
        )
        write_action_log(action_log)
        return 0
    validate_file(logo_source)
    validate_file(logo_duplicate)
    if sha256(logo_source) != sha256(logo_duplicate):
        raise RuntimeError("hash mismatch in shared logo")
    move_canonical(logo_source, logo_canonical, action_log, "shared RD logo asset")
    move_to_archive(logo_duplicate, action_log, "duplicate shared RD logo")
    symlink_alias(logo_source, logo_canonical, action_log, "legacy automation logo path")
    symlink_alias(logo_duplicate, logo_canonical, action_log, "legacy CREAMFIELDS logo path")

    write_action_log(action_log)
    print(json.dumps({"action_count": len(action_log), "action_log": str(ACTION_LOG)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
