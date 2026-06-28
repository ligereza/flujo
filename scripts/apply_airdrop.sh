#!/usr/bin/env bash
set -e

MODE="${1:-}"
AIRDROP_DIR="_airdrop"
BACKUP_DIR="_airdrop_backups/$(date +%Y-%m-%d_%H-%M-%S)"

if [ ! -d ".git" ]; then
    echo "ERROR: Este script debe ejecutarse desde la raíz del repositorio."
    exit 1
fi

if [ ! -d "$AIRDROP_DIR" ]; then
    echo "ERROR: No existe la carpeta $AIRDROP_DIR"
    exit 1
fi

if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
    echo ""
    echo "Uso:"
    echo "  bash scripts/apply_airdrop.sh --dry-run"
    echo "  bash scripts/apply_airdrop.sh --apply"
    echo ""
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "           FLUJO — Sistema de Airdrop"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Directorio de airdrop : $AIRDROP_DIR"
echo "Modo                  : $MODE"
echo ""

FILES=$(find "$AIRDROP_DIR" -type f ! -name ".gitkeep" | sort)

if [ -z "$FILES" ]; then
    echo "No hay archivos para aplicar en $AIRDROP_DIR"
    exit 0
fi

echo "Archivos detectados:"
echo "$FILES"
echo ""

if [ "$MODE" = "--dry-run" ]; then
    echo "DRY RUN: No se realizaron cambios."
    echo ""
    echo "Para aplicar los cambios ejecuta:"
    echo "  bash scripts/apply_airdrop.sh --apply"
    exit 0
fi

mkdir -p "$BACKUP_DIR"
echo "Backup de archivos existentes → $BACKUP_DIR"
echo ""

while IFS= read -r SRC; do
    REL="${SRC#$AIRDROP_DIR/}"
    DEST="$REL"

    if [ -f "$DEST" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$DEST")"
        cp "$DEST" "$BACKUP_DIR/$DEST"
        echo "  [BACKUP] $DEST"
    fi

    mkdir -p "$(dirname "$DEST")"
    cp "$SRC" "$DEST"

    if [[ "$DEST" == *.sh ]]; then
        chmod +x "$DEST"
    fi

    echo "  [APLICADO] $DEST"

done <<< "$FILES"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Airdrop aplicado correctamente."
echo "Backup guardado en: $BACKUP_DIR"
echo ""
echo "Próximos pasos recomendados:"
echo "  1. Revisar los cambios con: git status"
echo "  2. Ejecutar pruebas locales"
echo "  3. Hacer checkpoint"
echo "════════════════════════════════════════════════════════════"
