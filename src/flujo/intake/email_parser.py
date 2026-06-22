"""Parser de correos para extraer links de IG, secciones, tipo de proyecto."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List


def extract_instagram_links(text: str) -> List[str]:
    """Extrae links de posts/reels/tv de Instagram.

    Acepta URLs con o sin esquema (https://, http:// o nada) y con o sin www.
    Devuelve cada link normalizado con 'https://' al frente. Ignora query string.
    """
    # Soporta: instagram.com/p/CODE/  y  instagram.com/<usuario>/p/CODE/
    # (con o sin esquema, con o sin www, p/reel/reels/tv)
    pattern = (
        r'(?:https?://)?(?:www\.)?instagram\.com/'
        r'(?:[A-Za-z0-9_.]+/)?'
        r'(?:p|reel|reels|tv)/[A-Za-z0-9_-]+/?'
    )
    out: List[str] = []
    seen = set()
    for m in re.findall(pattern, text, flags=re.IGNORECASE):
        url = m.strip()
        # normalizar esquema
        low = url.lower()
        if low.startswith("http://"):
            url = "https://" + url[len("http://"):]
        elif not low.startswith("https://"):
            url = "https://" + url
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def detect_private_account(text: str) -> bool:
    keywords = ['privado', 'private', 'no se puede descargar', 'requiere login', 'shadowban']
    return any(kw in text.lower() for kw in keywords)


def detect_video_in_carousel(text: str) -> bool:
    keywords = ['video', 'reel', 'mp4', 'primera imagen es video']
    return any(kw in text.lower() for kw in keywords)


def detect_project_type(text: str) -> str:
    """Detecta el tipo de proyecto basado en palabras clave."""
    text_lower = text.lower()
    # order matters: more specific first
    checks = [
        ('rider', ['rider', 'layout operativo', 'intervención en terreno', 'intervencion en terreno']),
        ('etiqueta', ['etiqueta', 'label', 'suplemento']),
        ('brief', ['brief', 'briefing']),
        ('pendon', ['pendon', 'pendón', 'banner']),
        ('one_page', ['one page', 'one-page', 'dossier', 'propuesta']),
        ('carrusel', ['carrusel', 'carrusel cuadrado']),
        ('tarjeta', ['tarjeta', 'card']),
        ('sticker', ['sticker']),
        ('flyer', ['flyer']),
    ]
    for tipo, keywords in checks:
        if any(kw in text_lower for kw in keywords):
            return tipo
    return 'flyer'


def extract_sections(text: str) -> Dict[str, str]:
    sections = {}
    patterns = {
        'titulo': r'(?:título|titulo|title)[:\s]+(.+)',
        'fecha': r'(?:fecha|date)[:\s]+(.+)',
        'evento': r'(?:evento|event)[:\s]+(.+)',
        'productora': r'(?:productora|producer)[:\s]+(.+)',
        'lugar': r'(?:lugar|venue)[:\s]+(.+)',
        'medidas': r'(?:medidas|medida|size)[:\s]+(.+)',
        'cliente': r'(?:cliente|client)[:\s]+(.+)',
        'producto': r'(?:producto|product)[:\s]+(.+)',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()
    # FIX: captura medidas inline como 'etiqueta 16.5x6.5 cm'
    if 'medidas' not in sections:
        m = re.search(r'(\d+(?:[\.,]\d+)?)\s*[x×]\s*(\d+(?:[\.,]\d+)?)\s*(cm|mm)?', text, re.I)
        if m:
            unit = (m.group(3) or 'cm').lower()
            w = m.group(1).replace(',', '.')
            h = m.group(2).replace(',', '.')
            sections['medidas'] = f'{w}x{h} {unit}'

    return sections


def generate_warnings(result: Dict) -> List[str]:
    warnings = []
    if result.get('is_private'):
        warnings.append('⚠️ CUENTA PRIVADA')
    if result.get('has_video'):
        warnings.append('⚠️ VIDEO EN CARRUSEL')
    if result.get('link_count', 0) == 0:
        warnings.append('⚠️ SIN LINKS DE INSTAGRAM')
    return warnings


def parse_email_content(text: str) -> Dict:
    links = extract_instagram_links(text)
    result = {
        'project_type': detect_project_type(text),
        'instagram_links': links,
        'link_count': len(links),
        'is_private': detect_private_account(text),
        'has_video': detect_video_in_carousel(text),
        'sections': extract_sections(text),
        'warnings': [],
    }
    result['warnings'] = generate_warnings(result)
    return result


def parse_email_file(filepath: Path) -> Dict:
    try:
        return parse_email_content(filepath.read_text(encoding='utf-8'))
    except Exception as e:
        return {'error': str(e)}


# --- Pedido parser for hub API (real backend integration) ---
# Returns structure compatible with hub JS fallback + enhanced match
def parse_pedido_text(text: str) -> dict:
    """Parse free text pedido into structured brief + match hints.
    Used by flujo app hub API for real Python logic (vs pure JS fallback).
    """
    if not text or not text.strip():
        return {"tipo": "desconocido", "error": "Empty input"}
    low = text.lower()
    # Reuse existing detectors where possible
    project_type = detect_project_type(text)
    sections = extract_sections(text)
    vol_match = re.search(r'(\d+)', text)
    vol = int(vol_match.group(1)) if vol_match else 7

    # Map to formato/tool known in hub
    tipo_map = {
        'flyer': {'tipo': 'flyer', 'medidas': sections.get('medidas', '10x14'), 'formato': 'evt_flyer_fisico_10x14', 'tool': 'render'},
        'etiqueta': {'tipo': 'etiqueta', 'medidas': sections.get('medidas', '16.5x6.5'), 'formato': 'sup_etiqueta_165x65', 'tool': 'render'},
        'rider': {'tipo': 'rider', 'medidas': 'A4', 'formato': 'rider_eventos_a4', 'tool': 'plano'},
        'plano': {'tipo': 'plano', 'medidas': 'según evento', 'formato': 'plano_stand', 'tool': 'plano'},
        'stand': {'tipo': 'plano', 'medidas': 'según evento', 'formato': 'plano_stand', 'tool': 'plano'},
        'cotizacion': {'tipo': 'cotizacion', 'medidas': '', 'formato': 'cotizaciones', 'tool': 'cotizaciones'},
        'cartelera': {'tipo': 'cartelera', 'medidas': '1080x1920', 'formato': 'evt_cartelera', 'tool': 'render'},
        'ig': {'tipo': 'post_ig', 'medidas': '1080x1350', 'formato': 'evt_post_ig', 'tool': 'render'},
    }
    match = tipo_map.get(project_type, {'tipo': project_type or 'desconocido', 'medidas': sections.get('medidas', ''), 'formato': '', 'tool': 'render'})

    pub = 'interno' if ('interno' in low or 'empresa' in low) else 'productora'
    formato = match['formato']
    data = {
        'tipo': match['tipo'],
        'medidas': match.get('medidas') or sections.get('medidas', 'definir'),
        'formato': formato,
        'tool': match['tool'],
        'pub': pub,
        'vol': vol,
        'notas': text.strip()[:300],
        'sections': sections,
    }
    if not formato:
        data['sugerencia'] = 'NO MATCH - proponer en projects/flujo/ o LAST_HANDOFF'
    return data
