# Análisis automático de flyers

`flujo analyze` extrae información visual de los flyers descargados de Instagram, sin abrir Photoshop.

## Qué hace

1. **Colores dominantes**
   - Lee `input/input_ig.jpg`
   - Extrae 5-6 colores principales con Pillow (median cut)
   - Guarda `analysis/palette.json`
   - Genera `analysis/palette.png` – preview visual de swatches
   - Sin dependencias pesadas (solo Pillow, que ya viene con matplotlib)

2. **OCR (opcional)**
   - Si `pytesseract` está instalado, extrae texto del flyer
   - Guarda `analysis/ocr.txt`
   - Extrae hints: fechas, horas, @menciones, #hashtags
   - Guarda `analysis/ocr_hints.json`
   - Si NO está instalado: guarda `analysis/ocr_status.json` con instrucciones, no falla

## Uso

```bash
# analizar último flyer
flujo analyze
# o
py scripts/flyer_analyze.py

# analizar un proyecto específico
flujo analyze projects/flyer_eventos/2026-06-16_ig_ABC123

# analizar todos
flujo analyze --all
```

## Salidas

```
projects/flyer_eventos/YYYY-MM-DD_ig_XXXX/
└─ analysis/
   ├─ palette.json       # colores hex + rgb + porcentaje
   ├─ palette.png        # preview visual 600x120
   ├─ ocr.txt            # texto extraído (si pytesseract disponible)
   └─ ocr_hints.json     # fechas/horas/menciones detectadas
```

`manifest.json` se actualiza con:
```json
"analysis": {
  "analyzed_at": "2026-06-16T22:30:00",
  "palette_colors": ["#e63946", "#f1faee", "#a8dadc", "#457b9d", "#1d3557"],
  "ocr_ran": false
},
"steps": { "analysis": "done" }
```

## Instalar OCR (opcional)

Windows:
```
py -m pip install pytesseract
# descargar tesseract installer: https://github.com/UB-Mannheim/tesseract/wiki
# agregar C:\Program Files\Tesseract-OCR a PATH
```

Linux:
```
pip install pytesseract
sudo apt install tesseract-ocr tesseract-ocr-spa
```

macOS:
```
pip install pytesseract
brew install tesseract
```

Sin OCR instalado, el análisis de colores funciona igual. Solo se omite el paso OCR.

## API Python

```python
from flujo.analyze.run import analyze_project
from pathlib import Path

result = analyze_project(Path("projects/flyer_eventos/2026-06-16_ig_ABC"))
print(result["palette"]["colors"])
```

## Próximo

- Clustering de colores LAB (más preciso perceptualmente)
- Detección de texto con EasyOCR / PaddleOCR (sin tesseract externo)
- Extracción de layout: bounding boxes de texto
- Export palette a .aco (Photoshop), .ase (Illustrator)
