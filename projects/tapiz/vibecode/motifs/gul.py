NAME = "gul"
CITATION = "gul: medallon octogonal repetido en el campo, sello de clan de la familia tejedora (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 12
    hx = (x % g) - g / 2.0
    hy = (y % g) - g / 2.0
    diamond = abs(hx) + abs(hy)
    square = max(abs(hx), abs(hy))
    r = g * 0.42
    if diamond <= r and square <= g * 0.34:
        return min(int(diamond / max(1e-6, r) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
