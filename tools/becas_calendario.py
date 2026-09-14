#!/usr/bin/env python3
"""
becas_calendario.py: Parser de informes research FOSIS -> calendario de postulaciones.

Extrae fondos, ventanas, montos y requisitos desde informes MAK (formato MD).
Heurísticas tolerantes: busca fechas (meses español, rangos, "hasta", años 2026/2027),
montos ($, CLP, UF, USD, millones), nombres de fondo en headers.
Campos faltantes -> "no-especificado" (nunca inventar).

Uso:
  python tools/becas_calendario.py <dir_informes>
  python tools/becas_calendario.py <dir_informes> --out docs/becas/CALENDARIO_POSTULACIONES.md
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

MESES_UPPER = {k.upper(): v for k, v in MESES.items()}


def _extraer_urls(texto: str) -> List[str]:
    """Extrae todas las URLs del texto."""
    pattern = r'https?://[^\s\)\]]*'
    return list(set(re.findall(pattern, texto)))


def _extraer_fechas(texto: str) -> str:
    """Busca fechas en formato españo  l: mes ano, rangos, "hasta", años 2026/2027."""
    fechas = []

    # Buscar rangos: "15 de agosto a 30 de septiembre de 2026"
    rango_pattern = r'(\d{1,2})\s+de\s+(\w+)\s+a\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
    for match in re.finditer(rango_pattern, texto, re.IGNORECASE):
        dia1, mes1, dia2, mes2, ano = match.groups()
        mes1_num = MESES.get(mes1.lower())
        mes2_num = MESES.get(mes2.lower())
        if mes1_num and mes2_num:
            fechas.append(f"{dia1} de {mes1} a {dia2} de {mes2} de {ano}")

    # Buscar "hasta DD de mes de AAAA"
    hasta_pattern = r'hasta\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
    for match in re.finditer(hasta_pattern, texto, re.IGNORECASE):
        dia, mes, ano = match.groups()
        mes_num = MESES.get(mes.lower())
        if mes_num:
            fechas.append(f"hasta {dia} de {mes} de {ano}")

    # Buscar "DD de mes" sin ano (asume 2026/2027)
    simple_pattern = r'(\d{1,2})\s+de\s+(\w+)'
    for match in re.finditer(simple_pattern, texto, re.IGNORECASE):
        dia, mes = match.groups()
        mes_num = MESES.get(mes.lower())
        if mes_num:
            # Heurística: si no tiene año, asume 2026 o 2027 si no hay más contexto
            fechas.append(f"{dia} de {mes}")

    if fechas:
        # Dedup y retorna primera/más específica
        return "; ".join(list(dict.fromkeys(fechas))[:2])

    return "no-especificado"


def _extraer_montos(texto: str) -> str:
    """Busca montos: $, CLP, UF, USD, millones."""
    montos = []

    # Buscar rangos "entre $X.XXX.XXX y $Y.ZZZ.ZZZ CLP" (PRIMERO)
    rango_pattern = r'entre\s+\$?([\d\.]+)\s+y\s+\$?([\d\.]+)\s*(CLP|millones|UF|USD)?'
    for match in re.finditer(rango_pattern, texto, re.IGNORECASE):
        val1 = match.group(1)
        val2 = match.group(2)
        unidad = match.group(3) or 'CLP'
        if val1 and val2:
            montos.append(f"${val1} - ${val2} {unidad}".strip())

    # Buscar "máximo de $X millones" o "apoyo máximo de $X CLP"
    maximo_pattern = r'(?:máximo|apoyo máximo)\s+(?:de\s+)?\$?([\d\.]+)\s*(millones|CLP|UF|USD)?'
    for match in re.finditer(maximo_pattern, texto, re.IGNORECASE):
        val = match.group(1)
        unidad = match.group(2) or 'CLP'
        if val:
            montos.append(f"${val} {unidad}".strip())

    if montos:
        return "; ".join(list(dict.fromkeys(montos))[:2])

    return "no-especificado"


def _extraer_fondo(texto: str, filename: str) -> str:
    """Busca nombre del fondo en headers (# FONDO) o contexto del archivo."""
    # Buscar en headers: "# FOSIS Chile 2026:" o similar
    header_pattern = r'^#+\s+([A-Za-z0-9]+)'
    for line in texto.split('\n')[:20]:  # primeras 20 líneas
        match = re.match(header_pattern, line)
        if match:
            fondo = match.group(1).strip()
            if fondo.upper() in ['FOSIS', 'FOES', 'FNDR', 'PMG', 'FIC']:
                return fondo.upper()
            # Captura candidatos más largos
            if len(fondo) > 2:
                return fondo

    # Fallback: busca en negritas o mayúsculas
    bold_pattern = r'\*\*([A-Z][A-Za-z0-9]+)\*\*'
    for match in re.finditer(bold_pattern, texto):
        cand = match.group(1)
        if len(cand) >= 4:
            return cand

    # Fallback: extrae de nombre del archivo
    if 'fosis' in filename.lower():
        return 'FOSIS'

    return "no-especificado"


def _extraer_requisitos(texto: str) -> str:
    """Extrae requisitos mencionados en el informe."""
    requisitos = []

    # Buscar sección "4. Requisitos" o "Requisitos reportados"
    requisitos_pattern = r'requisitos[^:]*:\s*([^.]+(?:\.(?!\s*#))*)'
    matches = re.finditer(requisitos_pattern, texto, re.IGNORECASE | re.DOTALL)
    for match in matches:
        bloque = match.group(1).strip()
        # Limpia múltiples espacios y saltos
        bloque = re.sub(r'\s+', ' ', bloque)
        # Toma primeras 200 chars
        if len(bloque) > 50:
            requisitos.append(bloque[:200])

    if requisitos:
        return requisitos[0]

    return "no-especificado"


def parsear_informe(path: str) -> List[Dict]:
    """
    Extrae candidatos de un informe MD.

    Retorna: [{ fondo, ventana_postulacion, monto, requisitos_resumen, url_fuente, informe_origen }]
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return []

    try:
        texto = path_obj.read_text(encoding='utf-8')
    except Exception:
        return []

    # Extrae campos
    fondo = _extraer_fondo(texto, path_obj.name)
    ventana = _extraer_fechas(texto)
    monto = _extraer_montos(texto)
    requisitos = _extraer_requisitos(texto)
    urls = _extraer_urls(texto)

    if fondo == "no-especificado":
        # Si no encuentra fondo, no es un informe de becas
        return []

    return [{
        "fondo": fondo,
        "ventana_postulacion": ventana,
        "monto": monto,
        "requisitos_resumen": requisitos,
        "url_fuente": urls if urls else ["no-especificado"],
        "informe_origen": path_obj.name
    }]


def consolidar(informes_dir: str) -> List[Dict]:
    """
    Consolidaall .md files in directory que mencionen fondos/postulación/subvención.
    Dedup por nombre de fondo (conserva entrada con más campos llenos).

    Raises FileNotFoundError si `informes_dir` no existe. A missing directory
    used to return [] here, which flowed all the way to `main()` as "Fondos
    procesados: 0" and exit code 0 -- indistinguishable from a directory that
    genuinely had no matching informes this cycle. A wrong or unmounted path
    must not read as "nothing to do".
    """
    dir_path = Path(informes_dir)
    if not dir_path.exists():
        raise FileNotFoundError(
            "no existe el directorio de informes: %s" % dir_path)

    todos_candidatos = []
    for md_file in dir_path.glob('*.md'):
        candidatos = parsear_informe(str(md_file))
        todos_candidatos.extend(candidatos)

    # Dedup por fondo: conserva entrada con máximo de campos != "no-especificado"
    dedup = {}
    for cand in todos_candidatos:
        fondo = cand['fondo']
        if fondo not in dedup:
            dedup[fondo] = cand
        else:
            # Compara cantidad de campos útiles
            campos_nuevo = sum(1 for v in cand.values() if v != "no-especificado")
            campos_viejo = sum(1 for v in dedup[fondo].values() if v != "no-especificado")
            if campos_nuevo > campos_viejo:
                dedup[fondo] = cand

    return list(dedup.values())


def render_calendario(candidatos: List[Dict]) -> str:
    """
    Renderiza tabla ASCII markdown ordenada por fecha límite.
    no-especificado al final.
    """
    # Ordena: intenta parsear fechas para ordenarlas; si falla, va al final
    def sort_key(cand):
        ventana = cand.get('ventana_postulacion', 'no-especificado')
        if ventana == 'no-especificado':
            return (1, ventana)  # Al final
        # Intenta extraer mes/año para ordenar
        match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', ventana)
        if match:
            dia, mes, ano = match.groups()
            mes_num = MESES.get(mes.lower(), 13)
            return (0, int(ano), mes_num, int(dia))
        return (1, ventana)

    ordenados = sorted(candidatos, key=sort_key)

    # Encabezado
    lineas = [
        f"# Calendario de Postulaciones de Fondos",
        f"",
        f"_Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC_",
        f"_Fuente: Parseo de informes research MAK (generado por becas_calendario.py)_",
        f"",
        f"| Fondo | Ventana | Monto | Requisitos | Fuente |",
        f"|-------|---------|-------|-----------|--------|",
    ]

    # Rows
    for cand in ordenados:
        fondo = cand.get('fondo', '?')
        ventana = cand.get('ventana_postulacion', '?')
        monto = cand.get('monto', '?')
        req = cand.get('requisitos_resumen', '?')
        urls = cand.get('url_fuente', [])

        # Limpia requisitos para tabla (máx 80 chars)
        if req != '?' and req != "no-especificado":
            req = (req[:77] + '...') if len(req) > 80 else req

        # URLs: máximo 3, separadas por ; y abreviadas
        url_str = 'no-especificado'
        if urls and urls != ['no-especificado']:
            url_display = []
            for url in urls[:3]:
                # Acorta URL: dominio.ext
                match = re.search(r'https?://([^/]+)', url)
                if match:
                    url_display.append(match.group(1))
            url_str = '; '.join(url_display) if url_display else 'no-especificado'

        linea = f"| {fondo} | {ventana} | {monto} | {req} | {url_str} |"
        lineas.append(linea)

    lineas.extend([
        f"",
        f"**Nota:** No-especificado indica que el campo no se encontró en las fuentes.",
        f"Verifica las URLs y los informes originales antes de postular.",
    ])

    return '\n'.join(lineas)


def main():
    """CLI: python tools/becas_calendario.py <dir> [--out <output.md>]"""
    if len(sys.argv) < 2:
        print("Uso: python tools/becas_calendario.py <dir_informes> [--out <salida.md>]")
        sys.exit(1)

    dir_informes = sys.argv[1]
    out_file = None

    if '--out' in sys.argv:
        idx = sys.argv.index('--out')
        if idx + 1 < len(sys.argv):
            out_file = sys.argv[idx + 1]

    # Consolidar
    try:
        candidatos = consolidar(dir_informes)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Renderizar
    calendario = render_calendario(candidatos)

    # Guardar o imprimir
    if out_file:
        out_path = Path(out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(calendario, encoding='utf-8')
        print(f"Calendario guardado en: {out_file}")
        print(f"Fondos procesados: {len(candidatos)}")
    else:
        print(calendario)


if __name__ == '__main__':
    main()
