#!/usr/bin/env bash
set -e

MODE="$1"
AIRDROP="_airdrop"
BACKUP="_airdrop_backups/$(date +%Y-%m-%d_%H-%M-%S)"

if [ ! -d ".git" ]; then
  echo "ERROR: ejecuta esto desde la raíz del repo."
  exit 1
fi

if [ ! -d "$AIRDROP" ]; then
  echo "ERROR: no existe carpeta $AIRDROP"
  exit 1
fi

if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--apply" ]; then
  echo "Uso:"
  echo "  bash scripts/apply_airdrop.sh --dry-run"
  echo "  bash scripts/apply_airdrop.sh --apply"
  exit 1
fi

echo ""
echo "AIRDROP: $AIRDROP"
echo "MODO: $MODE"
echo ""

FILES=$(find "$AIRDROP" -type f | sort)

if [ -z "$FILES" ]; then
  echo "No hay archivos en $AIRDROP"
  exit 0
fi

echo "Archivos detectados:"
echo "$FILES"
echo ""

if [ "$MODE" = "--dry-run" ]; then
  echo "DRY RUN: no se copió nada."
  echo ""
  echo "Para aplicar:"
  echo "bash scripts/apply_airdrop.sh --apply"
  exit 0
fi

mkdir -p "$BACKUP"

echo "Aplicando archivos..."
echo ""

while IFS= read -r SRC; do
  REL="${SRC#$AIRDROP/}"
  DEST="$REL"

  mkdir -p "$(dirname "$DEST")"

  if [ -f "$DEST" ]; then
    mkdir -p "$BACKUP/$(dirname "$DEST")"
    cp "$DEST" "$BACKUP/$DEST"
    echo "Backup: $DEST -> $BACKUP/$DEST"
  fi

  cp "$SRC" "$DEST"
  echo "Copiado: $SRC -> $DEST"

  case "$DEST" in
    *.sh)
      chmod +x "$DEST"
      echo "chmod +x: $DEST"
      ;;
  esac

done <<< "$FILES"

echo ""
echo "Listo."
echo "Backup en: $BACKUP"
echo ""
echo "Revisa cambios con:"
echo "git status"
echo ""
echo "Luego guarda:"
echo "bash scripts/checkpoint.sh \"aplicar airdrop\""
