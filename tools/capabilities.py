#!/usr/bin/env python3
"""Probe MAK and FLUJO capability surfaces against their declarations.

The registry in this file is deliberately small and explicit: a path or a
process name is not treated as a capability by itself.  The command compares
the registry with the capability documents, then (optionally) probes the
current user services and local listeners.  It emits evidence; it never edits
the capability documents automatically.

Examples::

    python3 tools/capabilities.py
    python3 tools/capabilities.py --format json --output state/capabilities-runtime.json
    python3 tools/capabilities.py --check --no-live
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from .branch_contract import disposition as _disposition
    from .branch_contract import interpret_ref
except ImportError:  # direct ``python tools/capabilities.py`` execution
    import importlib.util

    _contract_spec = importlib.util.spec_from_file_location(
        "mak_branch_contract", Path(__file__).with_name("branch_contract.py")
    )
    if _contract_spec is None or _contract_spec.loader is None:
        raise ImportError("branch_contract_unavailable")
    _contract_module = importlib.util.module_from_spec(_contract_spec)
    _contract_spec.loader.exec_module(_contract_module)
    _disposition = _contract_module.disposition
    interpret_ref = _contract_module.interpret_ref


@dataclass(frozen=True)
class Surface:
    """One declared runtime/capability surface."""

    surface_id: str
    label: str
    owner: str
    source: str
    doc_anchors: tuple[str, ...]
    unit: str | None = None
    ports: tuple[int, ...] = ()
    http_paths: tuple[str, ...] = ()
    expectation: str = "manual"
    unit_scope: str = "user"
    models: tuple[str, ...] = ()
    consumer_sources: tuple[str, ...] = ()


# Keep this list explicit.  It is the semantic bridge between the physical
# services and the human capability registry; discovery alone cannot tell a
# compatibility wrapper from an owned Hub.
SURFACES: tuple[Surface, ...] = (
    Surface(
        "mak_hub",
        "MAK Hub",
        "mak",
        "cultura/mak_plataforma/hub.py",
        ("MAK Hub", "cultura/mak_plataforma/hub.py"),
        unit=".config/systemd/user/mak-hub.service",
        ports=(8900,),
        http_paths=("/health", "/api/status"),
        expectation="service_active",
    ),
    Surface(
        "flujo_app",
        "FLUJO App",
        "flujo",
        "src/flujo/web/hub.py",
        ("FLUJO App", "src/flujo/web/hub.py"),
        ports=(8765, 8766),
        http_paths=("/",),
        expectation="manual",
    ),
    Surface(
        "flujo_serve",
        "FLUJO serve",
        "flujo",
        "src/flujo/serve/server.py",
        ("FLUJO `serve`", "src/flujo/serve/server.py"),
        ports=(8777,),
        http_paths=("/",),
        expectation="manual",
    ),
    Surface(
        "mak_research",
        "Research",
        "mak",
        "cultura/mak_research/interfaz.py",
        ("Research", "cultura/mak_research/interfaz.py"),
        unit=".config/systemd/user/mak-research.service",
        ports=(8890,),
        http_paths=("/",),
        expectation="service_active",
    ),
    Surface(
        "mak_codex",
        "Codex bridge",
        "mak",
        "cultura/mak_codex/interfaz_codex.py",
        ("Codex bridge", "cultura/mak_codex/interfaz_codex.py"),
        unit=".config/systemd/user/mak-codex.service",
        ports=(8891,),
        http_paths=("/",),
        expectation="service_active",
    ),
    Surface(
        "ollama",
        "Ollama local inference",
        "mak",
        "cultura/mak_research/research_lib.py",
        ("ollama LOCAL en MAK", "ollama.service"),
        unit="/etc/systemd/system/ollama.service",
        unit_scope="system",
        ports=(11434,),
        http_paths=("/api/version", "/api/tags"),
        expectation="service_active",
        models=("gemma3:4b", "deepseek-coder:6.7b", "nomic-embed-text:latest"),
        consumer_sources=(
            "cultura/mak_research/research_lib.py",
            "cultura/mak_codex/codex_lib.py",
            "cultura/mak_plataforma/discernment.py",
            "cultura/mak_plataforma/mineria_rd.py",
            "cultura/mak_plataforma/tandas.py",
            "cultura/mak_plataforma/chat_agente.py",
        ),
    ),
    Surface(
        "mak_copilot",
        "Copilot curatorial",
        "mak",
        "cultura/mak_plataforma/copilot.py",
        ("Copilot curatorial", "cultura/mak_plataforma/copilot.py"),
        expectation="embedded",
    ),
    Surface(
        "searxng",
        "SearXNG",
        "mak",
        "searxng/settings.yml",
        ("SearXNG", "searxng/settings.yml"),
        ports=(8888,),
        http_paths=("/",),
        expectation="observe",
    ),
    Surface(
        "mak_research_queue",
        "ntfy queue",
        "mak",
        ".config/systemd/user/mak-research-queue.service",
        ("Cola ntfy", ".config/systemd/user/mak-research-queue.service"),
        unit=".config/systemd/user/mak-research-queue.service",
        expectation="optional_inactive",
    ),
)


def _run_systemctl(unit: str, scope: str = "user") -> str:
    """Return a bounded unit state without treating missing systemd as a bug."""

    try:
        command = ["systemctl"]
        if scope == "user":
            command.append("--user")
        command.extend(("is-active", unit))
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unavailable"
    state = result.stdout.strip()
    if state in {"active", "inactive", "failed", "activating", "deactivating"}:
        return state
    if result.returncode == 5 or "not found" in result.stderr.lower():
        return "missing"
    return state or "unavailable"


def _probe_http(port: int, paths: Iterable[str]) -> dict[str, object]:
    """Probe one local TCP port and the first responding HTTP path."""

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            socket_open = True
    except OSError:
        return {"port": port, "socket_open": False, "http_status": None, "http_path": None}

    for path in paths:
        try:
            request = Request(f"http://127.0.0.1:{port}{path}", method="GET")
            with urlopen(request, timeout=2) as response:
                return {
                    "port": port,
                    "socket_open": socket_open,
                    "http_status": int(response.status),
                    "http_path": path,
                }
        except (OSError, URLError, ValueError):
            continue
    return {"port": port, "socket_open": socket_open, "http_status": None, "http_path": None}


def _declared(docs: list[Path], anchors: tuple[str, ...]) -> list[str]:
    """Find current rows where the label and canonical source co-occur.

    Capability documents retain historical material below their current audit
    card. Searching the whole file made an old cross-check look like current
    ownership, so prefer the bounded ``Auditoría vigente`` section and only
    fall back to the whole document for older document shapes.
    """

    hits: list[str] = []
    lowered = tuple(anchor.lower() for anchor in anchors)
    for doc in docs:
        try:
            lines = doc.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        current = lines
        for index, line in enumerate(lines):
            if line.strip().lower().startswith("## auditoría vigente"):
                current = []
                for candidate in lines[index:]:
                    if candidate.startswith("## ") and candidate != line:
                        break
                    current.append(candidate)
                break
        if any(all(anchor in line.lower() for anchor in lowered) for line in current):
            hits.append(str(doc))
    return hits


def _surface_result(root: Path, docs: list[Path], surface: Surface, live: bool) -> dict[str, object]:
    source_path = root / surface.source
    unit_path = None
    if surface.unit:
        unit_path = Path(surface.unit)
        if not unit_path.is_absolute():
            unit_path = root / unit_path
    consumer_present = [
        path for path in surface.consumer_sources if (root / path).is_file()
    ]
    consumer_missing = [
        path for path in surface.consumer_sources if not (root / path).is_file()
    ]
    result: dict[str, object] = {
        "id": surface.surface_id,
        "label": surface.label,
        "owner": surface.owner,
        "source": surface.source,
        "source_exists": source_path.is_file(),
        "unit": surface.unit,
        "unit_scope": surface.unit_scope,
        "unit_exists": unit_path.is_file() if unit_path else None,
        # systemctl receives the unit name, while the registry keeps the
        # repository-relative unit path for provenance and source checks.
        "unit_state": (
            _run_systemctl(Path(surface.unit).name, scope=surface.unit_scope)
            if live and surface.unit
            else "not_applicable"
        ),
        "declared_in": _declared(docs, surface.doc_anchors),
        "ports": [],
        "expectation": surface.expectation,
        "models_expected": list(surface.models),
        "models_present": [],
        "consumer_sources": list(surface.consumer_sources),
        "consumer_sources_present": consumer_present,
        "consumer_sources_missing": consumer_missing,
        "issues": [],
    }
    if live and surface.ports:
        result["ports"] = [_probe_http(port, surface.http_paths) for port in surface.ports]

    issues: list[str] = result["issues"]  # type: ignore[assignment]
    if not result["source_exists"]:
        issues.append("source_missing")
    if not result["declared_in"]:
        issues.append("capability_row_missing")
    if consumer_missing:
        issues.append("consumer_source_missing:" + ",".join(consumer_missing))

    if live and surface.models and surface.ports:
        try:
            request = Request(f"http://127.0.0.1:{surface.ports[0]}/api/tags", method="GET")
            with urlopen(request, timeout=2) as response:
                payload = json.load(response)
            model_rows = payload.get("models", []) if isinstance(payload, dict) else []
            names = {
                str(row.get("name"))
                for row in model_rows
                if isinstance(row, dict) and row.get("name")
            }
            present = [name for name in surface.models if name in names]
            result["models_present"] = present
            missing = [name for name in surface.models if name not in names]
            if missing:
                issues.append("models_missing:" + ",".join(missing))
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            issues.append("models_probe_failed")

    state = str(result["unit_state"])
    if surface.expectation == "service_active" and live:
        if state != "active":
            issues.append(f"unit_not_active:{state}")
        ports = result["ports"]
        if ports and not any(bool(item["socket_open"]) for item in ports):
            issues.append("listener_missing")
    return result


def _git_value(root: Path, *args: str) -> str | None:
    """Read one bounded Git fact without treating Git as physical authority."""

    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _branch_result(root: Path) -> dict[str, object]:
    """Check the branch contract when a checkout exposes one."""

    branch = _git_value(root, "branch", "--show-current")
    profile_path = root / "branch_profile.json"
    result: dict[str, object] = {
        "branch": branch,
        "profile_path": str(profile_path),
        "profile_exists": profile_path.is_file(),
        "profile_branch": None,
        "current_ref": branch,
        "canonical_ref": None,
        "lane": None,
        "kind": None,
        "comparison_ref": None,
        "integration_target": None,
        "profile_scope": None,
        "profile_kind": None,
        "capabilities": None,
        "requirements": None,
        "hub_source": None,
        "selector": None,
        "pyproject_addopts": None,
        "issues": [],
    }
    issues: list[str] = result["issues"]  # type: ignore[assignment]
    if not branch:
        issues.append("branch_unknown")
    if not profile_path.is_file():
        issues.append("branch_profile_missing")
        return result
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        issues.append("branch_profile_unreadable")
        return result

    semantics = interpret_ref(branch, profile)
    profile_branch = profile.get("branch")
    profile_kind = semantics["kind"]
    result["profile_branch"] = profile_branch
    result.update({key: semantics.get(key) for key in (
        "current_ref", "canonical_ref", "lane", "kind", "comparison_ref",
        "integration_target", "profile_scope"
    )})
    result["profile_kind"] = profile_kind
    result["selector"] = profile.get("default_test_selector")
    capabilities = profile.get("capabilities")
    requirements = profile.get("requirements")
    hub = profile.get("hub") or {}
    hub_source = hub.get("module") if isinstance(hub, dict) else None
    result["capabilities"] = capabilities
    result["requirements"] = requirements
    result["hub_source"] = hub_source

    issues.extend(str(issue) for issue in semantics["issues"])
    if not isinstance(capabilities, str) or not (root / capabilities).is_file():
        issues.append("profile_capabilities_missing")
    if not isinstance(requirements, str) or not (root / requirements).is_file():
        issues.append("profile_requirements_missing")
    if profile_kind == "historical":
        if hub_source is not None:
            issues.append("historical_hub_declared")
    elif not isinstance(hub_source, str) or not (root / hub_source).is_file():
        issues.append("profile_hub_source_missing")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            parsed = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            marker = (
                parsed.get("tool", {})
                .get("pytest", {})
                .get("ini_options", {})
                .get("addopts")
            )
        except (OSError, tomllib.TOMLDecodeError):
            marker = None
        result["pyproject_addopts"] = marker
        selector = profile.get("default_test_selector")
        if profile_kind == "historical" and selector:
            issues.append("historical_selector_declared")
        elif isinstance(selector, str) and selector and selector not in (marker or ""):
            issues.append("profile_selector_not_in_pytest_addopts")
    return result


def _ref_inventory(root: Path) -> dict[str, object]:
    """Inventory heads, remote-tracking refs and tags using shared semantics."""
    try:
        raw = subprocess.run(
            [
                "git", "-C", str(root), "for-each-ref",
                "--format=%(refname)\t%(objectname)\t%(objecttype)",
                "refs/heads", "refs/remotes", "refs/tags",
            ], capture_output=True, text=True, timeout=8, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"schema": "mak-branch-ref-inventory-v2", "available": False, "refs": []}

    refs: list[dict[str, object]] = []
    by_identity: dict[tuple[str, str], list[str]] = {}

    def run_git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return result.stdout.strip()

    for line in raw.splitlines():
        full_ref, sha, object_type = line.split("\t", 2)
        if full_ref.endswith("/HEAD"):
            continue
        remote_name = None
        if full_ref.startswith("refs/remotes/"):
            remote_path = full_ref.removeprefix("refs/remotes/")
            remote_name, name = remote_path.split("/", 1)
            ref_kind = "remote_tracking"
        elif full_ref.startswith("refs/tags/"):
            name = full_ref.removeprefix("refs/tags/")
            ref_kind = "annotated_tag" if object_type == "tag" else "tag"
        else:
            name = full_ref.removeprefix("refs/heads/")
            ref_kind = "head"
        peeled_commit_sha = None
        if ref_kind == "annotated_tag":
            peeled = run_git("rev-parse", f"{full_ref}^{{}}")
            if peeled and run_git("cat-file", "-t", peeled) == "commit":
                peeled_commit_sha = peeled
        try:
            profile = json.loads(run_git("show", f"{full_ref}:branch_profile.json"))
        except (json.JSONDecodeError, OSError, ValueError):
            profile = {}
        semantics = interpret_ref(name, profile)
        comparison_ref = semantics.get("comparison_ref")
        target_ref = None
        sync: dict[str, int | None] = {"ahead": None, "behind": None}
        ancestry: dict[str, int | None] = {
            "exclusive_commit_count": None,
            "patch_unique_count": None,
            "patch_equivalent_count": None,
        }
        if isinstance(comparison_ref, str) and comparison_ref:
            for candidate in (
                comparison_ref,
                f"vibecodeine-legacy/{comparison_ref}",
                f"origin/{comparison_ref}",
            ):
                if run_git("rev-parse", "--verify", candidate):
                    target_ref = candidate
                    break
            if target_ref:
                counts = run_git("rev-list", "--left-right", "--count", f"{target_ref}...{full_ref}").split()
                if len(counts) == 2:
                    sync = {"behind": int(counts[0]), "ahead": int(counts[1])}
                exclusive = run_git("rev-list", f"{target_ref}..{full_ref}").splitlines()
                cherry = run_git("cherry", target_ref, full_ref).splitlines()
                ancestry = {
                    "exclusive_commit_count": len(exclusive),
                    "patch_unique_count": sum(line.startswith("+") for line in cherry),
                    "patch_equivalent_count": sum(line.startswith("-") for line in cherry),
                }
        row = {
            "ref": full_ref,
            "name": name,
            "sha": sha,
            "object_sha": sha,
            "object_type": object_type,
            "ref_kind": ref_kind,
            "remote_name": remote_name,
            "peeled_commit_sha": peeled_commit_sha,
            "profile_present": bool(profile),
            **semantics,
            "disposition": _disposition(name, semantics),
            "comparison_ref": comparison_ref,
            "comparison_git_ref": target_ref,
            "sync": sync,
            "ancestry": ancestry,
        }
        refs.append(row)
        # An annotated tag is a named historical object, not an alias merely
        # because it peels to the same commit as a branch.
        identity = ("head_remote_commit", sha) if ref_kind in {"head", "remote_tracking"} else ("tag", full_ref)
        by_identity.setdefault(identity, []).append(name)

    for row in refs:
        ref_kind = str(row["ref_kind"])
        identity = (
            ("head_remote_commit", str(row["object_sha"]))
            if ref_kind in {"head", "remote_tracking"}
            else ("tag", str(row["ref"]))
        )
        row["aliases"] = sorted(set(by_identity.get(identity, [])))
    alias_groups = [
        {"identity": identity[0], "sha": identity[1], "refs": sorted(set(names))}
        for identity, names in by_identity.items()
        if len(set(names)) > 1
    ]
    counts = {
        kind: sum(1 for row in refs if row["ref_kind"] == kind)
        for kind in ("head", "remote_tracking", "tag", "annotated_tag")
    }
    return {
        "schema": "mak-branch-ref-inventory-v2",
        "available": True,
        "ref_count": len(refs),
        "unique_sha_count": len({str(row["object_sha"]) for row in refs}),
        "ref_counts": counts,
        "alias_group_count": len(alias_groups),
        "alias_groups": sorted(alias_groups, key=lambda row: (row["identity"], row["sha"])),
        "refs": sorted(refs, key=lambda row: str(row["ref"])),
    }


def _markdown(report: dict[str, object]) -> str:
    rows = [
        "# Capability runtime check",
        "",
        f"- schema: `{report['schema']}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- root: `{report['root']}`",
        "",
        "| Surface | Owner | Source | Declared | Unit | Listener | Issues |",
        "|---|---|---|---:|---|---|---|",
    ]
    for item in report["surfaces"]:  # type: ignore[union-attr]
        declared = ", ".join(Path(p).name for p in item["declared_in"]) or "NO"
        unit = item["unit_state"]
        listeners = [p for p in item["ports"] if p["socket_open"]]
        listener = ", ".join(str(p["port"]) for p in listeners) or "none"
        issues = ", ".join(item["issues"]) or "—"
        rows.append(
            f"| {item['label']} | {item['owner']} | `{item['source']}` | "
            f"{declared} | {unit} | {listener} | {issues} |"
        )
    rows.extend(
        [
            "",
            f"- branch: `{report['branch']['branch']}`; profile: `{report['branch']['profile_branch']}`; "
            f"branch_issues: {', '.join(report['branch']['issues']) or '—'}",
            "",
            "This report is evidence only; it does not rewrite capability documents.",
        ]
    )
    return "\n".join(rows) + "\n"


def _write_atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def build_report(root: Path, docs: list[Path], live: bool) -> dict[str, object]:
    # This checker also ships in the MAK checkout as a shared implementation.
    # When run from the FLUJO checkout, report only FLUJO-owned surfaces: MAK
    # sources deliberately do not exist in that checkout.
    branch = _git_value(root, "branch", "--show-current")
    surfaces = tuple(
        surface for surface in SURFACES
        if branch != "FLUJO" or surface.owner == "flujo"
    )
    results = [_surface_result(root, docs, surface, live) for surface in surfaces]
    return {
        "schema": "mak-capabilities-runtime-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "documents": [str(doc) for doc in docs],
        "live_probe": live,
        "summary": {
            "surfaces": len(results),
            "declared": sum(bool(item["declared_in"]) for item in results),
            "sources_present": sum(bool(item["source_exists"]) for item in results),
            "with_issues": sum(bool(item["issues"]) for item in results),
        },
        "branch": _branch_result(root),
        "ref_inventory": _ref_inventory(root),
        "surfaces": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--docs",
        type=Path,
        action="append",
        help="capability document(s), relative to --root; defaults to the FLUJO matrix",
    )
    parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
    parser.add_argument("--output", type=Path, help="write the selected report atomically")
    parser.add_argument("--no-live", action="store_true", help="skip systemd, socket and HTTP probes")
    parser.add_argument(
        "--check-branch",
        action="store_true",
        help="also require branch_profile.json to match the checkout and pytest selector",
    )
    parser.add_argument("--check", action="store_true", help="exit 1 if a source/row/service is missing")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    doc_paths = args.docs or [
        Path("CAPACIDADES_FLUJO.md"),
    ]
    docs = [(path if path.is_absolute() else root / path) for path in doc_paths]
    docs = [path for path in docs if path.is_file()]
    report = build_report(root, docs, live=not args.no_live)

    if args.format == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    elif args.format == "markdown":
        rendered = _markdown(report)
    else:
        rendered = (
            f"{report['schema']} | {report['summary']['declared']}/"
            f"{report['summary']['surfaces']} declared | "
            f"{report['summary']['sources_present']}/{report['summary']['surfaces']} sources | "
            f"issues={report['summary']['with_issues']}\n"
        )
        rendered += (
            f"- branch: {report['branch']['branch'] or 'UNKNOWN'}; "
            f"profile={report['branch']['profile_branch'] or 'UNKNOWN'}; "
            f"branch_issues={','.join(report['branch']['issues']) or 'ok'}\n"
        )
        for item in report["surfaces"]:  # type: ignore[union-attr]
            listeners = [p["port"] for p in item["ports"] if p["socket_open"]]
            problems = ",".join(item["issues"]) or "ok"
            rendered += (
                f"- {item['label']}: source={'yes' if item['source_exists'] else 'NO'}; "
                f"declared={'yes' if item['declared_in'] else 'NO'}; "
                f"unit={item['unit_state']}; listeners={listeners or '-'}; {problems}\n"
            )
            if item["models_expected"]:
                rendered += (
                    f"  models={item['models_present']}/{item['models_expected']}; "
                    f"consumers={len(item['consumer_sources_present'])}/"
                    f"{len(item['consumer_sources'])}\n"
                )

    if args.output:
        output = args.output if args.output.is_absolute() else root / args.output
        _write_atomic(output, rendered)
    else:
        sys.stdout.write(rendered)

    if args.check:
        issues = int(report["summary"]["with_issues"])
        if args.check_branch:
            issues += len(report["branch"]["issues"])
        return 1 if issues else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
