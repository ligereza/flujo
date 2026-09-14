"""Create/update GitHub labels needed by flujo.

Windows/Git Bash usage:

    set GITHUB_TOKEN=github_pat_...
    py scripts/github_setup_labels.py --repo ligereza/vibecodeine

Git Bash alternative:

    export GITHUB_TOKEN=github_pat_...
    py scripts/github_setup_labels.py --repo ligereza/vibecodeine

No token is stored in the repo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


LABELS = [
    # Core
    ("pedido", "6d28d9", "Request or design task"),
    ("cambio", "a855f7", "Change or correction request"),
    ("cotizacion", "f59e0b", "Quote or commercial estimate"),
    ("bloqueado", "dc2626", "Blocked; needs information or decision"),
    # Areas
    ("area/eventos", "2563eb", "Events area"),
    ("area/suplementos", "7c3aed", "Supplements / RD commercial area"),
    # State
    ("estado/por-revisar", "facc15", "New request waiting for review"),
    ("estado/pendiente-datos", "fb923c", "Waiting for missing data"),
    ("estado/listo", "22c55e", "Ready to work"),
    ("estado/en-diseno", "0ea5e9", "In design"),
    ("estado/revision", "a855f7", "In review"),
    ("estado/entregado", "16a34a", "Delivered"),
    # Source/actions
    ("gmail", "64748b", "Created from Gmail"),
    ("instagram", "e879f9", "Contains Instagram link"),
    ("action/descargar-ig", "ec4899", "Download Instagram media"),
    ("action/crear-job", "14b8a6", "Create flujo job"),
    ("action/cotizar", "f97316", "Prepare quote"),
    # Priority
    ("prioridad/alta", "ef4444", "High priority"),
    ("prioridad/media", "f59e0b", "Medium priority"),
    ("prioridad/baja", "84cc16", "Low priority"),
]


def request_json(method: str, url: str, token: str, payload: dict | None = None) -> tuple[int, str]:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "flujo-label-setup",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update flujo GitHub labels")
    parser.add_argument("--repo", required=True, help="owner/repo, example: ligereza/vibecodeine")
    parser.add_argument("--token-env", default="GITHUB_TOKEN", help="env var containing GitHub token")
    args = parser.parse_args()

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        print(f"ERROR: missing token env var {args.token_env}", file=sys.stderr)
        print("Git Bash: export GITHUB_TOKEN=github_pat_...", file=sys.stderr)
        print("PowerShell: $env:GITHUB_TOKEN='github_pat_...'", file=sys.stderr)
        return 2

    base = f"https://api.github.com/repos/{args.repo}/labels"
    ok = True
    for name, color, description in LABELS:
        encoded = urllib.parse.quote(name, safe="")
        payload = {"name": name, "color": color, "description": description}

        status, body = request_json("PATCH", f"{base}/{encoded}", token, payload)
        if status in (200, 201):
            print(f"updated: {name}")
            continue
        if status == 404:
            status2, body2 = request_json("POST", base, token, payload)
            if status2 in (200, 201):
                print(f"created: {name}")
                continue
            print(f"ERROR create {name}: HTTP {status2} {body2}", file=sys.stderr)
            ok = False
            continue
        print(f"ERROR update {name}: HTTP {status} {body}", file=sys.stderr)
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
