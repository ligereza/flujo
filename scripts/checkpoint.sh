#!/usr/bin/env bash
#
# checkpoint.sh — Crea un checkpoint (commit) y hace push a origin/main.
#
# Robusto frente a pre-commit hooks: si un hook (trailing-whitespace,
# end-of-file-fixer, etc.) modifica archivos y aborta el primer commit,
# este script re-agrega los cambios y reintenta automáticamente.
# Antes había que correrlo DOS veces; ahora basta con UNA.
#
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

# --- Commit robusto frente a pre-commit hooks ---------------------------------
# Un hook puede modificar archivos y hacer fallar el primer 'git commit'.
# Reintentamos hasta 3 veces: re-agregamos lo que el hook tocó y volvemos a commitear.
commit_with_retry() {
    local attempt=1
    local max=3
    while [ "$attempt" -le "$max" ]; do
        git add -A
        if git diff --cached --quiet; then
            echo "No hay cambios"
            return 0
        fi
        # 'set +e' temporal: queremos inspeccionar el código de salida, no abortar.
        set +e
        git commit -m "checkpoint: $MSG"
        local rc=$?
        set -e
        if [ "$rc" -eq 0 ]; then
            return 0
        fi
        echo "⚠ El commit falló (probablemente un pre-commit hook modificó archivos)."
        echo "  Reintento $attempt/$max: re-agregando cambios y volviendo a commitear..."
        attempt=$((attempt + 1))
    done
    echo "✗ No se pudo commitear tras $max intentos. Revisa 'git status' y los hooks."
    return 1
}

commit_with_retry

# --- Push --------------------------------------------------------------------
if git remote get-url origin >/dev/null 2>&1; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    git push -u origin "$BRANCH"
    echo "✓ Push completado a origin/$BRANCH"
else
    echo "(sin remoto 'origin' configurado — no se hizo push)"
fi
