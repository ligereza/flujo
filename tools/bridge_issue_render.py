#!/usr/bin/env python3
"""Puente Windows: issue de GitHub (label "instagram") -> flyer-auto Blender -> drive/.

Gmail -> issue ya esta hecho (fuera de este repo, label real = "instagram",
"Contains Instagram link"). Este script cierra el otro lado: ve issues
abiertos con esa label, saca el link de Instagram, corre
`flujo eventos flyer-auto --render-blender --yes --blender-exe <ruta real>`
(Blender directo por nodos, sin Photoshop Droplet -- ver docs/BLENDER_FLYERS.md),
copia el PNG resultante a drive/ (sincroniza solo via Google Drive/rclone) y
comenta+cierra el issue con el resultado.

Foreground, no servicio: correlo solo cuando Windows esta prendido y vos
estas presente (autoriza lanzar Blender). Ctrl+C para parar.

Uso:
  py tools/bridge_issue_render.py                # loop, 60s
  py tools/bridge_issue_render.py --once          # una pasada, sale
  py tools/bridge_issue_render.py --interval 30
  py tools/bridge_issue_render.py --dry-run       # no corre flyer-auto ni comenta/cierra
"""
import argparse
import json
import shutil
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = "ligereza/vibecodeine"
LABEL = "instagram"  # "Contains Instagram link" -- label real del intake Gmail->issue
BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
STATE_FILE = Path(__file__).resolve().parent.parent / "_logs" / "bridge_issue_render_state.json"
IG_URL_RE = re.compile(r"https://www\.instagram\.com/[^\s\)\]]+", re.IGNORECASE)


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"processed": {}}
    return {"processed": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def _open_issues() -> list[dict]:
    res = _gh(
        "issue", "list", "--repo", REPO, "--label", LABEL, "--state", "open",
        "--json", "number,title,body", "--limit", "50",
    )
    if res.returncode != 0:
        print(f"[error] gh issue list: {res.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        return []


def _extract_ig_url(body: str) -> str | None:
    m = IG_URL_RE.search(body or "")
    return m.group(0) if m else None


SHORTCODE_RE = re.compile(r"instagram\.com/(?:[^/]+/)?(?:p|reel)/([^/?#]+)", re.IGNORECASE)


def _extract_shortcode(url: str) -> str | None:
    m = SHORTCODE_RE.search(url)
    return m.group(1) if m else None


def _run_flyer_auto(url: str) -> tuple[bool, str, Path | None]:
    res = subprocess.run(
        [sys.executable, "-m", "flujo", "eventos", "flyer-auto", url,
         "--render-blender", "--yes", "--blender-exe", BLENDER_EXE],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=Path(__file__).resolve().parent.parent,
    )
    output = (res.stdout or "") + (("\n" + res.stderr) if res.stderr else "")
    render_png = None
    m = re.search(r"Render guardado en:\s*(.+\.png)", output)
    if m:
        p = Path(m.group(1).strip())
        if p.exists():
            render_png = p
    return res.returncode == 0, output.strip(), render_png


DRIVE_DIR = Path(__file__).resolve().parent.parent / "drive"


def _copy_to_drive(render_png: Path, number: int, shortcode: str) -> Path | None:
    try:
        DRIVE_DIR.mkdir(parents=True, exist_ok=True)
        dest = DRIVE_DIR / f"render_issue{number}_{shortcode}.png"
        shutil.copy2(render_png, dest)
        return dest
    except Exception as e:
        print(f"[error] copiando a drive/: {e}", file=sys.stderr)
        return None


# Corta en comilla o fin de linea, no en espacio: "Program Files" y "Blender 4.5"
# llevan espacios y cortar ahi dejaba media ruta publicada.
_RUTA_WIN_RE = re.compile(r"[A-Za-z]:\\[^\"'\r\n]*")


def _sin_rutas(texto: str) -> str:
    """Saca las rutas absolutas de Windows del log antes de publicarlo.

    El log de Blender viene lleno de `C:\\Users\\<usuario>\\AppData\\...` y el
    issue es publico. Se conserva el nombre del archivo, que es lo unico que
    sirve para diagnosticar; el resto de la ruta no aporta y expone el disco.
    """
    return _RUTA_WIN_RE.sub(lambda m: ".../" + m.group(0).rsplit("\\", 1)[-1], texto or "")


def _comment_and_close(number: int, ok: bool, url: str, output: str, drive_path: Path | None, dry_run: bool) -> None:
    status = "OK" if ok else "FALLO"
    # Solo el nombre del archivo: el issue es PUBLICO y la ruta absoluta publica
    # la estructura del disco del usuario. Medido en el issue #320, que quedo
    # cerrado con `C:\...` a la vista. La carpeta es siempre drive/, asi que el
    # nombre alcanza para encontrarlo.
    extra = f"\n\nRender en `drive/`: `{drive_path.name}`" if drive_path else ""
    body = (f"Puente Windows: render {status} para {url}{extra}\n\n"
            f"```\n{_sin_rutas(output)[-3500:]}\n```")
    if dry_run:
        print(f"[dry-run] comentaria issue #{number} ({status}):\n{body}")
        return
    c = _gh("issue", "comment", str(number), "--repo", REPO, "--body", body)
    if c.returncode != 0:
        print(f"[error] gh issue comment #{number}: {c.stderr.strip()}", file=sys.stderr)
    if ok:
        cl = _gh("issue", "close", str(number), "--repo", REPO)
        if cl.returncode != 0:
            print(f"[error] gh issue close #{number}: {cl.stderr.strip()}", file=sys.stderr)


def run_once(dry_run: bool = False, only_issue: int | None = None) -> int:
    state = _load_state()
    processed = state.setdefault("processed", {})
    issues = _open_issues()
    if only_issue is not None:
        issues = [i for i in issues if i["number"] == only_issue]
    handled = 0
    for issue in issues:
        number = issue["number"]
        key = str(number)
        if key in processed and only_issue is None:
            continue
        url = _extract_ig_url(issue.get("body", ""))
        if not url:
            print(f"[skip] issue #{number}: sin link de Instagram en el body")
            continue
        print(f"[render] issue #{number}: {url}")
        if dry_run:
            ok, output, render_png = True, "[dry-run] no se corrio flyer-auto", None
        else:
            ok, output, render_png = _run_flyer_auto(url)
        print(output)
        drive_path = None
        if ok and render_png:
            shortcode = _extract_shortcode(url) or "unk"
            drive_path = _copy_to_drive(render_png, number, shortcode)
        _comment_and_close(number, ok, url, output, drive_path, dry_run)
        processed[key] = {
            "url": url, "ok": ok,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        handled += 1
        if not dry_run:
            _save_state(state)
    return handled


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="una pasada y sale (no loop)")
    ap.add_argument("--interval", type=int, default=60, help="segundos entre pasadas (default 60)")
    ap.add_argument("--dry-run", action="store_true", help="no corre flyer-auto ni comenta/cierra")
    ap.add_argument("--issue", type=int, default=None, help="procesar solo este numero de issue")
    args = ap.parse_args()

    print(f"Puente issue->render activo. repo={REPO} label={LABEL} "
          f"state={STATE_FILE}{' [dry-run]' if args.dry_run else ''}"
          f"{f' [issue #{args.issue}]' if args.issue else ''}")
    if args.once or args.issue:
        n = run_once(dry_run=args.dry_run, only_issue=args.issue)
        print(f"listo: {n} issue(s) procesado(s)")
        return
    try:
        while True:
            n = run_once(dry_run=args.dry_run)
            if n:
                print(f"listo: {n} issue(s) procesado(s)")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ndetenido por el usuario")


if __name__ == "__main__":
    main()
