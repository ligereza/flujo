"""Language meter for Python comments and docstrings, offline and deterministic.

Why this exists (2026-07-31): the repository language policy says code is written in English,
but the tree was measured at ~236 Python files with Spanish comments against
~36 in English (2026-07-30), and nothing measured it continuously -- the number
rots the day after it is written. This tool re-measures on demand and feeds the
ratchet in tests/test_idioma_ratchet.py, which stops NEW files from adding
Spanish comments without ever forcing a rename (renames break cron lines and
systemd units that invoke the old names).

What is measured -- and, just as important, what is NOT:

- The full tree measurement classifies comments (# ...) and docstrings.
  Identifiers remain a soft FYI for the historical tree.
- A change ratchet also inspects newly declared identifiers in changed or
  untracked Python files. Existing public names are compared with HEAD and
  remain allowed for compatibility; new declarations must use English ASCII.
- Ordinary string literals are left alone because product text is legitimately
  Spanish with diacritics and must never be accused.
- The full measurement uses `git ls-files -- '*.py'`. The change ratchet also
  reads untracked Python files deliberately, so new work cannot hide from it.
- Files under DEAD_ZONE (archives), FOREIGN_ZONE (vendorized, third-party) and
  QUARANTINE_ZONE (reversible evidence) are excluded: the instrument must
  earn the right to accuse a file, and quarantine is not active code. Same
  convention as tests/test_higiene_docs.py.

The heuristic, in full (it is deliberately transparent -- no model, no network):

1. Comments are collected with the `tokenize` module; docstrings with `ast`
   (module, class and function docstrings only). A file that fails to parse
   contributes whatever tokens were readable before the failure.
2. Words are lowercased runs of letters (including accented vowels and enie).
3. Evidence is counted per file:
   - Spanish stopword hit (unambiguous function words: "que", "para", "el",
     "la", "esto"...): +1 each. Words that are also English ("no", "a") or
     one-letter words ("y", "o", "e") are excluded from both sides.
   - Word carrying a Spanish-only mark (accented vowel, u-dieresis, enie) or
     an inverted question/exclamation mark in the text: +2 each -- diacritics
     are the strongest signal.
   - N-gram hint: word ending in "cion"/"ciones" (English uses "tion"): +1.
   - English stopword hit ("the", "and", "with", "this"...): +1 each.
4. Per-file verdict from the two totals (es, en):
   - es + en < 2         -> "none"   (no comments, or no language evidence;
                                      a lone "de" in "de-duplicate" accuses
                                      nobody)
   - en == 0             -> "es"
   - es == 0             -> "en"
   - es >= 3 * en        -> "es"     (a stray English word in a Spanish file
   - en >= 3 * es        -> "en"      does not flip the verdict, and vice versa)
   - otherwise           -> "mixed"

The ratchet pins the set of files whose verdict is "es" or "mixed" -- i.e.
every file carrying Spanish-classified comments.

CLI:
    python3 tools/idioma.py             # human report + one JSON line
    python3 tools/idioma.py --files     # adds the full per-file listing
    python3 tools/idioma.py --baseline  # prints the offender set, one path per
                                        # line, ready to redirect into
                                        # tests/fixtures/idioma_baseline.txt

Soft FYI for the historical tree: Spanish identifier stems used across many
files that docs/GLOSSARY.md does not mention. Detection is high-precision on
purpose (curated stem list + "cion" endings + diacritics). The change ratchet
uses the same detector only for newly declared names.
"""

from __future__ import annotations

import ast
import io
import json
import keyword
import re
import subprocess
import sys
import tokenize
import warnings
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Same convention as tests/test_higiene_docs.py: archives are history, not
# code anyone maintains; vendorized libraries are third-party and not ours to
# accuse.
DEAD_ZONE = (
    ".archive/",
    "_archive/",
    "context-history/",
    "projects/cultura/corpus_olvido/",
)
FOREIGN_ZONE = (
    "docs/cultura/lib/",
    "iskvw/piel/lib/",
)
QUARANTINE_ZONE = (
    "context/quarantine/",
)

# Unambiguous Spanish function words. Deliberately absent: "no" and "a"
# (English), every one-letter word ("y", "o", "e", "u" collide with variable
# names in comments), and "de" (appears in English prose: "de-duplicate",
# "de facto"). Accent-stripped variants are included because much of the
# tree writes Spanish comments in plain ASCII.
SPANISH_STOPWORDS = frozenset("""
el la los las un una unos unas del al lo le les que en se su sus es son esta
estan este esto estos estas ese esa eso esos esas aqui alli hay fue ser hace
hacia desde hasta tambien segun porque como cuando donde cada mas pero por para
con sin sobre entre muy ya todo toda todos todas otro otra otros otras mismo
misma nada nunca siempre algo alguien ningun ninguna tiene tienen puede pueden
debe deben asi aunque dentro fuera antes despues ahora luego solo si ni cual
cuales quien quienes cuanto cuantos donde
está están más también según después aquí allí así sólo qué cómo dónde cuándo
sí ningún
""".split())

# Unambiguous English function words ("no" excluded: Spanish too).
ENGLISH_STOPWORDS = frozenset("""
the and of to is that this for with not are was were from has have had it its
be by on as an or if we you they their there which what when where how all
each one two new only never always into then than them these those should
would can cannot must may does did done being been because before after
between without under over every any some most more but so at in up out about
against while during through
""".split())

SPANISH_MARKS = "áéíóúüñÁÉÍÓÚÜÑ"
INVERTED_PUNCT = "¿¡"

_WORD_RE = re.compile(r"[a-zA-Z%s]+" % SPANISH_MARKS)

# ---------------------------------------------------------------------------
# extraction


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def comment_and_docstring_text(source: str) -> str:
    """Everything a human wrote as commentary: # comments plus docstrings.

    Identifiers and ordinary string literals are deliberately NOT included --
    product data in Spanish is correct and must not count against a file.
    """
    parts: List[str] = []
    # Comments, tolerant of files that stop tokenizing halfway.
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                parts.append(tok.string.lstrip("#"))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        pass
    # Docstrings via the real grammar, not a guess about string positions.
    # Measured files are not on trial for their escape sequences here, so
    # their SyntaxWarning/DeprecationWarning noise is muted.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return "\n".join(parts)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                parts.append(doc)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# classification


def score_text(text: str) -> Tuple[int, int]:
    """(spanish_evidence, english_evidence) for a blob of commentary text."""
    es = 0
    en = 0
    for raw in _WORD_RE.findall(text):
        word = raw.lower()
        if any(ch in SPANISH_MARKS for ch in word):
            es += 2
            continue
        if word in SPANISH_STOPWORDS:
            es += 1
        elif word in ENGLISH_STOPWORDS:
            en += 1
        elif len(word) > 5 and (word.endswith("cion") or word.endswith("ciones")):
            es += 1
    es += 2 * sum(1 for ch in text if ch in INVERTED_PUNCT)
    return es, en


def classify(es: int, en: int) -> str:
    if es + en < 2:
        return "none"
    if en == 0:
        return "es"
    if es == 0:
        return "en"
    if es >= 3 * en:
        return "es"
    if en >= 3 * es:
        return "en"
    return "mixed"


# ---------------------------------------------------------------------------
# measurement over the repo


def tracked_python_files(root: Path = ROOT) -> List[str]:
    """`git ls-files`, never a disk walk: uncommitted files must not distort
    the measurement (lesson pinned in tests/test_higiene_docs.py)."""
    r = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=root, capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError("not a usable git checkout: " + r.stderr.strip())
    files = [f for f in r.stdout.splitlines() if f]
    return [
        f for f in files
        if not f.startswith(DEAD_ZONE)
        and not f.startswith(FOREIGN_ZONE)
        and not f.startswith(QUARANTINE_ZONE)
    ]


def changed_python_files(root: Path = ROOT) -> List[str]:
    """Return tracked changes plus untracked Python files in the worktree.

    This is intentionally narrower than a disk walk: only files Git considers
    project work are included, while untracked Python files are included so a
    new test or module cannot evade the change ratchet before staging.
    """
    changed = subprocess.run(
        ["git", "diff", "HEAD", "--name-only", "--diff-filter=ACMR", "--", "*.py"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
    )
    if changed.returncode != 0:
        raise RuntimeError("not a usable git checkout: " + changed.stderr.strip())
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
    )
    if untracked.returncode != 0:
        raise RuntimeError("could not list untracked Python files: " +
                           untracked.stderr.strip())
    files = set(changed.stdout.splitlines())
    files.update(untracked.stdout.splitlines())
    return sorted(
        f for f in files if f and not f.startswith(DEAD_ZONE)
        and not f.startswith(FOREIGN_ZONE)
        and not f.startswith(QUARANTINE_ZONE)
    )


def _source_at_head(root: Path, relative: str) -> Optional[str]:
    """Read a tracked file at HEAD, or return None for a new file."""
    result = subprocess.run(
        ["git", "show", "HEAD:" + relative], cwd=root, capture_output=True,
        text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        return None
    return result.stdout


def declared_identifiers(source: str) -> set[str]:
    """Return names declared by Python syntax, not ordinary references."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = (list(node.args.posonlyargs) + list(node.args.args) +
                        list(node.args.kwonlyargs))
                names.update(arg.arg for arg in args)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return names


def new_spanish_identifiers(root: Path = ROOT) -> List[Tuple[str, str]]:
    """Return newly declared Spanish-looking names in changed Python files."""
    offenders = []
    for relative in changed_python_files(root):
        current = _read_text(root / relative)
        previous = _source_at_head(root, relative)
        old_names = declared_identifiers(previous or "")
        for name in sorted(declared_identifiers(current) - old_names):
            if _looks_spanish_identifier(name):
                offenders.append((relative, name))
    return offenders


def new_spanish_comment_files(root: Path = ROOT) -> List[str]:
    """Return changed files that newly become Spanish-comment offenders."""
    offenders = []
    for relative in changed_python_files(root):
        current = _read_text(root / relative)
        current_es, current_en = score_text(comment_and_docstring_text(current))
        current_verdict = classify(current_es, current_en)
        if current_verdict not in ("es", "mixed"):
            continue
        previous = _source_at_head(root, relative)
        if previous is None:
            offenders.append(relative)
            continue
        old_es, old_en = score_text(comment_and_docstring_text(previous))
        old_verdict = classify(old_es, old_en)
        if old_verdict not in ("es", "mixed"):
            offenders.append(relative)
    return offenders


def measure(root: Path = ROOT) -> Dict:
    """Full measurement. Returns a dict the test and the CLI both consume."""
    per_file: Dict[str, Dict] = {}
    for rel in tracked_python_files(root):
        text = comment_and_docstring_text(_read_text(root / rel))
        es, en = score_text(text)
        per_file[rel] = {"es": es, "en": en, "verdict": classify(es, en)}
    counts = Counter(v["verdict"] for v in per_file.values())
    offenders = sorted(
        rel for rel, v in per_file.items() if v["verdict"] in ("es", "mixed")
    )
    return {
        "total": len(per_file),
        "counts": {k: counts.get(k, 0) for k in ("es", "en", "mixed", "none")},
        "spanish_files": offenders,
        "per_file": per_file,
    }


# ---------------------------------------------------------------------------
# soft FYI: Spanish identifiers missing from the glossary

# High-precision stems of Spanish words this repo actually uses in names.
# The list is data, not law: extending it widens the FYI, nothing else.
SPANISH_ID_STEMS = frozenset("""
archivo archivos borrador borradores busca buscar cadena camina caminar campo
capa capas carga cargar carpeta cifra cifras cola comando comandos conteo
contrato corre corrida corridas crea crear cuenta cuerpo datos entrada
entradas entrega entregar escribe escribir evento eventos fecha fechas ficha
fichas fila filas fuente fuentes genera generar guarda guardar herramienta
herramientas idioma informe informes lee leer linea lineas listar llave llaves
medida medido medir muestra mostrar nombre numero obra obras ofensa ofensas
palabra palabras pieza piezas plantilla prueba pruebas registro resumen ruta
rutas sala salida salidas tabla tablas tamano texto valor valores vinculo
vinculos zona zonas accion acciones activo activa barrera contenido detalle
destino decidir estado estados fuente guardia indice instalar limpiar
nota parcial resultado resultados reconstruir serializa serializar tocar
trabajo
""".split())


def spanish_identifiers(root: Path = ROOT, min_files: int = 4) -> List[Tuple[str, int]]:
    """Identifiers with a Spanish-looking part, used in >= min_files files.

    Returns (identifier, file_count) sorted by spread, widest first. Purely
    informative: enforcement would demand renames, and renames break the
    cron/systemd consumers the language rule explicitly protects.
    """
    ident_files: Dict[str, set] = {}
    name_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    for rel in tracked_python_files(root):
        source = _read_text(root / rel)
        seen = set()
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type == tokenize.NAME and not keyword.iskeyword(tok.string):
                    seen.add(tok.string)
        except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
            seen.update(name_re.findall(source))
        for name in seen:
            if _looks_spanish_identifier(name):
                ident_files.setdefault(name, set()).add(rel)
    spread = [(n, len(fs)) for n, fs in ident_files.items() if len(fs) >= min_files]
    return sorted(spread, key=lambda t: (-t[1], t[0]))


def _looks_spanish_identifier(name: str) -> bool:
    parts = re.split(r"[_\d]+", re.sub(r"(?<=[a-z])(?=[A-Z])", "_", name).lower())
    for part in parts:
        if not part:
            continue
        if part in SPANISH_ID_STEMS:
            return True
        if any(ch in SPANISH_MARKS for ch in part):
            return True
        if len(part) > 5 and (part.endswith("cion") or part.endswith("ciones")):
            return True
    return False


def glossary_misses(root: Path = ROOT, min_files: int = 4) -> List[Tuple[str, int]]:
    glossary = root / "docs" / "GLOSSARY.md"
    text = glossary.read_text(encoding="utf-8").lower() if glossary.exists() else ""
    misses = []
    for name, n in spanish_identifiers(root, min_files):
        parts = [p for p in re.split(r"[_\d]+", name.lower()) if p]
        if not any(p in text for p in parts if _looks_spanish_identifier(p)):
            misses.append((name, n))
    return misses


# ---------------------------------------------------------------------------
# CLI


def _report(root: Path, show_files: bool) -> str:
    m = measure(root)
    c = m["counts"]
    lines: List[str] = []
    lines.append("idioma -- language of comments/docstrings in tracked *.py")
    lines.append("(comments and docstrings ONLY; identifiers and product "
                 "strings are never counted)")
    lines.append("")
    lines.append("total files measured: %d" % m["total"])
    lines.append("  es (Spanish): %d" % c["es"])
    lines.append("  en (English): %d" % c["en"])
    lines.append("  mixed:        %d" % c["mixed"])
    lines.append("  none:         %d  (no comments, or no language evidence)" % c["none"])
    lines.append("  carrying Spanish (es + mixed, the ratchet's number): %d"
                 % len(m["spanish_files"]))
    lines.append("")
    lines.append("per top-level dir (es/en/mixed/none):")
    by_dir: Dict[str, Counter] = {}
    for rel, v in m["per_file"].items():
        top = rel.split("/", 1)[0] if "/" in rel else "."
        by_dir.setdefault(top, Counter())[v["verdict"]] += 1
    for top in sorted(by_dir, key=lambda d: -sum(by_dir[d].values())):
        d = by_dir[top]
        lines.append("  %-22s %3d / %3d / %3d / %3d" % (
            top, d.get("es", 0), d.get("en", 0), d.get("mixed", 0), d.get("none", 0)))
    lines.append("")
    top_offenders = sorted(
        ((rel, v) for rel, v in m["per_file"].items() if v["verdict"] in ("es", "mixed")),
        key=lambda t: -t[1]["es"],
    )[:15]
    lines.append("top offenders (most Spanish evidence):")
    for rel, v in top_offenders:
        lines.append("  %4d es / %4d en  %s  (%s)" % (v["es"], v["en"], rel, v["verdict"]))
    if show_files:
        lines.append("")
        lines.append("every file carrying Spanish comments:")
        for rel in m["spanish_files"]:
            lines.append("  " + rel)
    lines.append("")
    misses = glossary_misses(root)[:20]
    lines.append("FYI (not enforced): Spanish identifiers in >= 4 files, "
                 "absent from docs/GLOSSARY.md:")
    if misses:
        for name, n in misses:
            lines.append("  %-28s in %d files" % (name, n))
    else:
        lines.append("  none found")
    lines.append("")
    machine = {"total": m["total"], "counts": c,
               "spanish_carrying": len(m["spanish_files"])}
    lines.append("JSON: " + json.dumps(machine, sort_keys=True))
    return "\n".join(lines)


def _baseline(root: Path) -> str:
    m = measure(root)
    out = ["# Files carrying Spanish comments/docstrings (verdict es or mixed),",
           "# measured by `python3 tools/idioma.py --baseline`. Consumed by",
           "# tests/test_idioma_ratchet.py as the ratchet's ceiling: shrinking",
           "# this list is always welcome, growing it fails the suite."]
    out += list(m["spanish_files"])
    return "\n".join(out)


def main(argv: List[str]) -> int:
    if "--baseline" in argv:
        print(_baseline(ROOT))
        return 0
    print(_report(ROOT, show_files="--files" in argv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
