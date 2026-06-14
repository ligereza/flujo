#!/usr/bin/env python3
"""Extrae un brief.yaml inicial desde jobs/<job>/pedido_original.txt.

No busca ser perfecto: acelera el primer ordenamiento para que una IA/humano revise.
"""
from pathlib import Path
import re
import sys
from datetime import date

PRODUCT_HINTS = [
    'impulso', 'magnesio', 'creatina', 'proteína', 'proteina', 'pre fiesta',
    'post fiesta', 'hongos adaptógenos', 'hongos adaptogenos', 'whey', 'iso protein'
]


def q(s):
    if s is None or s == '':
        return ''
    s = str(s).replace('"', '\\"')
    return f'"{s}"'


def find_measure(text):
    # 14x10 cm, 14 x 10cm, 10×7 cm
    m = re.search(r'(\d+(?:[\.,]\d+)?)\s*[x×]\s*(\d+(?:[\.,]\d+)?)\s*(cm|mm)?', text, re.I)
    if not m:
        return None, None, None
    a = float(m.group(1).replace(',', '.'))
    b = float(m.group(2).replace(',', '.'))
    unit = (m.group(3) or 'cm').lower()
    if unit == 'mm':
        a, b = a / 10, b / 10
    return a, b, 'horizontal' if a >= b else 'vertical'


def detect_delivery(text):
    low = text.lower()
    return {
        'editable_svg': any(x in low for x in ['editable', 'svg editable', 'illustrator', '.ai', 'ai ']),
        'vectorizado_svg': any(x in low for x in ['vector', 'vectorizado', 'curvas', 'contornos', 'trazados']),
        'pdf_impresion': 'pdf' in low,
        'zip': 'zip' in low or 'comprimido' in low,
        'otro': ''
    }


def detect_type(text):
    low = text.lower()
    for key in ['etiqueta', 'flyer', 'sticker', 'tarjeta', 'afiche', 'catalogo', 'catálogo']:
        if key in low:
            return key
    return ''


def detect_products(text):
    low = text.lower()
    found = []
    for p in PRODUCT_HINTS:
        if p in low:
            label = p.title().replace('Proteina', 'Proteína')
            if label not in found:
                found.append(label)
    return found


def detect_bleed(text):
    low = text.lower()
    m = re.search(r'sangrado\D{0,10}(\d+(?:[\.,]\d+)?)\s*mm', low)
    if m:
        return float(m.group(1).replace(',', '.'))
    if 'sangrado' in low:
        return ''
    return ''


def main():
    if len(sys.argv) < 2:
        print('Uso: py scripts/job_extract_brief.py jobs/YYYY-MM-DD_nombre')
        sys.exit(1)
    job = Path(sys.argv[1])
    pedido_original = job / 'pedido_original.txt'
    pedido_sanitizado = job / 'pedido_sanitizado.txt'
    pedido = pedido_sanitizado if pedido_sanitizado.exists() else pedido_original
    brief = job / 'brief.yaml'
    estado = job / 'estado.md'
    if not pedido.exists():
        print(f'No existe {pedido_original}')
        sys.exit(1)
    text = pedido.read_text(encoding='utf-8', errors='ignore').strip()
    if pedido.name == 'pedido_original.txt':
        print('Aviso privacidad: usando pedido_original.txt. Si contiene datos personales, ejecutar primero: py scripts/privacy_check_job.py ' + str(job))
    else:
        print('Privacidad: usando pedido_sanitizado.txt')
    ancho, alto, orient = find_measure(text)
    entrega = detect_delivery(text)
    tipo = detect_type(text)
    productos = detect_products(text)
    sangrado = detect_bleed(text)

    pendientes = []
    if not ancho or not alto:
        pendientes.append('Confirmar medida final.')
    if not tipo:
        pendientes.append('Confirmar tipo de pieza.')
    if not productos:
        pendientes.append('Confirmar producto(s).')
    if not any(entrega.values()):
        pendientes.append('Confirmar formato de entrega.')
    if sangrado == '':
        pendientes.append('Confirmar sangrado.')

    job_id = job.name
    yaml = []
    yaml.append(f'id: {job_id}')
    yaml.append('estado: brief_extraido_pendiente_revision')
    yaml.append('origen: correo_jefe')
    yaml.append('cliente:')
    yaml.append('proyecto:')
    yaml.append(f'tipo_pieza: {q(tipo)}')
    yaml.append('')
    yaml.append('medidas:')
    yaml.append(f'  ancho_cm: {ancho if ancho else ""}')
    yaml.append(f'  alto_cm: {alto if alto else ""}')
    yaml.append(f'  orientacion: {q(orient or "")}')
    yaml.append(f'  sangrado_mm: {sangrado}')
    yaml.append('  area_segura_mm:')
    yaml.append('')
    yaml.append('entrega:')
    for k in ['editable_svg', 'vectorizado_svg', 'pdf_impresion', 'zip']:
        yaml.append(f'  {k}: {str(bool(entrega[k])).lower()}')
    yaml.append('  otro:')
    yaml.append('')
    yaml.append('productos:')
    if productos:
        for p in productos:
            yaml.append(f'  - {q(p)}')
    else:
        yaml.append('  []')
    yaml.append('')
    yaml.append('contenido:')
    yaml.append(f'  fuente: {pedido.name}')
    yaml.append('  texto_aprobado: false')
    yaml.append('  notas: "Extraído automáticamente; revisar antes de generar."')
    yaml.append('')
    yaml.append('restricciones:')
    yaml.append('  no_inventar_claims: true')
    yaml.append('  texto_vectorizado: true')
    yaml.append('  editable_para_illustrator: true')
    yaml.append('')
    yaml.append('pendientes:')
    if pendientes:
        for p in pendientes:
            yaml.append(f'  - {q(p)}')
    else:
        yaml.append('  []')
    yaml.append('')
    brief.write_text('\n'.join(yaml), encoding='utf-8')

    estado.write_text(f'''# Estado del job

Estado: brief extraído pendiente de revisión

## Resumen detectado

- Tipo pieza: {tipo or 'pendiente'}
- Medida: {(str(ancho) + ' x ' + str(alto) + ' cm') if ancho and alto else 'pendiente'}
- Orientación: {orient or 'pendiente'}
- Productos: {', '.join(productos) if productos else 'pendiente'}

## Pendientes

{chr(10).join('- [ ] ' + p for p in pendientes) if pendientes else '- [ ] Revisar y aprobar brief.'}

## Próxima acción

- [ ] Revisar `brief.yaml`.
- [ ] Completar faltantes.
- [ ] Crear/editar proyecto en `projects/piezas_vectoriales/`.
''', encoding='utf-8')

    print(f'Brief extraído: {brief}')
    if pendientes:
        print('Pendientes:')
        for p in pendientes:
            print('-', p)


if __name__ == '__main__':
    main()
