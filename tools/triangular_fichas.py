"""Triangula fichas de curatoria (OCR + vision) en eventos + productoras candidatas.

Entrada: JSONL de fichas (ver formato en context/WALKTHROUGH.md / mak curatoria).
Cada linea trae, entre otros campos: ocr_texto, vision.descripcion, y
datos_evento (productora/venue/fecha/handles) ya pre-extraido por el pipeline
de vision de mak. Este script usa ese campo estructurado como senal principal
(mas confiable que re-parsear el OCR crudo) y complementa con regex sobre
ocr_texto + vision.descripcion para capturar casos donde datos_evento vino
vacio.

Uso:
    py tools/triangular_fichas.py <fichas.jsonl> --out-dir <dir>

Salidas en --out-dir: eventos.jsonl, productoras_candidatas.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

MESES = {
    "ene": 1, "enero": 1, "jan": 1,
    "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "apr": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6,
    "jul": 7, "julio": 7,
    "ago": 8, "agosto": 8, "aug": 8,
    "sep": 9, "septiembre": 9, "set": 9,
    "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12, "dec": 12,
}

FECHA_NUM_RE = re.compile(r"\b([0-3]?\d)[.\-/]([01]?\d)(?:[.\-/](\d{2,4}))?\b")
FECHA_TXT_RE = re.compile(
    r"\b([0-3]?\d)\s+(?:de\s+)?(" + "|".join(MESES) + r")\.?\s*(\d{4})?\b",
    re.IGNORECASE,
)
HANDLE_RE = re.compile(r"@[a-zA-Z0-9_.]{2,40}")
VENUE_AT_RE = re.compile(r"@\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ .]{2,40})")
PROD_KEYWORDS_RE = re.compile(
    r"(?:presenta|prod\.?\s*por|produce|organiza)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ0-9][A-Za-zÁÉÍÓÚÑáéíóúñ0-9 .&]{2,40})",
    re.IGNORECASE,
)
SLUG_URL_RE = re.compile(r"(puntoticket|passline)\.com/[a-z0-9\-]+", re.IGNORECASE)

VENUES_CONOCIDOS = [
    "Espacio Riesco", "Club Hipico", "Club Hípico", "Blondie", "Fauna",
    "Basel", "Basel Venue", "Parque de los Gasometros", "Parque de los Gasómetros",
    "Ciudad Empresarial", "Centro Cultural", "Central Cultural", "La Feria",
    "Teatro Caupolican", "Teatro Caupolicán", "Movistar Arena", "Bar Berlin",
    "Bar Berlín", "Estadio", "Parque Padre Hurtado", "Casino",
]

UPPER_LINE_RE = re.compile(r"^[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 .&/'\-]{2,40}$")
STOP_WORDS = {
    "REDUCIENDODANO", "EVENTOSOREDUCIENDODANO", "RD", "CUIDARTE", "SUSTANCIA",
    "MUESTRA", "EXPERIMENTO", "PRODUCE", "FECHA", "PARQUE", "CIUDAD",
    "EMPRESARIAL", "TBA", "T B A",
}


def parse_fecha_candidatas(text: str, year_hint: int) -> list[str]:
    out = []
    for m in FECHA_NUM_RE.finditer(text):
        d, mth = int(m.group(1)), int(m.group(2))
        if 1 <= d <= 31 and 1 <= mth <= 12:
            yr = m.group(3)
            yr = int(yr) if yr and len(yr) == 4 else year_hint
            out.append(f"{yr:04d}-{mth:02d}-{d:02d}")
    for m in FECHA_TXT_RE.finditer(text):
        d = int(m.group(1))
        mth = MESES.get(m.group(2).lower())
        yr = int(m.group(3)) if m.group(3) else year_hint
        if mth and 1 <= d <= 31:
            out.append(f"{yr:04d}-{mth:02d}-{d:02d}")
    return out


def extraer_lineup(text: str) -> list[str]:
    lineup = []
    for line in text.splitlines():
        line = line.strip(" -|.")
        if not line or len(line) < 3:
            continue
        if UPPER_LINE_RE.match(line) and line.upper() not in STOP_WORDS:
            # descarta lineas puramente numericas/fechas
            if re.search(r"[A-ZÁÉÍÓÚÑ]{3,}", line):
                lineup.append(line.title() if line.isupper() else line)
    # dedup preservando orden
    seen = set()
    dedup = []
    for a in lineup:
        k = a.upper()
        if k not in seen:
            seen.add(k)
            dedup.append(a)
    return dedup[:12]


def triangular(fichas_path: Path, out_dir: Path, sample_debug: int = 0) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    registros = []
    with fichas_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            registros.append(json.loads(line))

    candidatos = []  # cada uno: dict con productora/venue/fecha/handles/lineup/fuente
    prod_counter = Counter()
    prod_evidence = defaultdict(list)

    for r in registros:
        de = r.get("datos_evento") or {}
        ocr = r.get("ocr_texto") or ""
        vis = (r.get("vision") or {}).get("descripcion") or ""
        text = f"{ocr}\n{vis}"
        mtime = r.get("mtime") or ""
        year_hint = int(mtime[:4]) if mtime[:4].isdigit() else date.today().year

        productoras = set()
        prod_val = de.get("productora")
        if isinstance(prod_val, str) and prod_val.strip():
            productoras.add(prod_val.strip())
        elif isinstance(prod_val, list):
            productoras.update(p.strip() for p in prod_val if p and p.strip())
        for m in PROD_KEYWORDS_RE.finditer(text):
            productoras.add(m.group(1).strip())
        # nombres en mayusculas linea propia, tipo lineup, tambien candidatan a productora/lineup
        lineup = extraer_lineup(ocr)

        venues = set()
        venue_val = de.get("venue")
        if isinstance(venue_val, str) and venue_val.strip():
            venues.add(venue_val.strip())
        elif isinstance(venue_val, list):
            venues.update(v.strip() for v in venue_val if v and v.strip())
        for m in VENUE_AT_RE.finditer(text):
            venues.add(m.group(1).strip())
        for v in VENUES_CONOCIDOS:
            if v.lower() in text.lower():
                venues.add(v)

        fechas = set()
        fecha_val = de.get("fecha")
        if isinstance(fecha_val, str) and fecha_val.strip():
            fechas.update(parse_fecha_candidatas(fecha_val, year_hint))
        elif isinstance(fecha_val, list):
            for fv in fecha_val:
                fechas.update(parse_fecha_candidatas(str(fv), year_hint))
        fechas.update(parse_fecha_candidatas(text, year_hint))

        handles = set(de.get("handles") or [])
        handles.update(HANDLE_RE.findall(text))

        slugs = set(SLUG_URL_RE.findall(text))

        # filtra ruido: identidad propia RD + mojibake/basura OCR
        productoras = {
            p for p in productoras
            if p.upper() not in {"RD", "REDUCIENDODANO", "REDUCIENDODANO.CL", "EVENTOS@REDUCIENDODANO.CL", "EVENTOSOREDUCIENDODANO.CL"}
            # U+FFFD escrito como escape y no como glifo: es el centinela de
            # mojibake (un nombre que ya perdio bytes en el OCR), y el archivo
            # que lo busca no tiene por que llevarlo literal.
            and "\ufffd" not in p
            and len(p) >= 3
            and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,}", p)
        }

        if not (productoras or venues or fechas or lineup or handles):
            continue

        candidatos.append({
            "id": r.get("id"),
            "categoria": r.get("categoria"),
            "mtime": mtime,
            "productoras": sorted(productoras),
            "venues": sorted(venues),
            "fechas": sorted(fechas),
            "lineup": lineup,
            "handles": sorted(handles),
            "slugs": sorted(slugs),
        })
        for p in productoras:
            prod_counter[p.upper()] += 1
            prod_evidence[p.upper()].append(r.get("id"))

    # --- clustering de eventos: por fecha (+-1 dia) + venue o solape de lineup ---
    def fecha_bucket(fechas):
        if not fechas:
            return None
        try:
            return min(date.fromisoformat(f) for f in fechas)
        except ValueError:
            return None

    clusters = []
    for c in candidatos:
        fb = fecha_bucket(c["fechas"])
        placed = False
        for cl in clusters:
            same_venue = bool(set(v.lower() for v in c["venues"]) & set(v.lower() for v in cl["venues"]))
            same_fecha = False
            if fb and cl["_fb"]:
                same_fecha = abs((fb - cl["_fb"]).days) <= 1
            lineup_overlap = bool(set(a.upper() for a in c["lineup"]) & set(a.upper() for a in cl["lineup"]))
            if (same_venue and (same_fecha or not fb or not cl["_fb"])) or (same_fecha and same_venue) or (lineup_overlap and (same_venue or same_fecha)):
                cl["fichas"].append(c["id"])
                cl["productoras"] |= set(c["productoras"])
                cl["venues"] |= set(c["venues"])
                cl["fechas"] |= set(c["fechas"])
                cl["lineup"] |= set(c["lineup"])
                cl["handles"] |= set(c["handles"])
                if fb and not cl["_fb"]:
                    cl["_fb"] = fb
                placed = True
                break
        if not placed and (fb or c["venues"]):
            clusters.append({
                "fichas": [c["id"]],
                "productoras": set(c["productoras"]),
                "venues": set(c["venues"]),
                "fechas": set(c["fechas"]),
                "lineup": set(c["lineup"]),
                "handles": set(c["handles"]),
                "_fb": fb,
            })

    eventos = []
    for cl in clusters:
        eventos.append({
            "fecha_min": cl["_fb"].isoformat() if cl["_fb"] else None,
            "fechas_candidatas": sorted(cl["fechas"]),
            "venues": sorted(cl["venues"]),
            "productoras": sorted(cl["productoras"]),
            "lineup": sorted(cl["lineup"]),
            "handles": sorted(cl["handles"]),
            "n_fichas": len(cl["fichas"]),
            "fichas": cl["fichas"],
        })
    eventos.sort(key=lambda e: (e["fecha_min"] or "9999", -e["n_fichas"]))

    productoras_candidatas = []
    for nombre, n in prod_counter.most_common():
        productoras_candidatas.append({
            "nombre": nombre,
            "menciones": n,
            "fichas": prod_evidence[nombre][:10],
        })

    (out_dir / "eventos.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in eventos), encoding="utf-8",
    )
    (out_dir / "productoras_candidatas.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in productoras_candidatas), encoding="utf-8",
    )

    if sample_debug:
        print(f"--- {sample_debug} fichas crudas de muestra (con senal) ---")
        for c in candidatos[:sample_debug]:
            print(json.dumps(c, ensure_ascii=False, indent=2))

    return {
        "total_fichas": len(registros),
        "fichas_con_senal": len(candidatos),
        "eventos": len(eventos),
        "productoras_candidatas": len(productoras_candidatas),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fichas", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--sample-debug", type=int, default=0)
    args = ap.parse_args()
    stats = triangular(args.fichas, args.out_dir, args.sample_debug)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
