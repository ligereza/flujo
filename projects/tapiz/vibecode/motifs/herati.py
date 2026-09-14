NAME = "herati"
CITATION = "herati / mahi: rombo-estanque con roseta central, abundancia y agua de Herat (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 12
    hx = (x % g) - g / 2.0
    hy = (y % g) - g / 2.0
    diamond = abs(hx) + abs(hy)
    r = g * 0.5
    if diamond < 1.0 or abs(diamond - r) < 1.0:
        return 0
    if diamond < r:
        return min(int(diamond / max(1e-6, r) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
