NAME = "scorpion"
CITATION = "alacran / scorpion: akrep tejido como talisman, protege del aguijon y del mal (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    gw, gh = 12, 12
    lx = (x % gw) - gw / 2.0
    ly = (y % gh) - gh / 2.0
    body = abs(lx) <= 1.5
    legs = abs(abs(ly) - abs(lx)) < 1.1 and abs(lx) <= gw * 0.4
    tail = abs(lx - gw * 0.3) < 1.1 and ly < 0
    if body or legs or tail:
        return min(int((abs(lx) + abs(ly)) / gw * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
