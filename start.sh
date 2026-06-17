#!/usr/bin/env bash
# Lanzador rápido para flujo.
set -euo pipefail
cd "$(dirname "$0")"
echo "🚀 Iniciando FLUJO // arte y automatización..."
if command -v py >/dev/null 2>&1; then PY=py
elif command -v python3 >/dev/null 2>&1; then PY=python3
else PY=python
fi
$PY -m flujo app
