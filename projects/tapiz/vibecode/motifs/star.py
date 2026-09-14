NAME = "star"
CITATION = "star / khatim: estrella de ocho puntas, sello de Salomon y orden cosmico (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 14
    hx = (x % g) - g / 2.0
    hy = (y % g) - g / 2.0
    diamond = abs(hx) + abs(hy)
    square = max(abs(hx), abs(hy))
    r = g * 0.34
    if diamond <= r * 1.15 or square <= r * 0.80:
        return min(int((diamond + square) / max(1e-6, g) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
