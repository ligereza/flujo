#!/usr/bin/env python3
"""Arma un ZIP de entrega de un tiro.

Uso: py tools/svg/pack_delivery.py OUT.zip <DIR|GLOB>...
Cada carpeta se agrega como subcarpeta (por su nombre) dentro del zip;
los archivos sueltos van a la raiz del zip.
"""
import sys, zipfile, glob, os

def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out, srcs = sys.argv[1], sys.argv[2:]
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for s in srcs:
            if os.path.isdir(s):
                base = os.path.basename(os.path.normpath(s))
                for f in glob.glob(os.path.join(s, "**", "*"), recursive=True):
                    if os.path.isfile(f):
                        arc = base + "/" + os.path.relpath(f, s).replace("\\", "/")
                        z.write(f, arc); n += 1
            else:
                for f in glob.glob(s):
                    if os.path.isfile(f):
                        z.write(f, os.path.basename(f)); n += 1
    print(f"ZIP {out}: {n} archivo(s), {round(os.path.getsize(out)/1024, 1)} KB")

if __name__ == "__main__":
    main()
