NAME = "elibelinde"
CITATION = "elibelinde: la diosa madre anatolia con las manos en la cintura, simbolo de fecundidad y maternidad (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    gw, gh = 12, 14
    lx = (x % gw) - gw / 2.0
    ly = y % gh
    head = abs(lx) + abs(ly - 2) <= 2.0
    body = abs(lx) <= 1.5 and ly >= 2
    arms = abs(ly - gh * 0.5) <= 1.2 and abs(lx) <= gw * 0.42
    if head or body or arms:
        return min(int(abs(lx) / max(1e-6, gw * 0.5) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
