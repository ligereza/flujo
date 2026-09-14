"""Portable, read-only diagnostics and context routing for MAK/FLUJO.

The same small engine serves the local CLI, the MAK hub and an external agent
working from a Git clone.  It never executes a user-supplied command, reads
the raw WIN archive or includes secrets in a copied report.
"""
from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "mak-diagnostic-v1"
ROUTE_SCHEMA = "mak-context-route-v1"
MAX_TEXT = 12000

_DEFAULT_DOMAINS: dict[str, dict[str, Any]] = {
    "core": {
        "branch_prefix": "maintenance",
        "keywords": [
            "repo", "git", "hub", "puerto", "dependencia", "runtime",
            "diagnostico", "error", "roto", "instalacion", "cli",
            "architecture", "branch", "deployment",
        ],
        "contract": "context/diagnostics/contracts/core.md",
        "read_paths": [
            "AGENTS.md", "pyproject.toml", "src/flujo/cli.py",
            "src/flujo/diagnostics.py", "context/LAST_HANDOFF.md",
        ],
        "checks": [
            "python3 -m flujo health",
            "python3 -m flujo diagnose --area core",
        ],
        "do_not_read": ["WIN raw archive", "large databases", "virtual environments"],
    },
    "rd": {
        "branch_prefix": "rd",
        "keywords": [
            "rd", "reducir dano", "plano", "rider", "cotizacion", "pack",
            "reactivo", "suplemento", "venue", "productora", "evento",
            "logo", "tarifa", "base de datos",
        ],
        "contract": "context/diagnostics/contracts/rd.md",
        "read_paths": [
            "src/flujo/rd", "src/flujo/plano", "web/src/components/PlanoTool.tsx",
            "web/src/components/RdDbPanel.tsx", "data/rd_packs.json",
        ],
        "checks": [
            "python3 -m pytest -q tests/test_rd_informe.py",
            "python3 -m flujo rd-db --help",
        ],
        "do_not_read": ["WIN raw archive", "RD media", "live provider credentials"],
    },
    "portfolio": {
        "branch_prefix": "portfolio",
        "keywords": [
            "portafolio", "portfolio", "iskvw", "web", "sitio", "dominio",
            "cloudflare", "dns", "deploy", "publicar", "publicacion", "frontend",
            "pagina", "certificado", "hosting",
        ],
        "contract": "context/diagnostics/contracts/portfolio.md",
        "read_paths": [
            "web", "iskvw", ".github/workflows/publicar_iskvw.yml",
            "tools/portfolio", "web/package.json",
        ],
        "checks": [
            "npm run typecheck --prefix web",
            "npm run build --prefix web",
        ],
        "do_not_read": ["WIN raw archive", "RD databases", "private media originals"],
    },
    "cultura": {
        "branch_prefix": "cultura",
        "keywords": [
            "cultura", "obra", "arte", "artistico", "artista", "ensayo", "tilde",
            "psicosis", "tapiz", "precursor", "ascii", "semilla", "planta",
            "plantas", "cultivo", "escultura", "3d", "visual",
        ],
        "contract": "context/diagnostics/contracts/cultura.md",
        "read_paths": [
            "cultura", "web/src/components/CulturaPanel.tsx",
            "docs/cultura", "context/diagnostics",
        ],
        "checks": [
            "python3 -m pytest -q tests/test_archivo_ensayos.py",
            "python3 -m compileall -q cultura",
        ],
        "do_not_read": ["WIN raw archive", "RD runtime data", "unrelated departments"],
    },
    "research": {
        "branch_prefix": "research",
        "keywords": [
            "research", "investigacion", "scraping", "scraper", "fuente", "fuentes",
            "manual", "manuales", "web", "url", "crawl", "crawl4ai", "firecrawl",
            "fondart", "postulacion", "catalogo", "triangulacion", "busqueda",
            "documentacion", "extraccion", "corpus",
        ],
        "contract": "context/diagnostics/contracts/research.md",
        "read_paths": [
            "cultura/mak_research", "tools",
            "context/diagnostics", "web/src/components/CulturaPanel.tsx",
        ],
        "checks": [
            "python3 -m pytest -q tests/test_mak_research_router.py",
            "python3 -m flujo diagnose --area research",
        ],
        "do_not_read": ["WIN raw archive", "private source exports", "provider secrets"],
    },
}

_ALIASES = {
    "mak": "core",
    "sistema": "core",
    "web": "portfolio",
    "iskvw": "portfolio",
    "obra": "cultura",
    "investigacion": "research",
    "curatoria": "research",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password|passwd|authorization)\b\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|pk|ghp|github_pat)[_-][A-Za-z0-9._-]{8,}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
)
_HOME_PATH_PATTERN = re.compile(
    r"(?<![\w@])/(?:home|root)/[^\s,;]+|"
    r"(?<![\w@])/[Uu]sers/[^\s,;]+"
)


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


def redact_text(value: Any, limit: int = MAX_TEXT) -> str:
    """Return bounded text safe to paste into an external agent."""
    text = str(value or "")
    home = str(Path.home())
    if home:
        text = text.replace(home, "~")
    # Diagnostics can be copied from another machine. Redact conventional
    # Unix user paths even when they do not match this process' home directory.
    text = _HOME_PATH_PATTERN.sub("~", text)
    for pattern in _SECRET_PATTERNS:
        replacement = "[EMAIL_REDACTED]" if "@" in pattern.pattern else "[SECRET_REDACTED]"
        text = pattern.sub(replacement, text)
    if len(text) > limit:
        text = text[:limit] + "\n...[truncated]"
    return text


def _repo_path(root: Path, relative: str) -> Path:
    return root / Path(*relative.split("/"))


def _load_domains(root: Path | None = None) -> dict[str, dict[str, Any]]:
    root = root or Path.cwd()
    path = _repo_path(root, "context/diagnostics/domains.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        domains = data.get("domains") if isinstance(data, dict) else None
        if isinstance(domains, dict) and domains:
            return domains
    except (OSError, ValueError, TypeError):
        pass
    return _DEFAULT_DOMAINS


def domain_catalog(root: Path | None = None) -> dict[str, Any]:
    """Expose routing metadata without exposing file contents."""
    domains = _load_domains(root)
    return {
        "schema": ROUTE_SCHEMA,
        "domains": {
            name: {
                "branch_prefix": cfg.get("branch_prefix", "maintenance"),
                "contract": cfg.get("contract", ""),
                "read_paths": list(cfg.get("read_paths", [])),
                "checks": list(cfg.get("checks", [])),
                "do_not_read": list(cfg.get("do_not_read", [])),
            }
            for name, cfg in domains.items()
        },
    }


def _normalize_area(area: str) -> str:
    folded = _fold(area).replace("-", "_").replace(" ", "_")
    folded = _ALIASES.get(folded, folded)
    return folded if folded in _DEFAULT_DOMAINS else ""


def _slug(value: str, fallback: str) -> str:
    folded = _fold(value)
    words = re.findall(r"[a-z0-9]+", folded)
    return "-".join(words[:4]) or fallback


def route_idea(text: str = "", area: str = "auto", root: Path | None = None) -> dict[str, Any]:
    """Select the smallest context packet for a human idea or incident."""
    root = root or Path.cwd()
    domains = _load_domains(root)
    explicit = _normalize_area(area)
    folded = _fold(text)
    scores: Counter[str] = Counter()
    matched: dict[str, list[str]] = {}
    for name, cfg in domains.items():
        hits = [str(keyword) for keyword in cfg.get("keywords", []) if _fold(keyword) in folded]
        if hits:
            matched[name] = hits
            scores[name] = len(hits)
    if explicit:
        primary = explicit
        confidence = "explicit"
    elif scores:
        primary = scores.most_common(1)[0][0]
        confidence = "medium" if scores[primary] >= 2 else "low"
    else:
        primary = "core"
        confidence = "low"
    support = [name for name, score in scores.most_common() if name != primary and score > 0]
    cfg = domains.get(primary, _DEFAULT_DOMAINS["core"])
    read_paths = list(cfg.get("read_paths", []))
    existing = [path for path in read_paths if _repo_path(root, path).exists()]
    missing = [path for path in read_paths if path not in existing]
    branch = "%s/%s" % (cfg.get("branch_prefix", "maintenance"), _slug(text, "diagnostic"))
    return {
        "schema": ROUTE_SCHEMA,
        "primary_domain": primary,
        "support_domains": support,
        "confidence": confidence,
        "matched_keywords": matched,
        "contract": cfg.get("contract", ""),
        "read_paths": read_paths,
        "existing_read_paths": existing,
        "missing_read_paths": missing,
        "do_not_read": list(cfg.get("do_not_read", [])),
        "checks": list(cfg.get("checks", [])),
        "suggested_branch": branch,
        "next_gate": (cfg.get("checks") or ["inspect the routed files"])[0],
    }


def _run_git(root: Path, *args: str) -> tuple[str, bool]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), text=True, encoding="utf-8",
            errors="replace", capture_output=True, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "", False
    return (proc.stdout or "").strip(), proc.returncode == 0


def _git_state(root: Path) -> dict[str, Any]:
    branch, branch_ok = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    commit, commit_ok = _run_git(root, "rev-parse", "--short", "HEAD")
    status, status_ok = _run_git(root, "status", "--porcelain=v1")
    rows = [line for line in status.splitlines() if line.strip()]
    available = branch_ok and commit_ok and status_ok
    return {
        "available": available,
        "branch": redact_text(branch, 120),
        "commit": redact_text(commit, 120),
        "dirty": bool(rows) if available else None,
        "changed_entries": len(rows) if available else None,
    }


def _hub_8900() -> dict[str, Any]:
    try:
        with socket.create_connection(("127.0.0.1", 8900), timeout=0.25):
            return {"available": True, "address": "127.0.0.1:8900"}
    except OSError as exc:
        return {"available": False, "address": "127.0.0.1:8900", "reason": type(exc).__name__}


def build_diagnostic_report(
    *,
    root: Path | None = None,
    area: str = "auto",
    idea: str = "",
    operation: str = "",
    error: str = "",
    command: str = "",
    expected: str = "",
    observed: str = "",
) -> dict[str, Any]:
    """Build a read-only, bounded report suitable for a web agent."""
    if root is None:
        from .paths import repo_root
        root = repo_root()
    root = Path(root).resolve()
    route = route_idea(idea or operation or error, area=area, root=root)
    contract = _repo_path(root, route["contract"]) if route.get("contract") else None
    checks = {
        "repo_exists": root.exists(),
        "pyproject": (root / "pyproject.toml").is_file(),
        "route_contract": bool(contract and contract.is_file()),
        "local_hub_8900": _hub_8900(),
    }
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "area": route["primary_domain"],
        "support_domains": route["support_domains"],
        "operation": redact_text(operation, 500),
        "idea": redact_text(idea, 3000),
        "environment": {
            "repo_name": root.name,
            "platform": platform.system(),
            "platform_release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
        },
        "git": _git_state(root),
        "reproduction": {
            "command": redact_text(command, 1200),
            "expected": redact_text(expected, 2000),
            "observed": redact_text(observed, 2000),
        },
        "error": redact_text(error),
        "route": route,
        "checks": checks,
        "safety": {
            "read_only": True,
            "raw_win_read": False,
            "secrets_included": False,
            "large_data_included": False,
            "redaction": "secrets, bearer values, email addresses and home path redacted",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable report without embedding untrusted HTML."""
    route = report.get("route") or {}
    git = report.get("git") or {}
    env = report.get("environment") or {}
    checks = report.get("checks") or {}
    repro = report.get("reproduction") or {}
    hub = checks.get("local_hub_8900") or {}
    dirty = git.get("dirty")
    dirty_label = "unknown" if dirty is None else str(dirty)
    changed_entries = git.get("changed_entries")
    changed_label = "unknown" if changed_entries is None else str(changed_entries)
    lines = [
        "# MAK diagnostic report",
        "",
        f"- schema: `{report.get('schema', SCHEMA)}`",
        f"- generated_at_utc: `{report.get('generated_at_utc', '')}`",
        f"- area: `{report.get('area', 'core')}`",
        f"- support_domains: `{', '.join(report.get('support_domains') or []) or 'none'}`",
        f"- operation: `{report.get('operation') or 'not provided'}`",
        f"- repository: `{env.get('repo_name', '')}`",
        f"- platform: `{env.get('platform', '')} {env.get('platform_release', '')}`",
        f"- python: `{env.get('python', '')}`",
        f"- git: `{git.get('branch') or 'unknown'}@{git.get('commit') or 'unknown'}`",
        f"- working_tree_dirty: `{dirty_label}` ({changed_label} entries)",
        "",
        "## Idea",
        "",
        report.get("idea") or "(not provided)",
        "",
        "## Error",
        "",
        "```text",
        report.get("error") or "(not provided)",
        "```",
        "",
        "## Reproduction",
        "",
        f"- command: `{repro.get('command') or 'not provided'}`",
        f"- expected: {repro.get('expected') or '(not provided)'}",
        f"- observed: {repro.get('observed') or '(not provided)'}",
        "",
        "## Routed context",
        "",
        f"- contract: `{route.get('contract') or 'none'}`",
        f"- suggested_branch: `{route.get('suggested_branch') or 'maintenance/diagnostic'}`",
        f"- confidence: `{route.get('confidence') or 'low'}`",
        f"- next_gate: `{route.get('next_gate') or 'inspect the routed files'}`",
        "- read first:",
    ]
    lines.extend(f"  - `{path}`" for path in route.get("existing_read_paths", []))
    if route.get("missing_read_paths"):
        lines.append("- missing or external paths:")
        lines.extend(f"  - `{path}`" for path in route["missing_read_paths"])
    lines.append("- do not read automatically:")
    lines.extend(f"  - {item}" for item in route.get("do_not_read", []))
    lines.extend([
        "",
        "## Checks observed",
        "",
        f"- repo_exists: `{checks.get('repo_exists')}`",
        f"- pyproject: `{checks.get('pyproject')}`",
        f"- route_contract: `{checks.get('route_contract')}`",
        f"- local_hub_8900: `{hub.get('available')}`",
        "",
        "## Safety boundary",
        "",
        "This report is read-only and sanitized. It excludes raw WIN, secrets, full databases and large media.",
    ])
    return "\n".join(lines) + "\n"


def render_route_markdown(route: dict[str, Any]) -> str:
    """Render the small context packet used by an external agent."""
    lines = [
        "# MAK context route",
        "",
        f"- schema: `{route.get('schema', ROUTE_SCHEMA)}`",
        f"- primary_domain: `{route.get('primary_domain', 'core')}`",
        f"- support_domains: `{', '.join(route.get('support_domains') or []) or 'none'}`",
        f"- confidence: `{route.get('confidence', 'low')}`",
        f"- suggested_branch: `{route.get('suggested_branch', 'maintenance/diagnostic')}`",
        f"- next_gate: `{route.get('next_gate', '')}`",
        "",
        f"contract: `{route.get('contract', '')}`",
        "",
        "## Read first",
        "",
    ]
    lines.extend(f"- `{path}`" for path in route.get("existing_read_paths", []))
    if route.get("missing_read_paths"):
        lines.extend(["", "## Missing or external", ""])
        lines.extend(f"- `{path}`" for path in route["missing_read_paths"])
    lines.extend(["", "## Do not read automatically", ""])
    lines.extend(f"- {item}" for item in route.get("do_not_read", []))
    lines.extend(["", "## Validation candidates", ""])
    lines.extend(f"- `{cmd}`" for cmd in route.get("checks", []))
    return "\n".join(lines) + "\n"
