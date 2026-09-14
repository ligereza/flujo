"""Attack the identity escalation: cheap evidence may reject, never accept.

The whole tool rests on one asymmetry, and each test below fails if it is
inverted or shortcut:

- a size difference IS a different file, and it costs nothing to see.
- two files with different content ARE different, and only a full read can
  say so with certainty on this corpus (see the module docstring for why a
  cheaper tail probe was measured and deleted: it resolved 0 of 4104 disputed
  assets for 197522805 bytes read).
- two files with identical content are the same file, but only after a full
  digest of BOTH has actually been computed -- never assumed from a cheap
  partial agreement.
- a run that hits its byte budget must say so per asset. A tool that quietly
  drops work reads as "covered everything" to whoever consumes its output.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "resolve_identity_ties.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("identity_ties_mod", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ties = load_tool()


def member(name: str, size: int, *, root: str = "R", sample: str = "S"):
    return {
        "asset_id": hashlib.sha256(name.encode()).hexdigest(),
        "relative_path": name, "extension": Path(name).suffix,
        "bytes": size, "sample_sha256": sample,
        "container_root": root, "is_appledouble": False,
    }


def write(root: Path, name: str, body: bytes) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


BIG = 1 << 18  # bigger than the window a deleted stage used to special-case


def test_size_difference_certifies_distinct_for_free(tmp_path: Path) -> None:
    write(tmp_path, "A/a.bin", b"x" * 10)
    write(tmp_path, "B/b.bin", b"x" * 20)
    out = ties.resolve({"S": [member("A/a.bin", 10, root="A"),
                             member("B/b.bin", 20, root="B")]},
                       tmp_path, full_budget=None)
    assert out["stats"]["stage0_resolved"] == 2
    assert out["stats"]["bytes_read_stage1"] == 0
    assert {m["verdict"] for m in out["assets"]} == {ties.CERTIFIED_DISTINCT}


def test_two_objects_with_different_bytes_are_certified_distinct(tmp_path: Path) -> None:
    write(tmp_path, "A/a.bin", b"P" * BIG + b"ENDING01")
    write(tmp_path, "B/b.bin", b"P" * BIG + b"ENDING02")
    size = BIG + 8
    out = ties.resolve({"S": [member("A/a.bin", size, root="A"),
                             member("B/b.bin", size, root="B")]},
                       tmp_path, full_budget=None)
    stats = out["stats"]
    # The only paid stage is the full read; there is no cheaper stage left
    # that could have found this, and none is claimed.
    assert stats["bytes_read_stage1"] == size * 2
    assert {m["verdict"] for m in out["assets"]} == {ties.CERTIFIED_DISTINCT}
    assert all(m["content_id"] is None for m in out["assets"])


def test_two_objects_with_identical_bytes_are_certified_same_once(tmp_path: Path) -> None:
    body = bytes(range(256)) * (BIG // 256)
    write(tmp_path, "A/a.bin", body)
    write(tmp_path, "B/b.bin", body)
    out = ties.resolve({"S": [member("A/a.bin", len(body), root="A"),
                             member("B/b.bin", len(body), root="B")]},
                       tmp_path, full_budget=None)
    assert {m["verdict"] for m in out["assets"]} == {ties.CERTIFIED_SAME}
    ids = {m["content_id"] for m in out["assets"]}
    assert len(ids) == 1 and next(iter(ids)).startswith("sha256:")
    klasses = ties.build_classes(out["assets"])
    assert len(klasses) == 1
    klass = klasses[0]
    assert klass["member_count"] == 2
    assert klass["reclaimable_bytes"] == len(body)      # one of the two, counted once
    assert klass["crosses_roots"] is True
    assert klass["distinct_roots"] == 2


def test_small_file_is_certified_with_a_true_full_digest(tmp_path: Path) -> None:
    """Under 64 KiB used to get a tail-window shortcut; that stage is gone.

    This must still pass, and the content id must still equal sha256 of the
    real bytes, so the deleted shortcut cannot come back disguised as a
    partial read.
    """
    body = b"tiny-and-identical"
    write(tmp_path, "A/a.txt", body)
    write(tmp_path, "B/b.txt", body)
    out = ties.resolve({"S": [member("A/a.txt", len(body), root="A"),
                             member("B/b.txt", len(body), root="B")]},
                       tmp_path, full_budget=None)
    assert {m["verdict"] for m in out["assets"]} == {ties.CERTIFIED_SAME}
    assert all(m["resolved_at_stage"] == 1 for m in out["assets"])
    expect = "sha256:" + hashlib.sha256(body).hexdigest()
    assert {m["content_id"] for m in out["assets"]} == {expect}


def test_budget_exhaustion_is_recorded_per_asset(tmp_path: Path) -> None:
    tail = b"z" * (1 << 12)
    write(tmp_path, "A/a.bin", b"1" * BIG + tail)
    write(tmp_path, "B/b.bin", b"2" * BIG + tail)
    size = BIG + len(tail)
    out = ties.resolve({"S": [member("A/a.bin", size, root="A"),
                             member("B/b.bin", size, root="B")]},
                       tmp_path, full_budget=1)
    assert out["stats"]["unresolved_over_budget"] == 2
    for asset in out["assets"]:
        assert asset["verdict"] == ties.UNRESOLVED
        # A cause, not a bare unknown, because the remedy differs per cause.
        assert asset["unknown_cause"]
        assert asset["note"] == "full_hash_budget_exhausted"


def test_missing_file_is_unresolved_not_distinct(tmp_path: Path) -> None:
    write(tmp_path, "A/a.bin", b"x" * BIG)
    out = ties.resolve({"S": [member("A/a.bin", BIG, root="A"),
                             member("B/gone.bin", BIG, root="B")]},
                       tmp_path, full_budget=None)
    verdicts = {m["relative_path"]: m["verdict"] for m in out["assets"]}
    assert verdicts["B/gone.bin"] == ties.UNRESOLVED
    assert verdicts["B/gone.bin"] != ties.CERTIFIED_DISTINCT
    assert out["stats"]["unreadable"] == 1


def test_duplicate_inside_one_root_is_not_a_cross_root_claim(tmp_path: Path) -> None:
    """Only a cross-root duplicate is evidence about two commissions."""
    body = b"same" * (BIG // 4)
    write(tmp_path, "A/one/x.bin", body)
    write(tmp_path, "A/two/y.bin", body)
    out = ties.resolve({"S": [member("A/one/x.bin", len(body), root="A"),
                             member("A/two/y.bin", len(body), root="A")]},
                       tmp_path, full_budget=None)
    klass = ties.build_classes(out["assets"])[0]
    assert klass["crosses_roots"] is False
    assert klass["distinct_roots"] == 1


def test_appledouble_stubs_are_labelled_not_dropped(tmp_path: Path) -> None:
    assert ties.is_appledouble("dir/._IMG_0551.JPG") is True
    assert ties.is_appledouble("dir/IMG_0551.JPG") is False
    assert ties.container_root("LYON/COMANDO/x.jpg") == "LYON"
    assert ties.container_root("./LYON/x.jpg") == "LYON"


def test_certified_same_never_skips_a_full_digest_of_every_member(tmp_path: Path) -> None:
    """The invariant the deleted stage was at risk of violating.

    No verdict may be CERTIFIED_SAME unless a real full-content digest was
    computed for EVERY member of that class -- never inferred from a partial
    read of some members and trusted for the rest. Checked across group sizes
    2 and 3, and across two distinct sample-hash groups at once, so a code
    path that only digests "the first of the group" cannot pass by accident.
    """
    bodies: dict[str, bytes] = {}

    pair_body = bytes(range(256)) * (BIG // 256)
    write(tmp_path, "A/pair1.bin", pair_body)
    write(tmp_path, "B/pair2.bin", pair_body)
    bodies["A/pair1.bin"] = pair_body
    bodies["B/pair2.bin"] = pair_body

    trio_body = b"trio" * (BIG // 4)
    for slot in ("X", "Y", "Z"):
        write(tmp_path, f"{slot}/trio.bin", trio_body)
        bodies[f"{slot}/trio.bin"] = trio_body

    groups = {
        "PAIR": [member("A/pair1.bin", len(pair_body), root="A", sample="PAIR"),
                 member("B/pair2.bin", len(pair_body), root="B", sample="PAIR")],
        "TRIO": [member(f"{slot}/trio.bin", len(trio_body), root=slot, sample="TRIO")
                 for slot in ("X", "Y", "Z")],
    }

    out = ties.resolve(groups, tmp_path, full_budget=None)

    same_members = [m for m in out["assets"] if m["verdict"] == ties.CERTIFIED_SAME]
    assert len(same_members) == 5, "test is vacuous unless both groups certify same"
    for m in same_members:
        body = bodies[m["relative_path"]]
        assert m.get("full_sha256") == hashlib.sha256(body).hexdigest(), (
            "CERTIFIED_SAME without a real full-content digest for this member")
        assert m["content_id"] == f"sha256:{m['full_sha256']}"

    # Reconstruct classes and check every member of every class was counted,
    # not just a majority.
    classes = ties.build_classes(out["assets"])
    assert len(classes) == 2
    for klass in classes:
        members_here = [m for m in same_members if m["content_id"] == klass["content_id"]]
        assert len(members_here) == klass["member_count"]


def test_result_digest_ignores_wall_time() -> None:
    """Two identical runs must produce one digest, or reproducibility is unfalsifiable."""
    a = {"files": 10, "elapsed_seconds": 1.5, "nested": {"elapsed_seconds": 9}}
    b = {"files": 10, "elapsed_seconds": 99.9, "nested": {"elapsed_seconds": 1}}
    from flujo.runrecord import result_digest
    assert (result_digest(a, ignore=("elapsed_seconds",))
            == result_digest(b, ignore=("elapsed_seconds",)))
    assert result_digest(a) != result_digest(b)
