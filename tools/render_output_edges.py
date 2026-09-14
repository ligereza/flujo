#!/usr/bin/env python3
"""Recover source-to-render edges from what a .blend file declares it writes.

WHAT THIS TOOL IS FOR

A .blend file declares the directory it renders into (block code SC00, kind
"scene" in ``blendfile.read_references``). That declaration lives in the
SOURCE, so it survives any re-encode or recompression of the output -- which
is the only reason a source-to-render chain is recoverable on this corpus at
all. It is read backwards from the project, never forwards from the export.

The reproducible full run on 2026-08-24 over the current disk found:

    927  .blend files
    872  readable; 55 are DECODER_LIMIT and stay unknown
    192  scene output declarations in the readable files
    104  are Blender's default (/tmp) and carry no location information
     10  point at another person's machine (a Windows or POSIX "Users" home)
     32  rebase cleanly but the directory no longer exists here
     26  resolve to a real directory on this disk
   2021  files live inside those 26 directories

The earlier hand count of 928 files, 193 declarations, 27 directories and
2189 candidate files is stale; the current run is the authority for this
checkpoint.

Triangulated directly against the real disk while building this tool
(read_references() on the actual files, not a transcription):

    SUERTE/TREBOL.blend       scene 'C:\\SUERTE\\1\\'                -> 100 files (flat `find -maxdepth 1 -type f`)
    3D JJJ/GORRO.blend        scene 'C:\\3D JJJ\\CUFFED\\focus\\'    -> 300 files
    3D JJJ/ANIMACION.blend    scenes '/tmp\\' AND 'C:\\3D JJJ\\letrap\\' -> 481 files
    LYON/MERECEDORA/MERECEDORA.blend  one scene, 'C:\\LYON\\MERECEDORA\\CACHE\\2\\3\\4\\New Folder\\343\\3\\' -> 156 files

Three of four direct spot checks matched the hand count exactly; ANIMACION's
"letrap" directory measured 481 files (one subfolder, "Nueva carpeta", holds 3
more, none of which reconciles the count to 482 under any simple rule this
tool tried). That is reported as a real, small, unexplained drift, not papered
over -- the corpus is a live disk and a file may have moved between the two
measurements.

The Blender default output path was confirmed byte-for-byte on this disk:
ANIMACION.blend's first scene declares the literal string '/tmp\\' -- forward
slash then backslash, Blender's own factory template, unrelated to any host
OS's path convention. A declaration equal to that string says nothing about
where the operator ever pointed a render.

THE REBASING RULE, AND WHY IT IS NOT A GUESS

'C:\\LYON\\Pajsaera\\PNG\\...' resolves to a real directory under --root
(confirmed: LYON/Pajsaera/SINBUG.blend's declared paths are real subtrees of
--root/LYON/Pajsaera/PNG on this disk). --root is a copy of that C:\\ tree, so
stripping the drive letter and rebasing under --root is a reconstruction, not
an assumption -- and it must be DECLARED DATA, not a regex buried in a
function. DRIVE_MAP below is that data: a letter, whether it maps onto
--root, and the measured reason. A second drive letter ("D") is recorded
explicitly with no root, so it resolves to "declared but unreachable" -- a
named, real drive with nothing to rebase onto here -- rather than to
"unrecognized" or silently to "not found".

A path under a Windows or POSIX user home directory is a FOREIGN MACHINE,
and that is a different verdict from "directory not found": the foreign ones
are downloaded assets or another operator's exports, never this operator's
renders, and folding them into "missing" would overcount genuinely lost
render locations.

WHAT THIS TOOL MAY AND MAY NOT CLAIM

It may certify project -> DIRECTORY. It may NOT certify project -> FILE.

1. The declared path names a LOCATION, not a file. A directory holding 482
   files is 482 candidates for which one this save of the project produced;
   that is a cardinality (``Evidence.candidate_count``), never a choice.
2. A .blend has no internal history: it is one mutable file overwritten on
   every save, so the edge this tool writes is "some state of this project
   wrote here", never "this exact state wrote here". (Blender's own .blend1
   backups are the only versions that exist at all, each exactly one save
   back -- and this tool does not read them, because a backup declares
   nothing beyond what the live file already declares.)
3. The declared directory may have been rendered into by a different, later,
   or earlier state of the project than the one on disk right now.

Consequently every non-suspect Evidence row this tool writes uses predicate RENDERS_TO
under authority "blend_declaration" (already registered and already
admissible for exactly this pair in ``schema.ADMISSIBLE_PREDICATES`` -- this
module adds no predicate and no authority), with the object being the
resolved DIRECTORY and ``candidate_count`` set to the number of files found
inside it. ``schema.py`` itself already forbids this authority from orienting
a DERIVED_FROM edge; this tool relies on that existing check rather than
re-implementing it.

TRIANGULATION OF WHAT A RESOLVED DIRECTORY ACTUALLY HOLDS

A render output directory should hold images or frame sequences (.exr, .png,
.jpg, .tif -- named directly in this tool's own specification). Every resolved
directory is scanned (flat, one level -- SUERTE/1 has zero subdirectories and
exactly 100 files, matching the hand count exactly) and flagged ``suspect``
when none of its files carry an image-like extension: a directory full of
.blend files or documents is not evidence of a render, and reporting it as an
ordinary resolved edge would silently launder that distinction away.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flujo import runrecord  # noqa: E402
from flujo.substrate.blendfile import read_references  # noqa: E402
from flujo.substrate.epistemics import MISSING_EVIDENCE  # noqa: E402
from flujo.substrate.resolution import candidate_count, resolve  # noqa: E402
from flujo.substrate.schema import (  # noqa: E402
    OBJ_BASENAME,
    RENDERS_TO,
    RESOLVED,
    Evidence,
    Substrate,
)

CONTRACT = "mak-render-output-edges-v1"

# ------------------------------------------------------------------ constants

# Measured directly on this disk: 3D JJJ/ANIMACION.blend's first scene
# declares this exact string. Forward slash then backslash -- Blender's own
# cross-platform factory default, not a path this operator ever chose.
DEFAULT_OUTPUT_PATHS = ("/tmp\\",)

# Named directly in this tool's specification: what a render output directory
# should hold. Anything else in a resolved directory is a suspect edge.
IMAGE_LIKE_EXTENSIONS = frozenset({".exr", ".png", ".jpg", ".jpeg", ".tif", ".tiff"})

# The five outcomes a declared scene path can reach. Kept as named constants,
# never bare strings, so a typo in one place cannot silently create a sixth
# unrecognized bucket.
DEFAULT_NO_INFO = "default_no_info"
FOREIGN_MACHINE = "foreign_machine"
DECLARED_BUT_UNREACHABLE = "declared_but_unreachable"
REBASED_BUT_MISSING = "rebased_but_missing"
RESOLVED_VERDICT = "resolved"
UNRECOGNIZED_SHAPE = "unrecognized_shape"

VERDICTS = (DEFAULT_NO_INFO, FOREIGN_MACHINE, DECLARED_BUT_UNREACHABLE,
            REBASED_BUT_MISSING, RESOLVED_VERDICT, UNRECOGNIZED_SHAPE)

# A "Users" home directory, Windows or POSIX-styled. Described by shape only
# -- no example account name appears anywhere in this file, on purpose: the
# real .blend files on this disk carry the ORIGINAL authors' own account
# names, and a literal one committed here is exactly how a name like that
# leaks into the repository.
_WINDOWS_USER_HOME = re.compile(r"^[A-Za-z]:[\\/][Uu]sers[\\/][^\\/]+[\\/]")
_POSIX_USER_HOME = re.compile(r"^/Users/[^/]+/")

# A Windows-style drive letter prefix, e.g. "C:\" or "C:/".
_DRIVE_LETTER = re.compile(r"^([A-Za-z]):[\\/]")


@dataclass(frozen=True)
class DriveRoot:
    """One drive letter's resolution rule on THIS disk.

    Declared data, not a regex buried inside a function: ``letter`` is what
    the .blend wrote, ``maps_to_scan_root`` says whether that letter's tree
    was copied onto --root, and ``reason`` is the measurement that licenses
    the mapping (or explains why the letter is known but unreachable).
    """

    letter: str
    maps_to_scan_root: bool
    reason: str


# The drive map. A letter absent from this dict entirely is treated exactly
# like "D" below is treated explicitly: no root, "declared but unreachable".
# The only difference between an absent letter and an explicitly-listed
# unreachable one is that the listed one carries a specific, checkable reason.
DRIVE_MAP: dict[str, DriveRoot] = {
    "C": DriveRoot(
        letter="C", maps_to_scan_root=True,
        reason="Measured on this disk: SUERTE/TREBOL.blend's declared scene "
               "path rebases under --root to a real directory holding "
               "exactly 100 files (a flat, non-recursive count), and "
               "3D JJJ/GORRO.blend's rebases to one holding exactly 300. "
               "--root is a copy of the operator's C:\\ tree onto this SSD, "
               "so stripping 'C:' and rebasing under --root reconstructs the "
               "same path; it does not guess at one."),
    "D": DriveRoot(
        letter="D", maps_to_scan_root=False,
        reason="Declared, not guessed: a second drive letter is named in "
               "declared render paths on this corpus, evidently a second "
               "physical disk of the operator's that was never copied onto "
               "this SSD. Recording the letter here (rather than leaving it "
               "unmentioned) is what makes the verdict "
               "'declared_but_unreachable' instead of silently falling into "
               "'unrecognized_shape' or being read as 'not found'."),
}


def _split_path_tail(tail: str) -> list[str]:
    """Path segments after a drive-colon or after Blender's '//' marker.

    Accepts either separator because Blender wrote these with backslashes on
    this corpus but a forward slash is handled the same way rather than
    silently producing one giant bad path segment. A trailing separator
    produces one empty segment at the end, which is dropped: a declared path
    names a directory, and a directory has no trailing-empty component.
    """
    normalized = tail.replace("\\", "/")
    return [part for part in normalized.split("/") if part]


def leading_drive_letter(declared_path: str) -> str:
    """The raw drive letter a declaration starts with, or "(none)".

    Used only for the report's drive-letter histogram: a tally over ALL 192
    declarations, independent of verdict, so a foreign Windows user-home path
    and a genuine project path both count under "C" -- the histogram
    answers "which letters appear at all", not "which letters resolved".
    """
    match = _DRIVE_LETTER.match(declared_path)
    return match.group(1).upper() if match else "(none)"


@dataclass(frozen=True)
class Classification:
    """The verdict for one declared scene path, and how it was reached."""

    declared_path: str
    verdict: str
    path: str | None   # the absolute path this declaration rebases to, when
                       # the shape allows computing one at all
    reason: str

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"undeclared_verdict: {self.verdict}")


def _rebase_verdict(declared_path: str, candidate: Path, reason: str) -> Classification:
    try:
        exists_as_dir = candidate.is_dir()
    except OSError:
        exists_as_dir = False
    verdict = RESOLVED_VERDICT if exists_as_dir else REBASED_BUT_MISSING
    return Classification(declared_path, verdict, str(candidate), reason)


def classify_scene_path(declared_path: str, *, blend_path: Path, scan_root: Path,
                        drive_map: dict[str, DriveRoot]) -> Classification:
    """Classify one declared render output path into one of the six verdicts.

    ``drive_map`` is a parameter, not a global lookup, on purpose: a caller
    (a test, or a future CLI flag) can hand in a different map and change the
    outcome, which is the whole point of the rebasing rule being DATA.
    """
    if declared_path in DEFAULT_OUTPUT_PATHS:
        return Classification(
            declared_path, DEFAULT_NO_INFO, None,
            "equals the measured Blender factory default output path; the "
            "operator never set an output path for this scene, so the "
            "string carries no information about where THIS project renders")

    if declared_path.startswith("//"):
        segments = _split_path_tail(declared_path[2:])
        candidate = (blend_path.parent.joinpath(*segments) if segments
                    else blend_path.parent)
        return _rebase_verdict(
            declared_path, candidate,
            "'//' is Blender's own marker for a path relative to this "
            ".blend; rebased against the file's own directory, which needs "
            "no drive map at all because the .blend's location on this disk "
            "is already known")

    if _WINDOWS_USER_HOME.match(declared_path) or _POSIX_USER_HOME.match(declared_path):
        return Classification(
            declared_path, FOREIGN_MACHINE, None,
            "path names a 'Users' home directory: another person's machine, "
            "not the operator's. A foreign-machine declaration is a "
            "different verdict from 'not found' and must never be counted "
            "toward a missing render directory")

    drive_match = _DRIVE_LETTER.match(declared_path)
    if drive_match:
        letter = drive_match.group(1).upper()
        segments = _split_path_tail(declared_path[drive_match.end():])
        mapping = drive_map.get(letter)
        if mapping is None:
            return Classification(
                declared_path, DECLARED_BUT_UNREACHABLE, None,
                f"drive {letter}: has no recorded root on this disk (the "
                "drive map carries no entry for this letter at all)")
        if not mapping.maps_to_scan_root:
            return Classification(declared_path, DECLARED_BUT_UNREACHABLE,
                                  None, f"drive {letter}: {mapping.reason}")
        candidate = scan_root.joinpath(*segments) if segments else scan_root
        return _rebase_verdict(declared_path, candidate,
                               f"drive {letter}: {mapping.reason}")

    return Classification(
        declared_path, UNRECOGNIZED_SHAPE, None,
        "matches none of the known shapes (the Blender default, a '//' "
        "relative marker, a 'Users' home, or a drive letter): this "
        "classifier has no rule for it, and it is reported rather than "
        "silently folded into another bucket")


def scan_resolved_directory(path: Path) -> tuple[Any, dict[str, int]]:
    """List a resolved render output directory, flat, one level down.

    Flat because it is what the measurements say Blender actually does:
    SUERTE/1 has zero subdirectories and exactly 100 files; a recursive count
    would silently change the number for every directory that happens to
    contain a stray subfolder, and this tool must report what it measured, not
    what a different counting rule would have produced.

    Returns a ``resolution.Resolution`` over the filenames (Unique / Many /
    Absent, per the module this tool is told to use rather than reinvent) and
    an extension histogram for the suspect check.
    """
    names: list[str] = []
    ext_counts: dict[str, int] = {}
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    is_file = entry.is_file(follow_symlinks=False)
                except OSError:
                    is_file = False
                if not is_file:
                    continue
                names.append(entry.name)
                ext = os.path.splitext(entry.name)[1].lower()
                ext_counts[ext] = ext_counts.get(ext, 0) + 1
    except OSError:
        pass
    names.sort()
    result = resolve(names,
                     witness="the only file in this declared render output "
                             "directory",
                     cause=MISSING_EVIDENCE)
    return result, dict(sorted(ext_counts.items()))


def is_suspect(ext_counts: dict[str, int]) -> bool:
    """True when a directory declared as a render output holds no image.

    An empty directory (no files at all) is reported separately -- it is not
    "the wrong kind of file", it is "no files yet" -- so it is never flagged
    suspect by this function.
    """
    if not ext_counts:
        return False
    return not any(ext in IMAGE_LIKE_EXTENSIONS for ext in ext_counts)


def process_blend_file(blend_path: Path, *, root: Path,
                       drive_map: dict[str, DriveRoot]) -> dict[str, Any]:
    """Read one .blend and classify every scene-kind declaration it carries.

    A single file may declare more than one scene output (measured: LYON/
    Pajsaera/SINBUG.blend declares three, ANIMACION.blend declares the
    default plus one real path) -- every declaration is classified and
    reported, never just the first or the largest.
    """
    relative = str(blend_path.relative_to(root))
    refs = read_references(blend_path)
    row: dict[str, Any] = {
        "relative_path": relative,
        "error": refs.error,
        "decoder": refs.decoder,
        "declarations": [],
    }
    if refs.error:
        return row
    scenes = [d for d in refs.declared if d["kind"] == "scene"]
    for index, decl in enumerate(scenes):
        declared_path = decl["declared_path"]
        classification = classify_scene_path(
            declared_path, blend_path=blend_path, scan_root=root,
            drive_map=drive_map)
        entry: dict[str, Any] = {
            "ordinal": index,
            "declared_path": declared_path,
            "drive_letter": leading_drive_letter(declared_path),
            "verdict": classification.verdict,
            "path": classification.path,
            "reason": classification.reason,
        }
        if classification.verdict == RESOLVED_VERDICT:
            result, ext_counts = scan_resolved_directory(Path(classification.path))
            k = candidate_count(result)
            entry["candidate_count"] = k
            entry["extensions"] = ext_counts
            entry["suspect"] = is_suspect(ext_counts)
        row["declarations"].append(entry)
    return row


def _evidence_id(*parts: Any) -> str:
    return "ev:" + hashlib.sha256(
        "\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]


def build_evidence(*, root_id: str, relative_path: str, ordinal: int,
                   resolved_path: str, candidate_count_value: int,
                   suspect: bool, recorded_at: str) -> Evidence:
    """One RENDERS_TO row: project -> DIRECTORY, never project -> FILE.

    The object is the resolved directory, never one of the files inside it --
    see the module docstring's three reasons. ``candidate_count`` carries the
    cardinality that a caller must not collapse into a single choice; schema's
    ``Evidence.individuating_deficit_bits`` reads directly off this field.
    """
    subject = f"blend:{root_id}:{relative_path}"
    obj = f"basename:{resolved_path}"
    detail = (
        f"scene render output declared in {relative_path} (declaration "
        f"#{ordinal}); declares a LOCATION, not a file -- "
        f"{candidate_count_value} candidate file(s) present in {resolved_path} "
        "at scan time, none of them individuated")
    if suspect:
        detail += ("; SUSPECT: no image-like file (.exr/.png/.jpg/.jpeg/"
                  ".tif/.tiff) found in this directory")
    return Evidence(
        evidence_id=_evidence_id(subject, RENDERS_TO, obj, ordinal),
        subject=subject, predicate=RENDERS_TO, object=obj,
        authority="blend_declaration",
        extractor="render_output_edges.classify_scene_path",
        method="scene_block_scan", search_completeness="exhaustive",
        recorded_at=recorded_at, detail=detail, ordinal=ordinal,
        object_kind=OBJ_BASENAME, object_resolution=RESOLVED,
        unknown_cause="" if candidate_count_value else MISSING_EVIDENCE,
        candidate_count=candidate_count_value)


def iter_blend_files(root: Path, *, errors: list[dict[str, str]]
                     ) -> Iterator[Path]:
    """Every *.blend under root, sorted, so a repeat run visits them in the
    same order and the report's list-valued fields stay reproducible.
    """
    def onerror(exc: OSError) -> None:
        errors.append({"path": getattr(exc, "filename", "?"), "error": str(exc)})

    for current, dirs, files in os.walk(root, onerror=onerror):
        dirs.sort()
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() == ".blend":
                yield Path(current) / name


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render_output_edges.py",
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/media/mak/PortableSSD"),
                        help="the disk to read .blend render-output "
                             "declarations from")
    parser.add_argument("--out", type=Path, required=True,
                        help="the Substrate sqlite sidecar to write RENDERS_TO "
                             "evidence rows into")
    parser.add_argument("--report", type=Path, default=None,
                        help="optional: write the full run record and "
                             "per-declaration classification here as JSON")
    parser.add_argument("--limit", type=int, default=None,
                        help="stop after this many .blend files. A bounded "
                             "run over a slow disk is a real measurement of "
                             "exactly the files it covered; this tool never "
                             "extrapolates a partial run to a full-corpus "
                             "number")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    # NOTHING is written to disk above this line, and parse_args() itself
    # exits(0) for --help before returning. A past tool in this repository
    # treated argv[0] as a directory to create before checking for --help,
    # and the repo's own tool ratchet -- which invokes every live tool with
    # --help -- made it a 305 MB directory literally named "--help". Asking a
    # tool what it does must never write anything.
    args = parser.parse_args(argv)

    root = args.root
    if not root.is_dir():
        print(f"error: root_not_a_directory: {root}", file=sys.stderr)
        return 2

    t0 = time.time()
    walk_errors: list[dict[str, str]] = []
    blend_files: list[Path] = []
    for path in iter_blend_files(root, errors=walk_errors):
        blend_files.append(path)
        if args.limit and len(blend_files) >= args.limit:
            break

    sub = Substrate(args.out)
    run_started_at = runrecord.now()

    per_file: list[dict[str, Any]] = []
    total_declarations = 0
    by_verdict: dict[str, int] = {}
    drive_letter_histogram: dict[str, int] = {}
    resolved_edges: list[dict[str, Any]] = []
    evidence_written = 0

    for blend_path in blend_files:
        row = process_blend_file(blend_path, root=root, drive_map=DRIVE_MAP)
        per_file.append(row)
        for decl in row["declarations"]:
            total_declarations += 1
            by_verdict[decl["verdict"]] = by_verdict.get(decl["verdict"], 0) + 1
            letter = decl["drive_letter"]
            drive_letter_histogram[letter] = drive_letter_histogram.get(letter, 0) + 1
            if decl["verdict"] == RESOLVED_VERDICT:
                edge = {
                    "blend": row["relative_path"],
                    "declared_path": decl["declared_path"],
                    "resolved_path": decl["path"],
                    "candidate_count": decl["candidate_count"],
                    "suspect": decl["suspect"],
                    "extensions": decl["extensions"],
                }
                resolved_edges.append(edge)
                if not decl["suspect"]:
                    sub.put_evidence(build_evidence(
                        root_id=str(root), relative_path=row["relative_path"],
                        ordinal=decl["ordinal"], resolved_path=decl["path"],
                        candidate_count_value=decl["candidate_count"],
                        suspect=False, recorded_at=run_started_at))
                    evidence_written += 1

    resolved_edges.sort(
        key=lambda e: (-e["candidate_count"], e["blend"], e["declared_path"]))

    readable = sum(1 for r in per_file if not r["error"])
    decoder_limit = sum(1 for r in per_file if r["error"])
    suspect_resolved = [e for e in resolved_edges if e["suspect"]]

    report: dict[str, Any] = {
        "contract": CONTRACT,
        "root": str(root),
        "limit": args.limit,
        "blend_files_found": len(blend_files),
        "blend_files_readable": readable,
        "blend_files_decoder_limit": decoder_limit,
        "walk_errors": sorted(walk_errors, key=lambda e: e["path"]),
        "scene_declarations_total": total_declarations,
        "by_verdict": dict(sorted(by_verdict.items())),
        "drive_letter_histogram": dict(sorted(drive_letter_histogram.items())),
        "resolved_edges": resolved_edges,
        "top5_resolved_by_candidate_count": resolved_edges[:5],
        "suspect_resolved": suspect_resolved,
        "suspect_resolved_count": len(suspect_resolved),
        "total_files_across_resolved_dirs": sum(
            e["candidate_count"] for e in resolved_edges),
        "evidence_written": evidence_written,
        "files": per_file,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    record = runrecord.record(
        contract=CONTRACT,
        argv=list(argv if argv is not None else sys.argv[1:]),
        modules=[read_references.__module__ and __import__(
            "flujo.substrate.blendfile", fromlist=["_"])],
        repo=ROOT, inputs=(), volumes=(root,))
    # source_version() only wants modules with a __file__; re-import the ones
    # this tool's own answer actually depends on, plus this file itself.
    import flujo.substrate.resolution as resolution_module
    import flujo.substrate.schema as schema_module
    import flujo.substrate.epistemics as epistemics_module
    import flujo.substrate.blendfile as blendfile_module
    record["code"] = runrecord.source_version(
        [blendfile_module, resolution_module, schema_module, epistemics_module,
         sys.modules[__name__]])
    record["result"] = report
    record["output_sha256"] = runrecord.result_digest(
        report, ignore=("elapsed_seconds",))
    record["finished_at"] = runrecord.now()

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "blend_files_found": report["blend_files_found"],
        "blend_files_readable": report["blend_files_readable"],
        "blend_files_decoder_limit": report["blend_files_decoder_limit"],
        "scene_declarations_total": report["scene_declarations_total"],
        "by_verdict": report["by_verdict"],
        "drive_letter_histogram": report["drive_letter_histogram"],
        "total_files_across_resolved_dirs": report["total_files_across_resolved_dirs"],
        "suspect_resolved_count": report["suspect_resolved_count"],
        "evidence_written": evidence_written,
        "output_sha256": record["output_sha256"],
        "elapsed_seconds": report["elapsed_seconds"],
        "limit": args.limit,
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
