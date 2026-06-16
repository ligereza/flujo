#!/usr/bin/env bash
set -e
MSG="$1"
if [ -z "$MSG" ]; then MSG="avance $(date +%Y-%m-%d_%H-%M)"; fi
mkdir -p checkpoints
DATE=$(date +%Y-%m-%d_%H-%M)
SAFE=$(echo "$MSG" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//')
CP="checkpoints/${DATE}_${SAFE}.md"
cat > "$CP" <<EOF2
# Checkpoint — $MSG

Fecha: $DATE

## Estado

$(cat context/ESTADO.md 2>/dev/null || echo "Sin context/ESTADO.md")

## Cambios realizados

-

## Próximo paso

-
EOF2
git add -A
if git diff --cached --quiet; then echo "No hay cambios"; else git commit -m "checkpoint: $MSG"; fi
if git remote get-url origin >/dev/null 2>&1; then git push -u origin main; fi
