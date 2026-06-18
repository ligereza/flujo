"""Tests del auto-checkpoint en Python puro (sin bash).

Regresión del bug en Windows: `run_auto_checkpoint` llamaba a `bash` y fallaba
con `execvpe(/bin/bash) failed` (Windows resolvía a bash de WSL). Ahora usa git
directamente. Estos tests verifican que NO dependa de bash y que pushee bien.
"""

import inspect
import subprocess
from pathlib import Path

import pytest

import flujo.airdrop as airdrop


def _has_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_git(), reason="git no disponible")


def test_no_invoca_bash():
    """El auto-checkpoint no debe LANZAR bash ni el script checkpoint.sh.

    (Se ignoran menciones en docstrings/comentarios; lo que importa es que no se
    ejecute bash, que es lo que rompía en Windows.)
    """
    import ast
    src = inspect.getsource(airdrop.run_auto_checkpoint)
    tree = ast.parse(src)
    func = tree.body[0]
    # eliminar el docstring del cuerpo para no falsear con menciones en texto
    if (func.body and isinstance(func.body[0], ast.Expr)
            and isinstance(getattr(func.body[0], "value", None), ast.Constant)):
        func.body = func.body[1:]
    code = ast.unparse(func)
    assert "bash" not in code
    assert "checkpoint.sh" not in code


def _init_repo(path: Path):
    bare = path / "remote.git"
    work = path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "t@t.com"], check=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(work), "checkout", "-q", "-b", "main"], check=True)
    (work / "context").mkdir()
    (work / "context" / "ESTADO.md").write_text("estado", encoding="utf-8")
    (work / "README.md").write_text("inicial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(work), "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(work), "push", "-q", "-u", "origin", "main"], check=True)
    return bare, work


def test_checkpoint_commitea_y_pushea(tmp_path, monkeypatch):
    bare, work = _init_repo(tmp_path)
    monkeypatch.setattr(airdrop, "repo_root", lambda: work)

    (work / "nuevo.txt").write_text("contenido", encoding="utf-8")
    ok = airdrop.run_auto_checkpoint("test commit y push")
    assert ok is True

    local = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
    remoto = subprocess.run(["git", "-C", str(bare), "rev-parse", "refs/heads/main"],
                            capture_output=True, text=True).stdout.strip()
    assert local == remoto, "el push no llegó al remoto"
    # se creó el archivo de checkpoint
    assert list((work / "checkpoints").glob("*.md"))


def test_checkpoint_reintenta_si_hook_modifica(tmp_path, monkeypatch):
    bare, work = _init_repo(tmp_path)
    monkeypatch.setattr(airdrop, "repo_root", lambda: work)

    # hook que modifica un archivo y aborta el primer commit
    hook = work / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "ch=0\n"
        "for f in $(git diff --cached --name-only); do\n"
        "  [ -f \"$f\" ] || continue\n"
        "  if [ -n \"$(tail -c1 \"$f\" 2>/dev/null)\" ]; then echo >> \"$f\"; ch=1; fi\n"
        "done\n"
        "[ \"$ch\" = 1 ] && { echo modificado; exit 1; } || exit 0\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)

    (work / "sin_newline.txt").write_text("texto sin salto", encoding="utf-8")
    ok = airdrop.run_auto_checkpoint("con hook")
    # En sistemas sin bash para hooks, el commit pasa directo igual => True.
    assert ok is True
    local = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
    remoto = subprocess.run(["git", "-C", str(bare), "rev-parse", "refs/heads/main"],
                            capture_output=True, text=True).stdout.strip()
    assert local == remoto


def test_checkpoint_sin_repo_git(tmp_path, monkeypatch):
    monkeypatch.setattr(airdrop, "repo_root", lambda: tmp_path)
    assert airdrop.run_auto_checkpoint("x") is False
