#!/usr/bin/env python3
"""
Genera un índice JSON de todos los SVG en /workspace/svg/
para que el SVG Studio Hub pueda catalogarlos y mostrarlos por secciones.
"""
import json
import os
import re
from pathlib import Path
from datetime import datetime

SVG_ROOT = Path("/workspace/svg")
OUTPUT_FILE = Path("/workspace/web/src/data/svg_index.json")

def extract_svg_metadata(svg_path: Path) -> dict | None:
    """Extrae metadata de un archivo SVG."""
    try:
        content = svg_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ⚠ Error leyendo {svg_path}: {e}")
        return None
    
    # Extraer dimensiones del viewBox o width/height
    width, height = None, None
    viewBox_match = re.search(r'viewBox="[\d\s,]+(\d+)[,\s]+(\d+)"', content)
    if viewBox_match:
        width, height = int(viewBox_match.group(1)), int(viewBox_match.group(2))
    else:
        width_match = re.search(r'width="(\d+)', content)
        height_match = re.search(r'height="(\d+)', content)
        if width_match and height_match:
            width, height = int(width_match.group(1)), int(height_match.group(1))
    
    # Extraer colores únicos (excluyendo blanco/negro puros)
    colors = set()
    for color in re.findall(r'#([0-9a-fA-F]{3,8})', content):
        if len(color) == 3:
            color = ''.join(c*2 for c in color)
        color_lower = color.lower()
        if color_lower not in ['000000', 'ffffff', 'fff', '000']:
            colors.add(f"#{color_lower}")
    
    # Determinar tipo de pieza basado en nombre y ruta
    name_lower = svg_path.name.lower()
    path_lower = str(svg_path).lower()
    
    piece_type = 'flyer'
    if 'etiqueta' in name_lower or 'label' in name_lower:
        piece_type = 'etiqueta'
    elif 'pendon' in name_lower or 'pendón' in name_lower:
        piece_type = 'pendon'
    elif 'post' in name_lower and ('ig' in name_lower or 'instagram' in name_lower):
        piece_type = 'post-ig'
    elif 'sticker' in name_lower:
        piece_type = 'sticker'
    elif 'logo' in name_lower:
        piece_type = 'logo'
    elif 'rider' in name_lower:
        piece_type = 'rider'
    elif 'cartelera' in name_lower:
        piece_type = 'cartelera'
    
    # Determinar área basada en ruta
    area = 'comun'
    if 'suplementos' in path_lower or 'supl' in path_lower:
        area = 'suplementos'
    elif 'evento' in path_lower or 'event' in path_lower:
        area = 'eventos'
    
    # Determinar medio (impresión vs digital)
    medio = 'digital'
    if 'print' in path_lower or 'impres' in path_lower or piece_type in ['etiqueta', 'flyer', 'pendon']:
        medio = 'impresion'
    
    # Extraer nombre del producto desde el nombre del archivo
    product = None
    name_clean = svg_path.stem.replace('_editable', '').replace('_vectorizado', '').replace('_', ' ').title()
    if 'suplementos_rd' in path_lower:
        product = 'Línea Suplementos RD'
        if 'impulso' in name_lower:
            product = 'Impulso'
        elif 'hongos' in name_lower:
            product = 'Hongos Adaptógenos'
        elif 'pre_fiesta' in name_lower:
            product = 'Pre Fiesta'
        elif 'magnesio' in name_lower:
            product = 'Magnesio'
        elif 'creatina' in name_lower:
            product = 'Creatina Monohidratada'
        elif 'proteina' in name_lower:
            product = 'Proteína'
        elif 'post_fiesta' in name_lower:
            product = 'Post Fiesta'
    
    # Determinar estado basado en si es editable o vectorizado
    status = 'borrador'
    if 'vectorizado' in name_lower or 'final' in name_lower:
        status = 'aprobado'
    elif 'editable' in name_lower:
        status = 'en-revision'
    
    # Extraer secciones/grupos del SVG
    sections = []
    for group_match in re.finditer(r'<g[^>]*id=["\']([^"\']+)["\'][^>]*>', content):
        group_id = group_match.group(1)
        if group_id and not group_id.startswith('_'):
            sections.append(group_id)
    
    # Tamaño real en cm (aproximado a 300 DPI)
    real_size_cm = "desconocido"
    if width and height:
        width_cm = round(width / 118.11, 1)  # 300 DPI ≈ 118.11 px/cm
        height_cm = round(height / 118.11, 1)
        real_size_cm = f"{width_cm} × {height_cm} cm"
    
    return {
        "id": svg_path.stem.replace('_editable', '').replace('_vectorizado', ''),
        "name": name_clean,
        "type": piece_type,
        "area": area,
        "medio": medio,
        "herramienta": "SVG+Illustrator",
        "product": product,
        "realSizeCm": real_size_cm,
        "canvasPx": f"{width} × {height}" if width and height else "desconocido",
        "colors": sorted(list(colors))[:12],
        "lastModified": datetime.fromtimestamp(svg_path.stat().st_mtime).strftime('%Y-%m-%d'),
        "status": status,
        "filePath": str(svg_path.relative_to(Path("/workspace"))),
        "sections": sections,
        "dimensions": {"width": width, "height": height} if width and height else None
    }

def main():
    print("🔍 Escaneando SVG en /workspace/svg/...")
    
    pieces = []
    svg_files = list(SVG_ROOT.rglob("*.svg"))
    
    for svg_path in svg_files:
        # Ignorar archivos de ejemplo o backup
        if '.bak' in svg_path.name or svg_path.name.startswith('_'):
            continue
            
        metadata = extract_svg_metadata(svg_path)
        if metadata:
            pieces.append(metadata)
            print(f"  ✓ {metadata['name']} ({metadata['type']}, {metadata['area']})")
    
    # Ordenar por área, luego tipo, luego nombre
    pieces.sort(key=lambda p: (p['area'], p['type'], p['name']))
    
    # Guardar índice JSON
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(pieces, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Índice generado: {OUTPUT_FILE}")
    print(f"   Total: {len(pieces)} piezas SVG")
    
    # Resumen por área
    areas = {}
    for p in pieces:
        areas[p['area']] = areas.get(p['area'], 0) + 1
    print("\n📊 Por área:")
    for area, count in sorted(areas.items()):
        print(f"   • {area}: {count} piezas")

if __name__ == '__main__':
    main()
