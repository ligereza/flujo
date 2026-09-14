#!/usr/bin/env python3
"""Crea un proyecto base de piezas_vectoriales desde un jobs/.../brief.yaml.

No diseña automáticamente: crea una base editable para continuar.
"""
from pathlib import Path
import re
import shutil
import sys
import json


def slugify(s):
    s = (s or 'proyecto').lower()
    s = re.sub(r'[^a-z0-9áéíóúñ]+', '-', s)
    s = (s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n'))
    s = re.sub(r'-+', '-', s).strip('-')
    return s or 'proyecto'


def simple_yaml_value(lines, key):
    pat = re.compile(rf'^{re.escape(key)}:\s*(.*)$')
    for line in lines:
        m = pat.match(line)
        if m:
            return m.group(1).strip().strip('"')
    return ''


def nested_value(lines, section, key):
    inside = False
    pat = re.compile(rf'^\s{{2}}{re.escape(key)}:\s*(.*)$')
    for line in lines:
        if re.match(rf'^{re.escape(section)}:\s*$', line):
            inside = True
            continue
        if inside and line and not line.startswith(' '):
            inside = False
        if inside:
            m = pat.match(line)
            if m:
                return m.group(1).strip().strip('"')
    return ''



def yaml_list_values(lines, section):
    vals=[]; inside=False
    for line in lines:
        if re.match(rf'^{re.escape(section)}:\s*$', line):
            inside=True; continue
        if inside and line and not line.startswith(' '):
            inside=False
        if inside:
            m=re.match(r'^\s*-\s*(.*)$', line)
            if m:
                vals.append(m.group(1).strip().strip('"'))
    return vals

def to_num(v, default):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return default


def choose_template(ancho, alto, tipo='', explicit='', size_was_default=False):
    if explicit:
        ep = Path(explicit)
        return ep if ep.exists() else Path('tools/piezas_vectoriales/plantillas') / explicit
    idx = Path('tools/piezas_vectoriales/plantillas/INDEX_FORMATOS.json')
    if not idx.exists():
        return None
    formatos = json.loads(idx.read_text(encoding='utf-8')).get('formatos', [])
    if not formatos:
        return None
    hint = (tipo or '').lower()

    # Si no había medida real en el brief, priorizar intención/formato antes que tamaño default.
    if size_was_default and hint:
        for wanted in ['one_page', 'one-page', 'dossier', 'propuesta', 'carrusel', 'etiqueta', 'flyer']:
            if wanted in hint:
                candidates = [f for f in formatos if wanted.replace('-', '_') in f.get('id','').lower() or wanted in f.get('tipo','').lower()]
                if candidates:
                    return Path(candidates[0]['template'])

    if not ancho or not alto:
        return None
    def sc(f):
        s=f.get('real_size_cm', {})
        fw, fh = float(s.get('width', 0)), float(s.get('height', 1))
        ratio_diff = abs((fw/fh) - (ancho/alto))
        size_diff = abs(fw-ancho)+abs(fh-alto)
        type_bonus = 0 if not hint or any(tok in f.get('tipo','').lower() or tok in f.get('id','').lower() for tok in hint.split()) else 10
        return ratio_diff*10 + size_diff + type_bonus
    best = sorted(formatos, key=sc)[0]
    return Path(best['template']) if sc(best) < 3.0 else None


def apply_template(template_path, out_dir, title, cliente, project_slug, job_dir, ancho, alto):
    cfg = json.loads(Path(template_path).read_text(encoding='utf-8'))
    cfg.setdefault('project', {})
    cfg['project']['name'] = title
    cfg['project']['slug'] = project_slug
    cfg['project']['brand'] = cliente
    cfg['project']['source_job'] = job_dir.as_posix()
    cfg['project']['note'] = 'Proyecto base creado desde brief.yaml usando plantilla.'
    if cfg.get('documents'):
        cfg['documents'][0]['id'] = f'01_base_{project_slug}'
        cfg['documents'][0]['title'] = title
        # reemplazo suave de primer texto grande si existe
        for el in cfg['documents'][0].get('elements', []):
            if el.get('type') == 'text' and str(el.get('content','')).upper() in ['NOMBRE PRODUCTO', 'TÍTULO PRINCIPAL']:
                el['content'] = title
                break
    (out_dir / 'config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/brief_to_project.py jobs/YYYY-MM-DD_nombre/brief.yaml [nombre_proyecto] [template_opcional]')
        sys.exit(1)
    brief = Path(sys.argv[1])
    if not brief.exists():
        print(f'No existe brief: {brief}')
        sys.exit(1)
    lines = brief.read_text(encoding='utf-8').splitlines()
    job_dir = brief.parent
    project_name = sys.argv[2] if len(sys.argv) > 2 else simple_yaml_value(lines, 'proyecto') or job_dir.name
    explicit_template = sys.argv[3] if len(sys.argv) > 3 else ''
    project_slug = slugify(project_name)
    out_dir = Path('projects/piezas_vectoriales') / project_slug
    if out_dir.exists():
        print(f'ERROR: ya existe {out_dir}')
        sys.exit(1)

    raw_ancho = nested_value(lines, 'medidas', 'ancho_cm')
    raw_alto = nested_value(lines, 'medidas', 'alto_cm')
    size_was_default = not raw_ancho or not raw_alto
    ancho = to_num(raw_ancho, 10)
    alto = to_num(raw_alto, 14)
    w = int(round(ancho * 200))
    h = int(round(alto * 200))
    if w <= 0 or h <= 0:
        w, h = 2000, 2800
        ancho, alto = 10, 14

    title = simple_yaml_value(lines, 'proyecto') or project_name
    cliente = simple_yaml_value(lines, 'cliente') or 'Cliente'
    tipo = simple_yaml_value(lines, 'tipo_pieza') or 'pieza'
    posibles = ' '.join(yaml_list_values(lines, 'posibles_formatos'))
    tipo_hint = (tipo + ' ' + posibles).strip()

    out_dir.mkdir(parents=True)
    template = choose_template(ancho, alto, tipo_hint, explicit_template, size_was_default)
    if template and template.exists():
        apply_template(template, out_dir, title, cliente, project_slug, job_dir, ancho, alto)
        print(f'Plantilla usada: {template}')
    else:
        config = f'''{{
  "project": {{
    "name": "{title}",
    "slug": "{project_slug}",
    "brand": "{cliente}",
    "website": "",
    "source_job": "{job_dir.as_posix()}",
    "note": "Proyecto base creado desde brief.yaml. Diseño pendiente de ajustar."
  }},
  "canvas": {{
    "width": {w},
    "height": {h},
    "real_size_cm": {{ "width": {ancho:g}, "height": {alto:g} }},
    "safe_margin_px": 120
  }},
  "palette": {{
    "cream": "#F6EFE3",
    "paper": "#FFF8ED",
    "white": "#FFFFFF",
    "ink": "#161513",
    "muted": "#675F55",
    "line": "#D9CEC0",
    "accent": "#173F2F"
  }},
  "background": "cream",
  "global_elements": [
    {{ "type": "rect", "x": 80, "y": 80, "w": {max(w-160,100)}, "h": {max(h-160,100)}, "radius": 60, "fill": "none", "stroke": "line", "stroke_width": 5 }},
    {{ "type": "text", "content": "{{brand}}", "x": 120, "y": 120, "size": 44, "fill": "ink", "weight": "bold" }}
  ],
  "documents": [
    {{
      "id": "01_base_{project_slug}",
      "title": "{title}",
      "tipo": "{tipo}",
      "elements": [
        {{ "type": "text", "content": "{title}", "x": 120, "y": 300, "size": 96, "fill": "ink", "weight": "bold", "max_width": {max(w-240,500)} }},
        {{ "type": "panel", "x": 120, "y": 520, "w": {max(w-240,500)}, "h": {max(h-760,400)}, "radius": 44, "fill": "white", "stroke": "line", "stroke_width": 3, "opacity": 0.72 }},
        {{ "type": "paragraph", "content": "Base creada desde brief. Reemplazar por estructura final de diseño.", "x": 190, "y": 610, "size": 44, "fill": "muted", "max_width": {max(w-380,400)}, "line_height": 60 }}
      ]
    }}
  ]
}}
'''
        (out_dir / 'config.json').write_text(config, encoding='utf-8')
    shutil.copy2(brief, out_dir / 'brief_fuente.yaml')
    pedido = job_dir / 'pedido_original.txt'
    if pedido.exists():
        shutil.copy2(pedido, out_dir / 'pedido_original.txt')
    print(f'Proyecto base creado: {out_dir}')
    print(f'Generar con: py scripts/piezas_generar.py "{out_dir / "config.json"}"')


if __name__ == '__main__':
    main()
