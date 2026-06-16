#!/usr/bin/env bash
# Flujo simplificado: correo -> job -> dashboard.
# Uso: bash scripts/nuevo_pedido.sh "nombre pedido" inbox/correo.txt
set -euo pipefail

cd "$(dirname "$0")/.."

NAME="${1:-}"
EMAIL="${2:-}"

if [ -z "$NAME" ] || [ -z "$EMAIL" ]; then
    echo "Uso: bash scripts/nuevo_pedido.sh \"nombre pedido\" inbox/correo.txt"
    exit 1
fi

if [ ! -f "$EMAIL" ]; then
    echo "ERROR: no existe archivo: $EMAIL"
    exit 1
fi

echo "=== Nuevo pedido: $NAME ==="

# 1. Crear job y preparar
py scripts/flujo_pipeline.py "$NAME" "$EMAIL" --confirm

# 2. Generar dashboard
py scripts/flujo_daily.py

# 3. Abrir dashboard
bash scripts/abrir_dashboard.sh

echo ""
echo "Pedido procesado. Revisar context/PIPELINE_RESULT.md y context/dashboard.html"
