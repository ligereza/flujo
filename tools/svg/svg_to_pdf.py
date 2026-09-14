#!/usr/bin/env python3
"""SVG -> PDF vectorial via Edge headless (Windows; sin cairosvg/inkscape).

Uso: py tools/svg/svg_to_pdf.py IN.svg OUT.pdf [--size A4|WxH]
--size: A4 (default) o WxH en mm (ej: 100x140 para flyer 10x14cm).
"""
import sys, subprocess, tempfile, os
from pathlib import Path

EDGE_CANDS = [
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

def edge():
    for e in EDGE_CANDS:
        if os.path.exists(e):
            return e
    raise SystemExit("Edge no encontrado (ajusta EDGE_CANDS)")

def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    inp, out = sys.argv[1], sys.argv[2]
    size = "A4"
    if "--size" in sys.argv:
        size = sys.argv[sys.argv.index("--size") + 1]
    if size.lower() == "a4":
        page, w, h = "size:A4", "210mm", "297mm"
    else:
        wmm, hmm = size.lower().split("x")
        page, w, h = f"size:{wmm}mm {hmm}mm", f"{wmm}mm", f"{hmm}mm"
    body = Path(inp).read_text(encoding="utf-8")
    body = body[body.index("<svg"):]
    html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
            f'@page{{{page};margin:0}}html,body{{margin:0}}svg{{display:block;width:{w};height:{h}}}'
            '</style></head><body>' + body + '</body></html>')
    tmp = Path(tempfile.gettempdir()) / "_svg2pdf.html"
    tmp.write_text(html, encoding="utf-8")
    udd = Path(tempfile.gettempdir()) / "_svg2pdf_edge"
    subprocess.run([edge(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf-no-header", f"--user-data-dir={udd}",
                    f"--print-to-pdf={os.path.abspath(out)}", tmp.as_uri()], check=False)
    print("PDF:", out if os.path.exists(out) else "FALLO")

if __name__ == "__main__":
    main()
