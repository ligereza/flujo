#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
  echo "Uso: bash scripts/cleanup_demo_artifacts.sh [--dry-run|--apply]"
  exit 2
fi

mapfile -t JOB_TARGETS < <(
  find jobs -maxdepth 1 -type d \
    \( -name '20*_etiquetas-acme*' \
       -o -name '20*_etiquetas-acme-test' \
       -o -name '20*_test-pipeline' \
       -o -name '20*_uno' \
       -o -name '20*_dos' \) \
    | sort
)

mapfile -t PROJECT_TARGETS < <(
  find projects/piezas_vectoriales -maxdepth 1 -type d \
    \( -name '20*-etiquetas-acme*' \
       -o -name 'pieza-x' \
       -o -name 'etiqueta-acme' \) \
    | sort
)

TARGETS=("${JOB_TARGETS[@]}" "${PROJECT_TARGETS[@]}")

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No hay artefactos demo/test para limpiar."
  exit 0
fi

echo "Artefactos demo/test detectados (${#TARGETS[@]}):"
printf '  %s\n' "${TARGETS[@]}"

if [[ "$MODE" == "--dry-run" ]]; then
  echo
  echo "Dry-run solamente. Para borrar: bash scripts/cleanup_demo_artifacts.sh --apply"
  exit 0
fi

echo
printf 'Eliminando artefactos...\n'

# Borra del índice si estaban trackeados. Las rutas ignoradas/no trackeadas se borran con rm -rf abajo.
git rm -r --ignore-unmatch -- "${TARGETS[@]}" >/dev/null || true
rm -rf -- "${TARGETS[@]}"

# Limpieza local segura asociada al ciclo de airdrops/tests.
rm -rf _airdrop_backups *airdrop*backups .pytest_cache
find . -type d -name "__pycache__" -prune -exec rm -rf {} +

echo "OK: limpieza aplicada. Revisa con: git status --short"
