#!/usr/bin/env bash
set -euo pipefail

echo "=================================================="
echo " Limpieza profunda del historial de git"
echo "=================================================="
echo ""
echo "Este script reescribe el historial de git para eliminar archivos binarios grandes."
echo "Requiere:"
echo "  - git-filter-repo instalado"
echo "  - un backup del repo"
echo "  - no tener trabajo no commiteado"
echo "  - avisar a otros colaboradores si los hay"
echo ""

if [ ! -d ".git" ]; then
    echo "ERROR: no estás en la raíz de un repo git."
    exit 1
fi

if ! command -v git-filter-repo >/dev/null 2>&1; then
    echo "ERROR: git-filter-repo no está instalado."
    echo "Instalar con: python3 -m pip install git-filter-repo"
    exit 1
fi

echo "Tamaño actual de .git:"
du -sh .git

echo ""
echo "Blobs más grandes actualmente en el historial:"
git rev-list --objects --all | \
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
    sed -n 's/^blob //p' | sort -rnk2 | head -10

echo ""
echo "Este script eliminará blobs mayores a 1 MB y los archivos:"
echo "  - reference_old/AutomatizadorFlyers.exe"
echo "  - old/flyer_final.jpg"
echo "  - old/Droplet_Flyer.exe"
echo ""
read -rp "¿Tienes un backup y quieres continuar? (escribe 'si' para continuar): " respuesta

if [ "$respuesta" != "si" ]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo "Ejecutando git filter-repo..."

# Eliminar blobs mayores a 1 MB
git filter-repo --strip-blobs-bigger-than 1M --force

# Eliminar paths específicos por si quedaron referencias
git filter-repo \
    --path reference_old/AutomatizadorFlyers.exe \
    --path old/flyer_final.jpg \
    --path old/Droplet_Flyer.exe \
    --path-glob 'scripts/__pycache__/*.pyc' \
    --path-glob 'reference_old/*.exe' \
    --invert-paths --force

echo ""
echo "Tamaño de .git después de la limpieza:"
du -sh .git

echo ""
echo "Blobs más grandes restantes:"
git rev-list --objects --all | \
    git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
    sed -n 's/^blob //p' | sort -rnk2 | head -10

echo ""
echo "Para subir los cambios al remoto, ejecuta:"
echo "  git push --force-with-lease origin main"
echo ""
echo "Recuerda: todos los clones antiguos deben borrarse y clonarse de nuevo."
