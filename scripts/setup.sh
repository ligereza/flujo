#!/usr/bin/env bash
# Instala dependencias y pre-commit para empezar a usar flujo.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Setup de flujo ==="

py -m pip install -r requirements.txt
py -m pip install -r requirements-dev.txt
py -m pre_commit install

echo ""
echo "Setup completo. Probar con:"
echo "  py scripts/flujo.py health"
echo "  py -m pytest tests/ -q"
