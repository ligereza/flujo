from __future__ import annotations
from pathlib import Path
from typing import List, Dict

def extract_palette(image_path: Path, n_colors: int = 5) -> Dict:
    """
    Extrae colores dominantes de una imagen usando Pillow.
    No requiere sklearn / opencv.
    Retorna dict con colors [{hex, rgb, pct}], width, height
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow es requerido (viene con matplotlib). pip install pillow") from e

    im = Image.open(image_path).convert("RGB")
    w, h = im.size

    # Redimensionar para acelerar – mantener aspecto
    max_side = 200
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = im.size

    # Cuantizar a n_colors
    # method=2 = median cut, mejor para fotos
    paletted = im.quantize(colors=n_colors, method=2)
    palette = paletted.getpalette()[: n_colors * 3]

    # Contar frecuencia de cada color indexado
    from collections import Counter
    # getdata() queda obsoleto en Pillow 14; get_flattened_data() es el reemplazo
    try:
        data = list(paletted.get_flattened_data())
    except AttributeError:
        data = list(paletted.getdata())
    counts = Counter(data)
    total = sum(counts.values())

    colors = []
    for idx, count in counts.most_common(n_colors):
        r = palette[idx * 3]
        g = palette[idx * 3 + 1]
        b = palette[idx * 3 + 2]
        hex_c = f"#{r:02x}{g:02x}{b:02x}"
        pct = round(count / total, 4)
        colors.append({"hex": hex_c, "rgb": [r, g, b], "pct": pct})

    return {
        "source_image": str(image_path.name),
        "width": w,
        "height": h,
        "colors": colors,
    }

def save_palette_preview(palette_data: Dict, output_path: Path, width: int = 600, height: int = 120):
    """Genera un PNG con swatches de la paleta"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    colors = palette_data.get("colors", [])
    if not colors:
        return False

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    x = 0
    total_pct = sum(c.get("pct", 0) for c in colors) or 1
    for c in colors:
        pct = c.get("pct", 0) / total_pct
        w = int(width * pct)
        rgb = tuple(c["rgb"])
        draw.rectangle([x, 0, x + w, height], fill=rgb)
        x += w

    # asegurarse que cubre todo el ancho
    if x < width and colors:
        rgb = tuple(colors[-1]["rgb"])
        draw.rectangle([x, 0, width, height], fill=rgb)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return True
