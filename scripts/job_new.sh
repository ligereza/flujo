#!/usr/bin/env bash
set -e

NAME="$1"
if [ -z "$NAME" ]; then
  echo "Uso: bash scripts/job_new.sh \"nombre pedido\""
  exit 1
fi

SLUG=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')
DATE=$(date +%Y-%m-%d)
DIR="jobs/${DATE}_${SLUG}"

if [ -e "$DIR" ]; then
  echo "ERROR: ya existe $DIR"
  exit 1
fi

mkdir -p "$DIR"
cp jobs/_template/* "$DIR/"
sed -i.bak "s/YYYY-MM-DD_nombre_pedido/${DATE}_${SLUG}/" "$DIR/brief.yaml" || true
rm -f "$DIR/brief.yaml.bak"

echo "Job creado: $DIR"
echo "Siguiente: pega el correo en $DIR/pedido_original.txt"
