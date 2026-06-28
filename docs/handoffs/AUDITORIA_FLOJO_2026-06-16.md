# Auditoría de flujo — 2026-06-16

Resumen ejecutivo con problemas detectados, prioridad y plan de acción.

## 1. Tamaño e historial de git (crítico, requiere decisión)

- Repo: **46 MB** en disco.
- `.git` solo: **43 MB**.
- Working tree actual: ~3 MB.
- El historial contiene archivos binarios grandes que ya no están en el working tree:
  - `reference_old/AutomatizadorFlyers.exe` — 37.7 MB
  - `old/flyer_final.jpg` — 7.7 MB
  - `old/Droplet_Flyer.exe` — 348 KB
  - Varios `__pycache__/*.pyc` — 14 KB / 10 KB
- Impacto: cada `git clone` descarga 43 MB de basura. Backups y CI son más lentos.
- Solución: limpiar historial con `git filter-repo` o BFG. Esto **reescribe el historial** y requiere `git push --force` en `main`. **No se hace automáticamente sin confirmación explícita.**

## 2. Archivos binarios trackeados actualmente (medio)

- `projects/flyer_eventos/2026-06-12_evento-prueba/input/input_ig.jpg` — 289 KB.
- Está trackeada aunque el espíritu del repo dice "no subir archivos pesados".
- Solución: moverla a un `_local/` o quitarla de git y agregar reglas de `.gitignore` para inputs de imágenes/video.

## 3. Documentación duplicada e inconsistente (medio)

- `README.md`, `AGENTS.md` y `PARA_IA.md` repiten comandos y listas.
- Algunos lugares dicen `py`, otros `python3`, otros `bash`.
- `context/ESTADO.md` dice "última actualización: 2026-06-12" pero hay commits hasta 2026-06-15.
- Solución: centralizar una fuente de verdad y unificar lenguaje de comandos.

## 4. Dependencias no documentadas (medio)

- `tools/piezas_vectoriales/scripts/generar_desde_json.py` usa `matplotlib`.
- El CI lo instala, pero el README no dice que se necesita.
- No hay `requirements.txt` raíz.
- Solución: crear `requirements.txt` y documentar en README.

## 5. Portabilidad de fuentes (medio)

- El generador de SVG usa ruta hardcoded:
  ```python
  FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
  FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
  ```
  Esto solo funciona en Linux con DejaVu instalada. En Windows/macOS falla.
- Solución: detectar fuentes del sistema o empaquetar una fuente propia.

## 6. Rutas relativas al CWD en scripts (medio)

- Varios scripts hacen `Path('jobs/_template')` o `Path('projects/...')`. Si ejecutas el script desde otro directorio, falla.
- Solución: usar `Path(__file__).resolve().parents[1]` para anclar a la raíz del repo.

## 7. Código duplicado (medio-bajo)

- `new_flyer_evento.sh` y `flyer_from_email.py` crean manifest casi idéntico.
- `flujo.py` es un wrapper manual que puede reemplazarse por un CLI más robusto.
- Solución: extraer una función `create_flyer_project()` reutilizable.

## 8. Falta de tests (medio)

- No hay test suite.
- `flujo_health.py` es un buen primer paso, pero no valida la lógica de los scripts.
- Solución: agregar `tests/` con pytest y un smoke test mínimo.

## 9. Carpeta `reference_old` (medio)

- Es un respaldo de código antiguo. Ocupa espacio visual y confunde.
- Tiene archivos `.exe`, `.pyw`, `.bat`.
- Solución: moverla a un repo aparte o a un release/attachment, o mantener solo un archivo `.md` con el contexto.

## 10. Carpeta `checkpoints` (bajo)

- 58 archivos de checkpoints automáticos. Son ruido para un visitante externo.
- Solución: conservar el script `checkpoint.sh`, pero quizás mover los archivos generados a una rama `log` o un wiki, o al menos marcarlos en `.gitattributes` como `linguist-documentation`.

## 11. Proyecto `tapiz` (bajo)

- Tiene `vibecode.egg-info/` y `__pycache__` trackeados (o al menos presentes).
- Parece un experimento aparte.
- Solución: limpiar o mover a submódulo/repo propio.

## 12. Proyectos de ejemplo generados (bajo)

- `projects/piezas_vectoriales/etiquetas_ejemplo/salida_generada/` está en `.gitignore`, pero el directorio aún aparece en working tree si se generó localmente.
- El CI los regenera, así que no deberían estar en git.

## Plan de acción propuesto (fase 1: seguro, no reescribe historial)

1. Crear `requirements.txt` raíz.
2. Unificar README / AGENTS / PARA_IA / context/ESTADO.
3. Mejorar `.gitignore` para inputs pesados y `egg-info`.
4. Hacer portátil la detección de fuentes en `generar_desde_json.py`.
5. Anclar rutas de scripts a la raíz del repo.
6. Extraer función común para crear proyectos flyer.
7. Agregar `tests/test_smoke.py` mínimo.
8. Agregar `Makefile` o `justfile` para comandos frecuentes.
9. Hacer un health check más completo.
10. Documentar el plan de limpieza profunda del historial en un archivo aparte.

## Plan de acción propuesto (fase 2: requiere decisión del usuario)

- Limpiar historial de git con `git filter-repo`.
- Eliminar/relajar `reference_old` y `checkpoints` antiguos.
- Mover `projects/tapiz` a repo aparte.
- Configurar pre-commit hooks.
