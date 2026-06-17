#!/usr/bin/env bash
# Lanzador rápido para flujo.
set -euo pipefail

# Ubicarse en la raíz del proyecto
cd "$(dirname "$0")"

echo "🚀 Iniciando FLUJO // Dimensiones del Orden..."

# Detectar python
if command -v py >/dev/null 2>&1; then
  PY=py
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

$PY scripts/app.py
