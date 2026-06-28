#!/usr/bin/env bash
# Instala dependencias y pre-commit para empezar a usar flujo.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Setup de flujo ==="

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v py >/dev/null 2>&1; then
    PYTHON_BIN="py"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

echo "Python: $PYTHON_BIN"
"$PYTHON_BIN" -m pip install -r requirements.txt
"$PYTHON_BIN" -m pip install -r requirements-dev.txt
"$PYTHON_BIN" -m pre_commit install

echo ""
echo "Setup completo. Probar con:"
echo "  $PYTHON_BIN -m flujo health"
echo "  $PYTHON_BIN -m pytest tests/ -q"
