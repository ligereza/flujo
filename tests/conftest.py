"""Make the suite test THIS checkout's src/flujo, not an editable install.

From a git worktree, `import flujo` would otherwise resolve to the main
checkout's installed package and the suite would silently test stale code.
Prepending this repo's src/ pins every test to the code next to it.

The labels below are a collection index, not a semantic claim about a test's
complete coverage. They let a person run a bounded slice such as
``pytest -m 'area_research and role_data'`` without moving the historical test
files into a new directory tree. Size, scope, and environment labels are
conservative: ``unknown`` is preferable to pretending that a filename proves
how a test behaves.
"""
from __future__ import annotations

import ast
from collections import Counter
from functools import lru_cache
import re
import sys
from pathlib import Path

import pytest
from tools.test_lane_map import LANES as TEST_LANES
from tools.test_lane_map import lane_for_test_path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# Filename tokens are deliberately broad and overlap is allowed. A bridge can
# be both ``area_portfolio`` and ``area_hub``; a degradation test can be both
# ``role_regression`` and ``role_integration``. ``misc`` is explicit when no
# area rule matches, so an unclassified file is never silently invisible.
_AREA_RULES: dict[str, tuple[str, ...]] = {
    "hub": ("hub", "serve", "dashboard", "system_status"),
    "research": (
        "research", "knowledge", "fuentes", "source", "busqueda", "consulta",
        "debate", "memoria", "vigia", "opportunity", "certified",
    ),
    "archive": (
        "archive", "archiv", "ingesta", "substrate", "reconstruction", "identity",
        "project", "corpus", "classification", "material", "catalog",
    ),
    "portfolio": (
        "portfolio", "product", "application", "artistic", "practice", "possibility",
        "director", "copilot", "episode", "title",
    ),
    "curatoria": (
        "curatoria", "curaduria", "iskvw", "micelio", "vinculo", "entregar",
        "gen_archivo", "animadas", "piel",
    ),
    "rd": (
        "rd_", "_rd", "reactivo", "becas", "cotizacion", "mineria", "testeo", "datos",
    ),
    "render": (
        "render", "blender", "resolume", "video", "flyer", "svg", "adobe", "illustrator",
        "laser", "png", "scene", "plano", "autofit", "formato", "formats", "venue",
    ),
    "runtime": (
        "codex", "xio", "conductor", "tanda", "jobs", "backlog", "autonomia", "reanudar",
        "trabajo", "cron", "heartbeat", "pausa", "wifi", "operational", "process",
    ),
    "governance": (
        "higiene", "repo", "agent", "revisor", "manifest", "privacy", "idioma", "contract",
        "feature", "learning", "admissibility", "epistemic", "review", "policy",
        "mantenimiento", "borradura", "check",
    ),
}

_ROLE_RULES: dict[str, tuple[str, ...]] = {
    "contract": (
        "contract", "schema", "manifest", "catalog", "format", "identity", "admissibility",
        "policy", "registry",
    ),
    "regression": (
        "defect", "hotfix", "fallback", "missing", "absence", "higiene", "privacy", "failure",
        "error", "degradation", "broken", "fix",
    ),
    "integration": (
        "bridge", "hub", "http", "route", "execution", "smoke", "pipeline", "concurrency",
        "integration", "endpoint", "surface", "server",
    ),
    "data": (
        "archive", "database", "_db", "ingesta", "source", "corpus", "memory", "knowledge",
        "material", "index", "ledger",
    ),
    "render": (
        "render", "blender", "resolume", "video", "flyer", "svg", "adobe", "illustrator",
        "laser", "png", "scene", "plano", "autofit",
    ),
    "operations": (
        "jobs", "backlog", "autonomia", "reanudar", "trabajo", "cron", "heartbeat", "pausa",
        "tanda", "vigia", "wifi", "concurrency",
    ),
}

# These tokens are intentionally high-confidence only. They are a first
# routing layer for the suite, not a replacement for reading a test's body.
_SIZE_RULES: dict[str, tuple[str, ...]] = {
    "small": (
        "pure", "unit", "parser", "schema", "contract", "policy", "higiene",
        "privacy", "math", "scoring", "coherence", "resolver", "validator",
    ),
    "medium": (
        "integration", "http", "hub", "web", "database", "_db", "cross_archive",
        "toolchain", "archive_pipeline", "smoke",
    ),
    "large": (
        "production", "physical", "ssd", "resolume", "xio", "blender", "video",
        "screen_setup", "e2e", "real_fixture", "onedrive",
    ),
}

_SCOPE_RULES: dict[str, tuple[str, ...]] = {
    "unit": (
        "pure", "unit", "parser", "schema", "contract", "policy", "higiene",
        "privacy", "math", "scoring", "coherence", "validator",
    ),
    "integration": (
        "integration", "bridge", "http", "hub", "web", "database", "_db",
        "cross_archive", "pipeline", "route", "endpoint", "surface",
    ),
    "system": (
        "production", "physical", "ssd", "resolume", "xio", "blender", "video",
        "screen_setup", "e2e", "real_fixture", "onedrive", "issue",
    ),
}

_ENVIRONMENT_RULES: dict[str, tuple[str, ...]] = {
    "physical": (
        "physical", "ssd", "resolume", "xio", "real_fixture", "portfolio_production",
        "screen_setup", "mak_organism",
    ),
    "external": (
        "http", "https", "github", "onedrive", "network", "download", "ig_",
        "firecrawl", "mcp", "spotify", "mail", "issue",
    ),
    "machine_bound": (
        "/home/mak", "actions_runner", "subprocess", "venv", "experiments_pilots",
        "portable",
    ),
    "optional": (
        "psd_tools", "imagehash", "ffmpeg", "vpype", "torch", "faiss", "mobileclip",
    ),
}

_MACHINE_TEXT_SIGNALS = ("/home/mak", "/media/", "/mnt/", "actions-runner")
_PHYSICAL_TEXT_SIGNALS = ("/media/", "portable_ssd", "resolume", "xio")
_EXTERNAL_IMPORT_SIGNALS = (
    "requests", "httpx", "urllib", "aiohttp", "selenium", "boto3", "googleapiclient",
)
_EXTERNAL_CALL_SIGNALS = (
    "urlopen", "requests", "httpx", "rclone", "selenium", "webdriver",
)
_OPTIONAL_TEXT_SIGNALS = (
    "psd_tools", "imagehash", "ffmpeg", "vpype", "torch", "faiss", "mobileclip",
)


@lru_cache(maxsize=None)
def _source_signals(path: str) -> frozenset[str]:
    """Extract high-confidence environment signals from one test module."""
    candidate = Path(path)
    try:
        tree = ast.parse(candidate.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return frozenset()

    strings = [node.value.lower() for node in ast.walk(tree)
               if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    imports = [node.module.lower() for node in ast.walk(tree)
               if isinstance(node, ast.ImportFrom) and node.module]
    imports.extend(alias.name.lower() for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names)
    names = [node.id.lower() for node in ast.walk(tree) if isinstance(node, ast.Name)]
    attributes = [node.attr.lower() for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
    joined = "\n".join((*strings, *imports, *names, *attributes))
    signals: set[str] = set()
    if any(signal in joined for signal in _MACHINE_TEXT_SIGNALS):
        signals.add("machine_bound")
    if any(signal in joined for signal in _PHYSICAL_TEXT_SIGNALS):
        signals.add("physical")
    if any(signal in imports for signal in _EXTERNAL_IMPORT_SIGNALS):
        signals.add("external")
    if any(signal in joined for signal in _EXTERNAL_CALL_SIGNALS):
        signals.add("external")
    if any(signal in joined for signal in _OPTIONAL_TEXT_SIGNALS):
        signals.add("optional")
    return frozenset(signals)


def _labels(stem: str, rules: dict[str, tuple[str, ...]], fallback: str) -> tuple[str, ...]:
    lowered = stem.lower()
    labels = tuple(name for name, tokens in rules.items()
                   if any(token in lowered for token in tokens))
    return labels or (fallback,)


def _axis_label(stem: str, rules: dict[str, tuple[str, ...]], fallback: str) -> str:
    """Return one conservative label for a size/scope/environment axis."""
    lowered = stem.lower()
    for name, tokens in rules.items():
        if any(token in lowered for token in tokens):
            return name
    return fallback


def classify_test_path(path: str | Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return stable (areas, roles) labels for one test file path."""
    stem = Path(path).stem
    return _labels(stem, _AREA_RULES, "misc"), _labels(stem, _ROLE_RULES, "general")


def topic_for_test_path(path: str | Path) -> str:
    """Return the exact first subject token used for a topic marker.

    This preserves the existing filename taxonomy (`test_mak_research_...`
    becomes `research`) while the broader area labels above provide useful
    cross-cutting selections. The fallback is explicit rather than silent.
    """
    stem = Path(path).stem.lower()
    tokens = [token for token in stem.split("_")[1:]
              if token not in {"mak", "test"}]
    topic = tokens[0] if tokens else "misc"
    return re.sub(r"[^a-z0-9]+", "_", topic).strip("_") or "misc"


def classify_test_axes(path: str | Path) -> tuple[str, str, str]:
    """Return conservative ``(size, scope, environment)`` labels.

    The fallback values are explicit because filename inference cannot prove
    that a test is hermetic or small. Future fixes should prefer adding an
    explicit override or a focused marker over widening these token lists.
    """
    candidate = Path(path)
    stem = candidate.stem
    signals = _source_signals(str(candidate)) if candidate.is_file() else frozenset()
    environment = _axis_label(stem, _ENVIRONMENT_RULES, "unknown")
    if "physical" in signals:
        environment = "physical"
    elif "external" in signals:
        environment = "external"
    elif "machine_bound" in signals:
        environment = "machine_bound"
    elif "optional" in signals:
        environment = "optional"
    return (
        _axis_label(stem, _SIZE_RULES, "unknown"),
        _axis_label(stem, _SCOPE_RULES, "unknown"),
        environment,
    )


def pytest_configure(config: pytest.Config) -> None:
    for area in (*_AREA_RULES, "misc"):
        config.addinivalue_line("markers", f"area_{area}: broad MAK test area")
    for role in (*_ROLE_RULES, "general"):
        config.addinivalue_line("markers", f"role_{role}: test behavior or verification role")
    for axis, values in {
        "size": (*_SIZE_RULES, "unknown"),
        "scope": (*_SCOPE_RULES, "unknown"),
        "environment": (*_ENVIRONMENT_RULES, "unknown"),
    }.items():
        for value in values:
            config.addinivalue_line(
                "markers", f"{axis}_{value}: conservative test routing label"
            )
    for lane in ("fast", "contract", "machine", "optional", "review"):
        config.addinivalue_line("markers", f"lane_{lane}: execution lane recommendation")
    for lane in TEST_LANES:
        config.addinivalue_line("markers", f"{lane}: deterministic test execution lane")
    # Register exact filename topics so `pytest -m topic_research` is warning-free.
    for path in sorted((_REPO / "tests").glob("test_*.py")):
        config.addinivalue_line(
            "markers", f"topic_{topic_for_test_path(path)}: exact test filename topic"
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--area-report",
        action="store_true",
        help="print collected test counts by automatic area and role labels",
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Always collect tests before applying a marker expression.

    The repository is standalone now, so a stale generated lane map must not
    hide a newly migrated test before pytest can evaluate it. Marker filtering
    remains a normal post-collection operation.
    """
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        areas, roles = classify_test_path(Path(str(item.fspath)))
        size, scope, environment = classify_test_axes(Path(str(item.fspath)))
        for area in areas:
            item.add_marker(f"area_{area}")
        for role in roles:
            item.add_marker(f"role_{role}")
        item.add_marker(f"size_{size}")
        item.add_marker(f"scope_{scope}")
        item.add_marker(f"environment_{environment}")
        item.add_marker(f"topic_{topic_for_test_path(Path(str(item.fspath)))}")
        # The exclusive execution lane comes from the persisted AST import map.
        # An absent or stale entry returns ``review`` and cannot fail collection.
        item.add_marker(lane_for_test_path(Path(str(item.fspath))))

        # Lanes overlap by design. ``lane_fast`` is only for high-confidence
        # small candidates; unknown tests remain visible in ``lane_review``.
        if size == "small" and environment == "unknown":
            item.add_marker("lane_fast")
        if "contract" in roles:
            item.add_marker("lane_contract")
        if environment in {"physical", "external", "machine_bound"}:
            item.add_marker("lane_machine")
        if environment == "optional":
            item.add_marker("lane_optional")
        if size == "unknown" or scope == "unknown" or environment == "unknown":
            item.add_marker("lane_review")


def pytest_collection_finish(session: pytest.Session) -> None:
    if not session.config.getoption("--area-report"):
        return
    areas: Counter[str] = Counter()
    roles: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    sizes: Counter[str] = Counter()
    scopes: Counter[str] = Counter()
    environments: Counter[str] = Counter()
    lanes: Counter[str] = Counter()
    for item in session.items:
        areas.update(mark.name.removeprefix("area_")
                     for mark in item.iter_markers() if mark.name.startswith("area_"))
        roles.update(mark.name.removeprefix("role_")
                     for mark in item.iter_markers() if mark.name.startswith("role_"))
        topics.update(mark.name.removeprefix("topic_")
                      for mark in item.iter_markers() if mark.name.startswith("topic_"))
        sizes.update(mark.name.removeprefix("size_")
                     for mark in item.iter_markers() if mark.name.startswith("size_"))
        scopes.update(mark.name.removeprefix("scope_")
                      for mark in item.iter_markers() if mark.name.startswith("scope_"))
        environments.update(mark.name.removeprefix("environment_")
                            for mark in item.iter_markers()
                            if mark.name.startswith("environment_"))
        lanes.update(mark.name.removeprefix("lane_")
                     for mark in item.iter_markers() if mark.name.startswith("lane_"))
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    reporter.write_line("AREA REPORT (overlap is intentional; counts are collected cases)")
    reporter.write_line("areas: " + ", ".join(f"{k}={v}" for k, v in sorted(areas.items())))
    reporter.write_line("roles: " + ", ".join(f"{k}={v}" for k, v in sorted(roles.items())))
    reporter.write_line("sizes: " + ", ".join(f"{k}={v}" for k, v in sorted(sizes.items())))
    reporter.write_line("scopes: " + ", ".join(f"{k}={v}" for k, v in sorted(scopes.items())))
    reporter.write_line(
        "environments: " + ", ".join(f"{k}={v}" for k, v in sorted(environments.items()))
    )
    reporter.write_line("lanes: " + ", ".join(f"{k}={v}" for k, v in sorted(lanes.items())))
    reporter.write_line("topics_top: " + ", ".join(f"{k}={v}" for k, v in topics.most_common(30)))
