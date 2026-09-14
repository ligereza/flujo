NAME = "memling_gul"
CITATION = "gul de Memling: octogono ganchudo que el pintor flamenco retrato, emblema de linaje (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 12
    hx = (x % g) - g / 2.0
    hy = (y % g) - g / 2.0
    diamond = abs(hx) + abs(hy)
    square = max(abs(hx), abs(hy))
    r = g * 0.44
    oct_d = max(square, diamond * 0.72)
    if oct_d <= r:
        return min(int(oct_d / max(1e-6, r) * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
