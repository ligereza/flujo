# Plan de limpieza profunda del historial de git

## Problema

El repositorio pesa **46 MB** en disco, de los cuales **43 MB son `.git`**.
El árbol de trabajo actual solo pesa ~3 MB.

El historial contiene archivos binarios grandes que ya no están en el working tree:

| Archivo en historial | Tamaño |
|----------------------|--------|
| `reference_old/AutomatizadorFlyers.exe` | 37.7 MB |
| `old/flyer_final.jpg` | 7.7 MB |
| `old/Droplet_Flyer.exe` | 348 KB |
| `scripts/__pycache__/*.pyc` | ~25 KB |

Cada `git clone` descarga toda esa basura.

## Solución

Limpiar el historial con `git filter-repo` (recomendado) o `BFG Repo-Cleaner`. Esto reescribe los commits que tocaban esos archivos.

## Requisitos

- Tener un backup del repo completo (o estar seguro de que GitHub/GitLab tiene el remoto).
- No tener trabajo no commiteado en otras máquinas.
- Avisar si otras personas colaboran en este repo.

## Pasos con `git filter-repo`

### 1. Instalar git-filter-repo

```bash
python3 -m pip install git-filter-repo
```

### 2. Hacer un backup local

```bash
cd ..
cp -R flujo flujo-backup-antes-limpieza
```

### 3. Ejecutar el filtro

```bash
cd flujo
git filter-repo --strip-blobs-bigger-than 1M --force
```

Esto eliminará blobs mayores a 1 MB del historial completo.

Si quieres ser más selectivo:

```bash
git filter-repo --path reference_old/AutomatizadorFlyers.exe --path old/flyer_final.jpg --path old/Droplet_Flyer.exe --path-glob 'scripts/__pycache__/*.pyc' --invert-paths --force
```

### 4. Revisar el tamaño

```bash
du -sh .git
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sed -n 's/^blob //p' | sort -rnk2 | head -20
```

El `.git` debería bajar de ~43 MB a ~3–5 MB.

### 5. Forzar push

```bash
git push --force-with-lease origin main
```

## Precauciones

- **Reescribe el historial**: todos los clones existentes deben borrarse y clonarse de nuevo.
- **No mezclar**: no hacer `git pull` normal desde un clone antiguo; generaría commits duplicados.
- **GitHub Actions / releases**: si hay releases adjuntos, revisar que no dependan de esos blobs.
- **Checkpoints**: movidos a `.archive/checkpoints/`. Los archivos quedan como bitácora histórica.

## Alternativa más conservadora

Si no quieres reescribir el historial, puedes:

1. Dejar el historial como está.
2. Borrar `reference_old` del working tree.
3. Seguir usando `.gitignore` correctamente.
4. El `.git` seguirá pesando, pero el repo no crecerá más.

## Recomendación

Hacer la limpieza profunda ahora, antes de que el repo crezca. Es el momento ideal porque todavía es un repo personal y no hay colaboradores activos.
