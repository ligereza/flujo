NAME = "crab"
CITATION = "cangrejo / crab: motivo ganchudo turcomano que aleja la esterilidad, amuleto de fecundidad (dossier tapiz)"


def color_index(x, y, n_cols, n_rows, n_colors):
    ncol = max(1, n_colors)
    g = 10
    lx = (x % g) - g / 2.0
    ly = (y % g) - g / 2.0
    arm = 2.0
    on_cross = abs(lx) <= arm or abs(ly) <= arm
    hook = (abs(abs(lx) - g * 0.4) < 1.1 and abs(ly) <= arm) or (
        abs(abs(ly) - g * 0.4) < 1.1 and abs(lx) <= arm
    )
    if on_cross or hook:
        return min(int((abs(lx) + abs(ly)) / g * ncol), ncol - 1)
    return ((x // 4) + (y // 2)) % ncol
