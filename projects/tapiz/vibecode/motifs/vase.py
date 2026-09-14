NAME = "vase"
CITATION = "jarron / vase: el vaso de la inmortalidad persa, fuente de la que brota el jardin eterno (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    tw, th = 14, 16
    lx = (x % tw) - tw / 2.0
    ly = y % th
    neck = th * 0.2
    belly = th * 0.55
    if ly < neck:
        half = tw * 0.14
    elif ly < belly:
        half = tw * 0.14 + (tw * 0.30) * ((ly - neck) / max(1e-6, belly - neck))
    else:
        half = tw * 0.44 - (tw * 0.30) * ((ly - belly) / max(1e-6, th - belly))
    dx = abs(lx)
    if dx <= half:
        if abs(dx - half) < 1.0 or ly < 1.0:
            return 0  # boca / borde del jarron
        return min(int((1 - dx / max(1e-6, half)) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
