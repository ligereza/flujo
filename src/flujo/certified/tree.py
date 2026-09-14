"""Summary trees over the real corpora, built from natural containment only.

There is no clustering here and no similarity. The hierarchy is the one the
corpus already has -- container root, path segments, project on the SSD; surface,
month, file in the Instagram export -- because a grouping invented to improve
pruning would be a grouping whose members were never shown to belong together.

Every leaf records, per authority, whether that authority produced evidence for
it. That per-member coverage is what lets ``certify`` refuse a negative built
over a subset, and it is the reason these builders are more careful than a scan
needs to be.

Read-only. Nothing here writes to the index, the export, or the repository.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .contracts import DECLARED_3D_FORMATS
from .summary import Summary, empty, from_member, join_all

SSD_INDEX = Path("/home/mak/labs/portable-ssd-index-20260813/archivo_index.sqlite")
IG_MEDIA = Path("/home/mak/portfolio_media/media")
REPO = Path(__file__).resolve().parents[3]
DISCOGRAPHIES = REPO / "data" / "artist_discographies.json"

IG_SURFACES = ("posts", "reels", "igtv", "stories", "archived_posts", "other",
               "_contact_sheets")
MONTH = re.compile(r"^\d{6}$")
MEDIA_ID = re.compile(r"^(\d{10,})")
TRACK_NUMBER = re.compile(r"^\s*\d{1,2}\s*[-_. ]\s*")
ARTICLES = ("la ", "el ", "los ", "las ", "the ")


class TreeError(ValueError):
    """A corpus could not be read as the declared input."""


@dataclass
class TreeNode:
    """One node of the hierarchy: a scope, its summary, and its children."""

    scope: str
    summary: Summary
    children: list["TreeNode"] = field(default_factory=list)
    payload: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def descendants(self) -> Iterable["TreeNode"]:
        yield self
        for child in self.children:
            yield from child.descendants()

    def depth(self) -> int:
        return 1 + max((c.depth() for c in self.children), default=0)

    def shape(self) -> dict[str, Any]:
        nodes = list(self.descendants())
        return {
            "scope": self.scope,
            "nodes": len(nodes),
            "leaves": sum(1 for n in nodes if n.is_leaf),
            "depth": self.depth(),
            "members": self.summary.n_members,
        }


def _fold(scope: str, children: Sequence[TreeNode]) -> TreeNode:
    return TreeNode(scope=scope,
                    summary=join_all((c.summary for c in children), scope=scope),
                    children=list(children))


# ------------------------------------------------------------------ discography

def _normalise_title(text: str) -> str:
    out = TRACK_NUMBER.sub("", str(text)).strip().casefold()
    out = re.sub(r"\.(mov|mp4|aep|blend|png|jpg)$", "", out)
    out = re.sub(r"[^a-z0-9 ]+", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    for article in ARTICLES:
        if out.startswith(article):
            out = out[len(article):]
    return out


def load_discographies(path: Path | None = None) -> dict[str, dict[str, str]]:
    """container -> {normalised title: canonical title}. Absence is not evidence.

    A container missing from this map means the lookup was never performed, which
    is why every project under such a container is counted as an unresolved name
    rather than as a non-track.
    """
    target = path or DISCOGRAPHIES
    if not target.is_file():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for container, entry in payload.get("containers", {}).items():
        titles = {}
        for track in entry.get("tracks", ()):
            title = str(track.get("title") or "")
            if title:
                titles[_normalise_title(title)] = title
        if titles:
            out[container] = titles
    return out


def _resolve_track(container: str, project_path: str,
                   discs: Mapping[str, Mapping[str, str]]) -> str | None:
    titles = discs.get(container)
    if not titles:
        return None
    leaf = project_path.rstrip("/").split("/")[-1]
    key = _normalise_title(leaf)
    if not key:
        return None
    if key in titles:
        return titles[key]
    # A misspelling is admitted only when one catalogue title contains the whole
    # observed name or vice versa, and only when exactly one does. Two candidates
    # is a tie and a tie abstains.
    hits = [canon for norm, canon in titles.items()
            if len(key) >= 5 and (key in norm or norm in key)]
    return hits[0] if len(hits) == 1 else None


def _virtualenv_ancestor(path: str) -> bool:
    parts = path.split(os.sep)
    for index in range(len(parts) - 1, 1, -1):
        candidate = os.sep.join(parts[:index])
        if not candidate:
            continue
        try:
            if os.path.isfile(os.path.join(candidate, "pyvenv.cfg")):
                return True
        except OSError:
            return False
    return any(seg in ("site-packages", "dist-packages") for seg in parts)


# ------------------------------------------------------------------- SSD corpus

def build_ssd_tree(index: Path | str | None = None, *, scope: str | None = None,
                   discographies: Mapping[str, Mapping[str, str]] | None = None
                   ) -> TreeNode:
    """A tree over the portable SSD index. One member per project row.

    The unit is the project rather than the asset, because every query in the
    contract set asks about a work or a commission, never about a byte. Asset
    level facts are folded into each project's leaf summary.
    """
    path = Path(index) if index else SSD_INDEX
    if not path.is_file():
        raise TreeError(f"ssd_index_missing: {path}")
    discs = dict(discographies) if discographies is not None else load_discographies()

    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        where, params = "", []
        if scope:
            where = " WHERE container_root = ?"
            params = [scope]
        projects = con.execute(
            "SELECT project_id, project_path, container_root, asset_count, bytes, "
            "dimensionality FROM projects" + where + " ORDER BY project_path",
            params).fetchall()
        if not projects:
            raise TreeError(f"ssd_index_has_no_projects_for_scope: {scope!r}")
        ids = [str(r["project_id"]) for r in projects]
        exts: dict[str, set[str]] = {i: set() for i in ids}
        hashes: dict[str, set[str]] = {i: set() for i in ids}
        full_hashed: dict[str, int] = {i: 0 for i in ids}
        mtimes: dict[str, list[int]] = {i: [] for i in ids}
        chunk = 400
        for start in range(0, len(ids), chunk):
            block = ids[start:start + chunk]
            marks = ",".join("?" * len(block))
            for row in con.execute(
                f"SELECT m.project_id, a.extension, a.full_sha256, a.mtime_ns "
                f"FROM project_members m JOIN assets a ON a.asset_id = m.asset_id "
                f"WHERE m.project_id IN ({marks})", block):
                pid = str(row["project_id"])
                ext = (row["extension"] or "").lower()
                if ext:
                    exts[pid].add(ext)
                if row["full_sha256"]:
                    hashes[pid].add(str(row["full_sha256"]))
                    full_hashed[pid] += 1
                if row["mtime_ns"]:
                    mtimes[pid].append(int(row["mtime_ns"]))
    finally:
        con.close()

    leaves: list[TreeNode] = []
    for row in projects:
        pid = str(row["project_id"])
        project_path = str(row["project_path"])
        container = str(row["container_root"])
        extensions = exts[pid]
        properties: list[str] = []
        if extensions & DECLARED_3D_FORMATS:
            properties.append("has_3d_format")
        if _virtualenv_ancestor(project_path):
            properties.append("in_virtualenv")
        # A project counts as fully hashed only when EVERY asset in it is; a
        # sample hash is not an identity and must not be promoted to one.
        if row["asset_count"] and full_hashed[pid] == int(row["asset_count"]):
            properties.append("has_full_hash")

        authorities = ["ssd_index_paths", "ssd_index_extensions"]
        sets: dict[str, Iterable] = {"container_root": {container},
                                     "extension": extensions,
                                     "sha256": hashes[pid]}
        track = _resolve_track(container, project_path, discs)
        if container in discs:
            authorities.append("artist_discography")
            if track:
                sets["track_id"] = {track}
            else:
                properties.append("unmatched_name")
        else:
            properties.append("unmatched_name")

        values: dict[str, tuple[float, str]] = {}
        if mtimes[pid]:
            authorities.append("filesystem_mtime")
            values["date"] = (float(min(mtimes[pid])) / 1e9, "filesystem_mtime")
        else:
            properties.append("undated")

        leaves.append(TreeNode(
            scope=project_path,
            summary=from_member(project_path, authorities_covering=authorities,
                                sets=sets, properties=properties, values=values,
                                provenance={"ssd_index"}),
            payload={"project_id": pid, "container_root": container,
                     "bytes": int(row["bytes"] or 0),
                     "assets": int(row["asset_count"] or 0),
                     "index_dimensionality": row["dimensionality"]},
        ))
    return _build_path_trie(leaves, root_scope=scope or "SSD")


def _build_path_trie(leaves: Sequence[TreeNode], *, root_scope: str) -> TreeNode:
    """Group leaves by their real path segments. No invented grouping."""
    if not leaves:
        return TreeNode(scope=root_scope, summary=empty(root_scope))

    def group(nodes: Sequence[TreeNode], depth: int, prefix: str) -> TreeNode:
        buckets: dict[str, list[TreeNode]] = {}
        terminal: list[TreeNode] = []
        for node in nodes:
            parts = node.scope.split("/")
            if len(parts) <= depth + 1:
                terminal.append(node)
            else:
                buckets.setdefault(parts[depth], []).append(node)
        children: list[TreeNode] = list(terminal)
        for segment, bucket in sorted(buckets.items()):
            child_prefix = f"{prefix}/{segment}" if prefix else segment
            if len(bucket) == 1:
                children.append(bucket[0])
            else:
                children.append(group(bucket, depth + 1, child_prefix))
        if len(children) == 1 and prefix:
            return children[0]
        return _fold(prefix or root_scope, children)

    by_root: dict[str, list[TreeNode]] = {}
    for node in leaves:
        by_root.setdefault(node.scope.split("/")[0], []).append(node)
    roots = [group(bucket, 1, root)
             for root, bucket in sorted(by_root.items())]
    return _fold(root_scope, roots) if len(roots) != 1 else roots[0]


# -------------------------------------------------------------------- IG corpus

def build_ig_tree(media_root: Path | str | None = None) -> TreeNode:
    """A tree over the Instagram export. One member per file.

    Depth is surface then month, both of which are directories the export itself
    created. Contact sheets are kept as their own surface because they are
    derivatives, and folding them into their originals would erase a distinction
    the reconciliation measured: 8 media ids appear in two surfaces and all 8 are
    an original beside its generated sheet.
    """
    root = Path(media_root) if media_root else IG_MEDIA
    if not root.is_dir():
        raise TreeError(f"ig_media_root_missing: {root}")

    surfaces: list[TreeNode] = []
    for surface in sorted(p.name for p in root.iterdir() if p.is_dir()):
        surface_dir = root / surface
        months: dict[str, list[TreeNode]] = {}
        loose: list[TreeNode] = []
        for current, _dirs, files in os.walk(surface_dir):
            rel = os.path.relpath(current, surface_dir)
            bucket = rel.split(os.sep)[0] if rel != "." else ""
            for name in sorted(files):
                full = Path(current) / name
                try:
                    stat = full.stat()
                except OSError:
                    continue
                match = MEDIA_ID.match(name)
                authorities = ["ig_export_surfaces", "operator_surface_rule",
                               "filesystem_mtime"]
                properties: list[str] = []
                values: dict[str, tuple[float, str]] = {}
                if MONTH.fullmatch(bucket):
                    authorities.append("ig_export_month_folders")
                    values["date"] = (float(int(bucket[:4]) * 12 + int(bucket[4:6])),
                                      "ig_export_month_folders")
                else:
                    properties.append("undated")
                scope = f"{surface}/{bucket}/{name}" if bucket else f"{surface}/{name}"
                node = TreeNode(
                    scope=scope,
                    summary=from_member(
                        scope, authorities_covering=authorities,
                        sets={"surface": {surface},
                              "media_id": {match.group(1)} if match else set()},
                        properties=properties, values=values,
                        provenance={"ig_export"}),
                    payload={"bytes": stat.st_size, "surface": surface,
                             "month": bucket or None},
                )
                (months.setdefault(bucket, []) if bucket else loose).append(node)
        children = list(loose)
        for month, bucket in sorted(months.items()):
            children.append(_fold(f"{surface}/{month}", bucket))
        if children:
            surfaces.append(_fold(surface, children))
    if not surfaces:
        raise TreeError(f"ig_media_root_empty: {root}")
    return _fold("IG", surfaces)
