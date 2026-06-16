#!/usr/bin/env bash
# Abre el dashboard HTML en el navegador predeterminado.
set -euo pipefail

cd "$(dirname "$0")/.."

DASHBOARD="context/dashboard.html"

if [ ! -f "$DASHBOARD" ]; then
    echo "No existe $DASHBOARD. Generando..."
    py scripts/flujo_daily.py
fi

if command -v start >/dev/null 2>&1; then
    start "$DASHBOARD"
elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$DASHBOARD"
elif command -v open >/dev/null 2>&1; then
    open "$DASHBOARD"
else
    echo "No se pudo abrir el navegador. Abre manualmente: $DASHBOARD"
fi
