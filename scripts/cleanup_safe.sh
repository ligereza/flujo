#!/usr/bin/env bash
#
# cleanup_safe.sh — Limpieza CONTROLADA y REVERSIBLE de scripts legacy.
#
# Qué hace:
#   - NO borra de verdad: MUEVE los archivos a `_archive/legacy_scripts/<fecha>/`
#     conservando su ruta, así siempre puedes recuperarlos con un `git mv` inverso.
#   - Solo toca una lista blanca de scripts que están VERIFICADOS como
#     NO referenciados por el código (`src/`), los tests, el Makefile,
#     `start.sh`, el README, ni por otros scripts (incluido `scripts/flujo.py`).
#   - Por defecto hace DRY-RUN. Para aplicar de verdad: `--apply`.
#
# Uso:
#   bash scripts/cleanup_safe.sh            # muestra qué movería (dry-run)
#   bash scripts/cleanup_safe.sh --apply    # mueve a _archive/ + git add
#
# Después de --apply, revisa con `git status`, corre los tests y haz tu checkpoint.
#
set -euo pipefail

MODE="${1:-}"

if [ ! -d ".git" ]; then
    echo "ERROR: ejecútalo desde la raíz del repositorio (donde está .git)."
    exit 1
fi

# Lista blanca: scripts legacy verificados como NO referenciados.
# (Generada con: grep por nombre en src/ tests/ Makefile start.sh README.md scripts/ docs/)
LEGACY=(
    "scripts/archive_checkpoints.py"
    "scripts/clean_git_history.sh"
    "scripts/cleanup_legacy_scripts.sh"
    "scripts/flyer_duplicates_report.sh"
    "scripts/flyer_open_latest.sh"
    "scripts/flyer_set_input_demo.sh"
    "scripts/flyer_set_input_latest_demo.sh"
    "scripts/intake_from_email.py"
    "scripts/new_flyer_evento.sh"
    "scripts/orden_status.sh"
)

DEST_BASE="_archive/legacy_scripts/$(date +%Y-%m-%d_%H-%M-%S)"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "      FLUJO — Limpieza segura de scripts legacy"
echo "════════════════════════════════════════════════════════════"
echo ""

FOUND=()
for f in "${LEGACY[@]}"; do
    if [ -f "$f" ]; then
        FOUND+=("$f")
    fi
done

if [ ${#FOUND[@]} -eq 0 ]; then
    echo "Nada que limpiar: ninguno de los scripts legacy existe ya."
    exit 0
fi

echo "Scripts legacy detectados (no referenciados por el código):"
for f in "${FOUND[@]}"; do echo "  · $f"; done
echo ""

if [ "$MODE" != "--apply" ]; then
    echo "DRY-RUN: no se movió nada."
    echo "Se moverían a: $DEST_BASE/"
    echo ""
    echo "Para aplicar:  bash scripts/cleanup_safe.sh --apply"
    exit 0
fi

for f in "${FOUND[@]}"; do
    mkdir -p "$DEST_BASE/$(dirname "$f")"
    git mv "$f" "$DEST_BASE/$f" 2>/dev/null || mv "$f" "$DEST_BASE/$f"
    echo "  [ARCHIVADO] $f -> $DEST_BASE/$f"
done

echo ""
echo "════════════════════════════════════════════════════════════"
echo "Listo. ${#FOUND[@]} scripts movidos a $DEST_BASE/"
echo ""
echo "Próximos pasos:"
echo "  1. git status"
echo "  2. py -m pytest tests/ -q"
echo "  3. flujo health"
echo "  4. Tu checkpoint habitual (commit + push)"
echo ""
echo "Para revertir: git mv los archivos de vuelta, o git checkout -- ."
echo "════════════════════════════════════════════════════════════"
