"""
TAPIZ TELEMETRY: Live self-portrait builder
Ecosystem: Tapiz <-> Psicosis <-> Fungi
Version: 1.0.0

build_live_ecosystem(repo_root=None) -> compete_engine.EcosystemState

Paints the ecosystem from REAL repo state using only cheap signals:
file names, byte sizes, counts, mtimes and short-timeout git plumbing.
The only file bodies ever sampled are the first line of
src/flujo/__init__.py and version/date tokens from versioned metadata.
Exported (decaying) asset content must stay names/sizes/counts/dates
only -- keep that invariant when adding builders.

PRIVACY (hard rule -- the exported JSON gets published):
  - Asset content is limited to names, sizes, counts, dates, git
    shorthashes and the first-line samples described above.
  - Nothing matching EXCLUDE_PATTERNS is ever listed, read or embedded.
  - Session JSONL files are only stat()'ed (size/mtime); their content
    is never opened.

Every signal degrades gracefully: missing dirs, absent git, unreadable
files are skipped or replaced by a fallback asset -- never a crash.
Stdlib only. Target budget: the full build stays well under ~2 seconds.
"""
import fnmatch
import os
import re
import subprocess
import sys
import time
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import compete_engine as ce

# ---------------------------------------------------------------------------
# Privacy exclusions (fnmatch, matched case-insensitively on basenames).
# Anything matching is invisible to every scanner in this module.
# ---------------------------------------------------------------------------
EXCLUDE_PATTERNS = [
    ".env*",
    "*.env",
    "*key*",
    "*secret*",
    "*token*",
    "*.local.md",
    "*credential*",
    "*password*",
    "tilde_log*",
    "*.pem",
    "*.csv",
    "id_rsa*",
    "id_ed25519*",
    "id_ecdsa*",
    "*.p12",
    "*.pfx",
    "*.ppk",
    "*.db",
    "*.sqlite*",
    ".npmrc",
    ".netrc",
    "*cookie*",
    "*clave*",
    "*contrasena*",
    "*credencial*",
    "config.json",
]

GIT_TIMEOUT = 1.5        # seconds per git plumbing call
SCAN_CAP = 4000          # max directory entries walked per fat zone
NAME_SAMPLE_MAX = 6      # max file/dir names quoted inside one asset
FILLER_CAP = 160_000     # cap on synthetic magnitude filler (chars)
FIRST_LINE_MAX = 120     # max chars kept from a first-line sample
SESSIONS_ROOT = Path.home() / ".claude" / "projects"

_VERSION_RE = re.compile(r"v?\d+\.\d+\.\d+")


def _is_excluded(name: str) -> bool:
    """True if a file/dir basename matches any privacy exclusion pattern."""
    low = name.lower()
    return any(fnmatch.fnmatch(low, pat) for pat in EXCLUDE_PATTERNS)


def _path_excluded(rel_path: str) -> bool:
    """True if ANY component of a relative path matches an exclusion.

    Git may C-quote paths with special chars ('"caf\\303\\251.txt"');
    surrounding quotes are stripped so the patterns still anchor.
    """
    rel = rel_path.strip().strip('"')
    return any(_is_excluded(part)
               for part in rel.replace("\\", "/").split("/") if part)


def _fmt_date(mtime: float) -> str:
    try:
        return time.strftime("%Y-%m-%d", time.localtime(mtime))
    except (OSError, OverflowError, ValueError):
        return "?"


def _fmt_mb(n_bytes: int) -> str:
    return "%.1f MB" % (n_bytes / (1024.0 * 1024.0))


def _git(repo_root: Path, *args: str):
    """Run a git plumbing command; return stripped stdout or None on any failure."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _dir_stats(path: Path, cap: int = SCAN_CAP):
    """Cheap recursive stat of a directory (capped walk, exclusions applied).

    Returns dict {files, bytes, mtime, names, capped} or None if missing.
    Only os.stat is used -- file content is never opened.
    """
    if not path.is_dir():
        return None
    files, total, newest, seen, capped = 0, 0, 0.0, 0, False
    names = []
    try:
        for root, dirs, fnames in os.walk(path):
            dirs[:] = [d for d in dirs if not _is_excluded(d)]
            if root == str(path):
                names = [n for n in (sorted(dirs) + sorted(fnames))
                         if not _is_excluded(n)][:NAME_SAMPLE_MAX]
            for fn in fnames:
                seen += 1
                if seen > cap:
                    capped = True
                    break
                if _is_excluded(fn):
                    continue
                try:
                    st = os.stat(os.path.join(root, fn))
                except OSError:
                    continue
                files += 1
                total += st.st_size
                if st.st_mtime > newest:
                    newest = st.st_mtime
            if capped:
                break
    except OSError:
        return None
    if newest == 0.0:
        try:
            newest = path.stat().st_mtime
        except OSError:
            newest = time.time()
    return {"files": files, "bytes": total, "mtime": newest,
            "names": names, "capped": capped}


def _first_line(path: Path, max_chars: int = FIRST_LINE_MAX):
    """First non-empty line of an ALLOWED file, sanitized and truncated."""
    if _is_excluded(path.name):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = "".join(c for c in line.strip() if c.isprintable())
                if line:
                    return line[:max_chars]
    except OSError:
        return None
    return None


def _version_token(path: Path):
    """Extract only a version token (v0.51.0 style) from a file header.

    Reads at most 2 KB and returns just the regex match -- never the line.
    """
    if _is_excluded(path.name):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(2048)
    except OSError:
        return None
    m = _VERSION_RE.search(head)
    return m.group(0) if m else None


def _pyproject_version(path: Path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except OSError:
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', head, re.MULTILINE)
    return m.group(1) if m else None


def _session_stats(repo_root: Path):
    """Count and total-size the Claude session JSONL files for this repo.

    stat() only -- session content is NEVER opened (it may embed pasted
    secrets from past sessions). Returns (count, bytes, newest_mtime).
    """
    try:
        slug = re.sub(r"[\\/:.]", "-", str(repo_root))
        base = slug.split("--claude-worktrees")[0]
        count, total, newest = 0, 0, 0.0
        if SESSIONS_ROOT.is_dir():
            for d in SESSIONS_ROOT.glob(base + "*"):
                if not d.is_dir():
                    continue
                for j in d.glob("*.jsonl"):
                    try:
                        st = j.stat()
                    except OSError:
                        continue
                    count += 1
                    total += st.st_size
                    if st.st_mtime > newest:
                        newest = st.st_mtime
        return count, total, newest
    except Exception:
        return 0, 0, 0.0


# ---------------------------------------------------------------------------
# Asset builders. Each receives (state, root, now) and may add assets or
# event_log entries. Any exception inside one builder is swallowed by the
# orchestrator so a single bad signal never kills the portrait.
# ---------------------------------------------------------------------------

_FAT_ZONES = [
    ("FUN-001", "Masa Jobs", "jobs", ["fungi", "binary_mass", "decay"]),
    ("FUN-002", "Esporas SVG RD", "svg/suplementos_rd",
     ["fungi", "svg", "active_render"]),
    ("FUN-003", "Datadrop Sediment", "datadrops", ["fungi", "drop"]),
]


def _build_fungi_zones(state, root, now):
    for aid, name, rel, tags in _FAT_ZONES:
        stats = _dir_stats(root / rel.replace("/", os.sep))
        if stats is None:
            continue
        content = "%s/: %d files, %s, last touch %s; entries: %s%s" % (
            rel, stats["files"], _fmt_mb(stats["bytes"]),
            _fmt_date(stats["mtime"]), ", ".join(stats["names"]) or "(none)",
            " (walk capped)" if stats["capped"] else "",
        )
        asset = ce.ArtAsset(
            aid, name, content,
            ce.MetadataLayer("Accumulated repo mass decomposing in place",
                             list(tags), True),
            ce.EntityState.DECAYING, stats["mtime"],
        )
        state.decaying_assets[asset.asset_id] = asset


def _build_tapiz_core(state, root, now):
    init = root / "src" / "flujo" / "__init__.py"
    line = _first_line(init)
    if line is None:
        return
    try:
        mtime = init.stat().st_mtime
    except OSError:
        mtime = now
    asset = ce.ArtAsset(
        "TAP-001", "Tapiz Core",
        'src/flujo/__init__.py first line: "%s"' % line,
        ce.MetadataLayer("Woven core package of the repo",
                         ["tapiz", "python"], True),
        ce.EntityState.ACTIVE, mtime,
    )
    state.active_assets[asset.asset_id] = asset


def _build_tapiz_tooling(state, root, now):
    stats = _dir_stats(root / "tools")
    if stats is None:
        return
    asset = ce.ArtAsset(
        "TAP-002", "Telar Tooling",
        "tools/: %d files, %s, last touch %s" % (
            stats["files"], _fmt_mb(stats["bytes"]), _fmt_date(stats["mtime"])),
        ce.MetadataLayer("The loom that weaves the repo",
                         ["tapiz", "tooling"], True),
        ce.EntityState.ACTIVE, stats["mtime"],
    )
    state.active_assets[asset.asset_id] = asset


def _build_token_pressure(state, root, now):
    """Real magnitude -> mesh pressure.

    The biggest compiled context/*.html bundle and the session JSONL
    volume are measured (stat only), then re-expressed as a synthetic
    'x' filler whose LENGTH carries the magnitude into the
    TokenVolumetricAnalyzer. No real file content is embedded.
    """
    html_max, html_count = 0, 0
    ctx = root / "context"
    if ctx.is_dir():
        try:
            for h in ctx.glob("*.html"):
                if _is_excluded(h.name):
                    continue
                try:
                    size = h.stat().st_size
                except OSError:
                    continue
                html_count += 1
                if size > html_max:
                    html_max = size
        except OSError:
            pass
    ses_count, ses_bytes, _ = _session_stats(root)

    chars = min(FILLER_CAP, max(html_max, ses_bytes // 256))
    header = ("context bundles: %d html, biggest %d bytes; "
              "session logs: %d jsonl, %s (stat only); "
              "magnitude re-expressed as %d filler chars" % (
                  html_count, html_max, ses_count, _fmt_mb(ses_bytes), chars))
    asset = ce.ArtAsset(
        "TAP-003", "Presion Compilada",
        header + "\n" + ("x" * chars),
        ce.MetadataLayer("Real compiled-bundle and session mass as token pressure",
                         ["tapiz", "compiled", "telemetry"], True),
        ce.EntityState.ACTIVE, now,
    )
    state.active_assets[asset.asset_id] = asset

    sessions = ce.ArtAsset(
        "SES-001", "Memoria de Sesiones",
        "session jsonl under ~/.claude/projects: %d files, %s "
        "(sizes only; content never read)" % (ses_count, _fmt_mb(ses_bytes)),
        ce.MetadataLayer("Weight of past conversations",
                         ["tapiz", "telemetry", "sessions"], True),
        ce.EntityState.ACTIVE, now,
    )
    state.active_assets[sessions.asset_id] = sessions


def _build_version_lag(state, root, now):
    decl = _version_token(root / "context" / "AVANCES_BLOCK.txt")
    pyver = _pyproject_version(root / "pyproject.toml")
    if decl is None and pyver is None:
        return
    lag = bool(decl and pyver and decl.lstrip("v") != pyver.lstrip("v"))
    content = "context/AVANCES_BLOCK.txt declares %s; pyproject.toml says %s%s" % (
        decl or "?", pyver or "?", "; VERSION LAG" if lag else "")
    asset = ce.ArtAsset(
        "PSI-001", "Avances Desfasados", content,
        ce.MetadataLayer("Context block lagging behind the living version",
                         ["psicosis", "version_lag"], True),
        ce.EntityState.DECAYING if lag else ce.EntityState.ACTIVE, now,
    )
    # Still consumed as live context -> active; if it lags, it is also
    # decaying: a real state violation the concurrency analyzer will flag.
    state.active_assets[asset.asset_id] = asset
    if lag:
        state.decaying_assets[asset.asset_id] = asset


def _build_untracked_engine(state, root, now):
    # quotePath=false: git would C-quote unicode/special-char names, which
    # garbles the sample and defeats end-anchored exclusion patterns.
    porcelain = _git(root, "-c", "core.quotePath=false", "status", "--porcelain")
    if porcelain is None:
        return
    untracked = [ln[3:].strip().strip('"') for ln in porcelain.splitlines()
                 if ln.startswith("?? ")]
    untracked = [u for u in untracked if u and not _path_excluded(u)]
    if not untracked:
        return
    sample = ", ".join(untracked[:NAME_SAMPLE_MAX])
    extra = len(untracked) - NAME_SAMPLE_MAX
    tags = ["psicosis", "untracked"]
    if any(u.replace("\\", "/").startswith("tools/") for u in untracked):
        # The engine analyzing its own uncommitted self: a real
        # Decay-Render race (fresh mtime + active_render tag).
        tags.append("active_render")
    asset = ce.ArtAsset(
        "PSI-002", "Motor No Tejido",
        "git status untracked: %s%s" % (
            sample, " (+%d more)" % extra if extra > 0 else ""),
        ce.MetadataLayer("Files not woven into the repo they describe",
                         tags, True),
        ce.EntityState.DECAYING, now,
    )
    state.decaying_assets[asset.asset_id] = asset


def _build_stale_todo(state, root, now):
    todos = root / "docs" / "todos"
    if not todos.is_dir():
        return
    try:
        candidates = sorted(p for p in todos.glob("*.md")
                            if not _is_excluded(p.name))
    except OSError:
        return
    if not candidates:
        return
    todo = candidates[0]
    try:
        mtime = todo.stat().st_mtime
    except OSError:
        mtime = now
    age_days = max(0.0, (now - mtime) / 86400.0)
    tags = ["psicosis", "todo"]
    if age_days > 7:
        tags.append("stale")
    asset = ce.ArtAsset(
        "PSI-003", "Handoff Fantasma",
        "docs/todos/%s: last touch %s (%.0f days ago)" % (
            todo.name, _fmt_date(mtime), age_days),
        ce.MetadataLayer("A todo that outlived the job it points at",
                         tags, True),
        ce.EntityState.DECAYING, mtime,
    )
    state.decaying_assets[asset.asset_id] = asset


def _build_repo_vitals(state, root, now):
    head = _git(root, "rev-parse", "--short", "HEAD")
    commits_14d = _git(root, "rev-list", "--count", "--since=14.days", "HEAD")
    worktrees = _git(root, "worktree", "list", "--porcelain")
    ses_count, ses_bytes, _ = _session_stats(root)
    state.event_log.append({
        "event": "repo_vitals",
        "timestamp": now,
        "head": head,
        "commits_14d": int(commits_14d) if commits_14d and commits_14d.isdigit() else None,
        "worktrees_locked": (sum(1 for ln in worktrees.splitlines()
                                 if ln.startswith("locked"))
                             if worktrees else None),
        "pyproject_version": _pyproject_version(root / "pyproject.toml"),
        "session_jsonl": ses_count,
        "session_bytes": ses_bytes,
    })
_BUILDERS = [
    _build_fungi_zones,
    _build_tapiz_core,
    _build_tapiz_tooling,
    _build_token_pressure,
    _build_version_lag,
    _build_untracked_engine,
    _build_stale_todo,
    _build_repo_vitals,
]


def build_live_ecosystem(repo_root=None) -> "ce.EcosystemState":
    """Build an EcosystemState from real repo signals. Never raises."""
    if repo_root is None:
        root = Path(__file__).resolve().parents[1]
    else:
        root = Path(repo_root)
    state = ce.EcosystemState()
    now = time.time()
    for builder in _BUILDERS:
        try:
            builder(state, root, now)
        except Exception:
            continue  # one dead signal never kills the portrait
    if not state.active_assets and not state.decaying_assets:
        void = ce.ArtAsset(
            "VOID-001", "Telar Vacio",
            "no live signals found under '%s'" % root.name,
            ce.MetadataLayer("An empty loom still hums", ["tapiz", "void"], True),
            ce.EntityState.ACTIVE, now,
        )
        state.active_assets[void.asset_id] = void
    return state


if __name__ == "__main__":
    # Tiny smoke: print asset ids and content lengths, nothing else.
    _state = build_live_ecosystem()
    for _label, _pool in (("active", _state.active_assets),
                          ("decaying", _state.decaying_assets)):
        for _aid, _a in sorted(_pool.items()):
            print("%s %s %s (%d chars)" % (_label, _aid, _a.name, len(_a.content)))
    print("event_log entries: %d" % len(_state.event_log))
