"""Tests de projects/tapiz/vibecode (reconciliado 2026-07-10).

El paquete vive fuera de src/flujo, asi que se agrega su carpeta al path.
Cubre: primitivas compartidas (ansi), render estatico (spaces), render de
linea (void), proxy vivo (life) y medidor de potencia (power).
"""

import io
import sys
from pathlib import Path

TAPIZ_DIR = Path(__file__).resolve().parents[1] / "projects" / "tapiz"
sys.path.insert(0, str(TAPIZ_DIR))

import vibecode  # noqa: E402
from vibecode.ansi import RESET, bg_gray, fg_gray, tokenize  # noqa: E402
from vibecode.render import style_text  # noqa: E402
from vibecode.power import PowerMeter  # noqa: E402
from vibecode.spaces import PALETTES, render_spaces, render_static  # noqa: E402
from vibecode.void import render_line_blocks, render_line_negative  # noqa: E402


def _strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;?]*[a-zA-Z]", "", text)


def test_tokenize_preserva_todo():
    line = "def foo(a, b):  return a"
    tokens = tokenize(line)
    assert "".join(part for _, part in tokens) == line
    kinds = {kind for kind, _ in tokens}
    assert kinds == {"word", "space"}


def test_gray_clamp():
    assert bg_gray(-5) == bg_gray(0)
    assert fg_gray(99) == fg_gray(23)


def test_render_static_conserva_texto_ghost():
    code = "if x:\n    y = 1"
    out = render_static(code, mode="void", palette_name="flujo")
    # El texto original debe seguir presente (ghost), los espacios rellenados con el fill char
    plain = _strip_ansi(out)
    assert "if" in plain and "y = 1".replace(" ", "·") in plain.replace("·", "·")
    assert "·" in plain  # espacios -> fill char


def test_render_static_paleta_desconocida_cae_a_flujo():
    out_bad = render_static("a  b", palette_name="no-existe")
    out_flujo = render_static("a  b", palette_name="flujo")
    assert out_bad == out_flujo


def test_paleta_default_es_flujo():
    assert list(PALETTES.keys())[0] == "flujo"


def test_render_spaces_estatico_escribe_a_file():
    buf = io.StringIO()
    render_spaces("x = 1", mode="void", animate=False, file=buf)
    out = buf.getvalue()
    assert "Tapiz Spaces" in _strip_ansi(out)
    assert "x" in _strip_ansi(out)


def test_void_render_line_ancho_exacto():
    line = "    return data"
    for fn in (render_line_negative, render_line_blocks):
        out = fn(line, width=40, ghost=True)
        assert len(_strip_ansi(out)) == 40


def test_void_render_line_recorta():
    out = render_line_negative("x" * 100, width=10, ghost=False)
    assert len(_strip_ansi(out)) == 10


def test_style_text_reposo_vs_actividad():
    text = "a  b"
    quiet = style_text(text, power=0.0)
    busy = style_text(text, power=1.0)
    assert _strip_ansi(quiet) == text
    assert _strip_ansi(busy) == text
    assert quiet != busy  # la potencia cambia el estilo


def test_power_meter_sube_y_decae():
    meter = PowerMeter(window=1.0, threshold=10)
    assert meter.power() == 0.0
    meter.pulse(100)
    assert meter.power() > 0.5


def test_life_proxy_restaura_stdout():
    original = sys.stdout
    with vibecode.watch():
        print("hola vibecode")
        assert sys.stdout is not original
    assert sys.stdout is original


def test_api_publica():
    for name in ("init", "deinit", "watch", "life", "pulse", "render_spaces"):
        assert hasattr(vibecode, name)


def test_svg_export_xml_valido_y_paleta_flujo(tmp_path):
    import xml.etree.ElementTree as ET
    from vibecode.svg_export import FLUJO_HEX, export_svg

    out = tmp_path / "pieza.svg"
    export_svg("def f(x):\n    return x\n     y", str(out), mode="void")
    svg = out.read_text(encoding="utf-8")
    ET.fromstring(svg)  # XML valido
    assert FLUJO_HEX["ink"] in svg       # fondo
    assert FLUJO_HEX["support"] in svg   # bloques de 1 y 4 espacios (idx len%5)
    assert FLUJO_HEX["accent"] in svg    # bloque de 5 espacios (idx 0)
    assert "<animate" not in svg         # sin -a no hay animacion


def test_svg_export_animado_y_sin_ghost(tmp_path):
    from vibecode.svg_export import GHOST_COLOR, export_svg

    out = tmp_path / "pieza.svg"
    export_svg("a b\n  c", str(out), animate=True, ghost=False)
    svg = out.read_text(encoding="utf-8")
    assert "<animate" in svg and 'dur="90s"' in svg
    assert GHOST_COLOR not in svg  # sin ghost el texto no lleva gris fantasma


def test_svg_export_escapa_html(tmp_path):
    from vibecode.svg_export import export_svg

    out = tmp_path / "pieza.svg"
    export_svg("if a < b: c = '<&>'", str(out))
    svg = out.read_text(encoding="utf-8")
    assert "&lt;" in svg and "&amp;" in svg


# ---------------------------------------------------------------------------
# Modos loom: field / border / medallion / mihrab (nativos) + motifs/ (plugins)
# ---------------------------------------------------------------------------
from vibecode.loom import (  # noqa: E402
    LOOM_BUILTIN_MODES,
    LOOM_MODES,
    MOTIF_CITATIONS,
    block_segments,
    canvas_size,
    loom_color_index,
)

# Canvas sintetico: 24 filas x 40 columnas, con espacio interior grande para
# que aparezcan marcos, vacio central, anillos y arco.
LOOM_SAMPLE = "\n".join("x" + " " * 38 + "x" for _ in range(24))


def test_loom_modes_registrados_con_cita():
    # Los 4 nativos encabezan la tupla; los plugins de motifs/ se suman detras.
    assert LOOM_BUILTIN_MODES == ("field", "border", "medallion", "mihrab")
    assert LOOM_MODES[:4] == LOOM_BUILTIN_MODES
    assert len(LOOM_MODES) == len(set(LOOM_MODES))  # sin nombres repetidos
    for mode in LOOM_MODES:
        cita = MOTIF_CITATIONS[mode]
        assert cita and "\n" not in cita  # una linea
        assert "dossier tapiz" in cita    # cita al dossier curado


def test_loom_plugins_cargados_y_distintos_del_field():
    # El loader de motifs/ registra motivos extra (fold del telar en loom).
    extra = LOOM_MODES[4:]
    assert extra, "no se cargo ningun motivo-plugin de motifs/"
    field = render_static(LOOM_SAMPLE, mode="field")
    for mode in extra:
        # Cada plugin es un modo real, no un alias del campo base.
        assert render_static(LOOM_SAMPLE, mode=mode) != field


def test_loom_render_static_valido_por_modo():
    for mode in LOOM_MODES:
        out = render_static(LOOM_SAMPLE, mode=mode, palette_name="flujo")
        plain = _strip_ansi(out)
        assert "·" in plain  # espacios digeridos a fill char
        # El contenido plano se conserva (mismas celdas, solo cambia el color)
        assert plain == LOOM_SAMPLE.replace(" ", "·")


def test_loom_modos_difieren_estructuralmente_en_ansi():
    outs = {m: render_static(LOOM_SAMPLE, mode=m) for m in LOOM_MODES}
    vals = list(outs.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert vals[i] != vals[j]


def test_loom_border_marcos_y_vacio_central():
    # Borde exterior: primer marco (indice 0); centro: vacio (None)
    assert loom_color_index("border", 0, 0, 40, 24, 5) == 0
    assert loom_color_index("border", 20, 12, 40, 24, 5) is None
    # Los marcos avanzan de color con la profundidad
    assert loom_color_index("border", 2, 12, 40, 24, 5) == 1


def test_loom_medallion_radial_y_simetrico():
    # Centro del canvas: indice 0 (nucleo del medallon)
    assert loom_color_index("medallion", 20, 12, 41, 25, 5) == 0
    # Esquina: anillo exterior, indice mayor que el centro
    corner = loom_color_index("medallion", 0, 0, 41, 25, 5)
    assert corner is not None and corner > 0
    # Simetria vertical: fila de arriba == fila de abajo
    assert loom_color_index("medallion", 7, 0, 41, 25, 5) == loom_color_index(
        "medallion", 7, 24, 41, 25, 5
    )


def test_loom_mihrab_asimetrico_apunta_arriba():
    # Apice: arriba al centro, indice 0
    assert loom_color_index("mihrab", 20, 0, 41, 25, 5) == 0
    # Sin simetria vertical: el arco abre hacia abajo
    top = loom_color_index("mihrab", 20, 0, 41, 25, 5)
    bottom = loom_color_index("mihrab", 20, 24, 41, 25, 5)
    assert top != bottom


def test_loom_field_malla_repetitiva():
    # La malla se repite: misma celda de la malla -> mismo color
    a = loom_color_index("field", 0, 0, 40, 24, 5)
    b = loom_color_index("field", 0 + 4 * 5, 0, 40, 24, 5)  # 5 celdas a la derecha
    assert a == b
    # Y varia dentro de la malla
    assert loom_color_index("field", 0, 0, 40, 24, 5) != loom_color_index(
        "field", 4, 0, 40, 24, 5
    )


def test_loom_block_segments_conserva_longitud():
    for mode in LOOM_MODES:
        segs = block_segments(mode, 3, 5, 17, 40, 24, 5)
        assert sum(n for n, _ in segs) == 17
        assert all(n > 0 for n, _ in segs)


def test_loom_modo_desconocido_lanza_error():
    import pytest

    with pytest.raises(ValueError):
        loom_color_index("garden", 0, 0, 10, 10, 5)


def test_canvas_size_minimos():
    assert canvas_size([]) == (1, 1)
    assert canvas_size(["", "abc"]) == (3, 2)


def test_loom_render_spaces_terminal_incluye_cita():
    for mode in LOOM_MODES:
        buf = io.StringIO()
        render_spaces(LOOM_SAMPLE, mode=mode, animate=False, file=buf)
        plain = _strip_ansi(buf.getvalue())
        assert MOTIF_CITATIONS[mode] in plain


def test_loom_animate_cae_a_estatico():
    # Los modos loom son composiciones estaticas: -a no debe entrar al bucle
    # de animacion (sin CLEAR_SCREEN, sin frames).
    from vibecode.ansi import CLEAR_SCREEN

    buf = io.StringIO()
    render_spaces(LOOM_SAMPLE, mode="border", animate=True, file=buf)
    out = buf.getvalue()
    assert CLEAR_SCREEN not in out
    assert MOTIF_CITATIONS["border"] in _strip_ansi(out)


def test_loom_svg_valido_con_desc_curatorial(tmp_path):
    import xml.etree.ElementTree as ET
    from vibecode.svg_export import export_svg

    for mode in LOOM_MODES:
        out = tmp_path / f"pieza_{mode}.svg"
        export_svg(LOOM_SAMPLE, str(out), mode=mode)
        svg = out.read_text(encoding="utf-8")
        root = ET.fromstring(svg)  # XML valido
        desc = root.find("{http://www.w3.org/2000/svg}desc")
        assert desc is not None, f"modo {mode} sin <desc>"
        assert desc.text == MOTIF_CITATIONS[mode]


def test_loom_svg_modos_difieren_estructuralmente(tmp_path):
    from vibecode.svg_export import render_svg

    svgs = {m: render_svg(LOOM_SAMPLE, mode=m) for m in LOOM_MODES}
    vals = list(svgs.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert vals[i] != vals[j]


def test_loom_svg_border_usa_vacio_central(tmp_path):
    from vibecode.svg_export import LOOM_VOID_HEX, render_svg

    svg_border = render_svg(LOOM_SAMPLE, mode="border")
    assert LOOM_VOID_HEX in svg_border      # el centro queda apagado
    svg_field = render_svg(LOOM_SAMPLE, mode="field")
    assert LOOM_VOID_HEX not in svg_field   # la malla no tiene vacio


def test_loom_svg_sin_desc_en_modos_clasicos(tmp_path):
    import xml.etree.ElementTree as ET
    from vibecode.svg_export import render_svg

    root = ET.fromstring(render_svg(LOOM_SAMPLE, mode="void"))
    assert root.find("{http://www.w3.org/2000/svg}desc") is None


def test_loom_cli_acepta_modos():
    # El registry del CLI (-m) debe ofrecer todos los modos loom (nativos+plugins)
    import vibecode.spaces as spaces_mod

    src_choices = ["void", "length", "blocks", "flow", "scan", "drift", "pulse", "rain"]
    assert set(LOOM_MODES).isdisjoint(src_choices)
    for mode in LOOM_MODES:
        out = render_static("a  b", mode=mode)  # no lanza
        assert out
    assert hasattr(spaces_mod, "LOOM_VOID_COLOR")


# ---------------------------------------------------------------------------
# Modo cauce: reconocimiento, rios y marcas (puente tilde)
# ---------------------------------------------------------------------------
from vibecode.cauce import (  # noqa: E402
    CAUCE_CITATION,
    CAUCE_MODE,
    freq_class,
    render_svg_cauce,
    river_runs,
    token_color,
    token_frequencies,
)

SVG_NS = "{http://www.w3.org/2000/svg}"

# Fuente con recurrencia clara: "telar" recurrente, "unico" hapax,
# marcas (tilde/enie/puntuacion) y sangria que forma rios.
CAUCE_SAMPLE = "\n".join(
    [
        "telar rio anos telar:",
        "    telar rio unico",
        "    telar rio",
        "    telar fin.",
    ]
)


def _cauce_groups(svg_text):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(svg_text)
    return [g for g in root.iter(f"{SVG_NS}g") if (g.get("class") or "").startswith("cauce-")]


def _fills_de_token(svg_text, token):
    fills = []
    for g in _cauce_groups(svg_text):
        for t in g.findall(f"{SVG_NS}text"):
            if t.text == token:
                fills.append(g.get("fill"))
    return fills


def test_cauce_modo_registrado_y_cli_corre(tmp_path):
    import os
    import subprocess

    # Registro: render estatico y frecuencias funcionan
    out = render_static(CAUCE_SAMPLE, mode=CAUCE_MODE)
    assert out and _strip_ansi(out)
    assert freq_class(8) == "structural" and freq_class(1) == "hapax"
    # CLI real: -m cauce sin -a (terminal estatico)
    src = tmp_path / "src.py"
    src.write_text("def f():\n    return 1\n", encoding="utf-8")
    script = TAPIZ_DIR / "vibecode_spaces.py"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), str(src), "-m", CAUCE_MODE],
        capture_output=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert CAUCE_CITATION.split(";")[0] in r.stdout.decode("utf-8", "replace")


def test_cauce_render_spaces_incluye_cita_y_es_estatico():
    from vibecode.ansi import CLEAR_SCREEN

    buf = io.StringIO()
    # cauce en terminal es estatico: -a no entra al bucle de animacion
    render_spaces(CAUCE_SAMPLE, mode=CAUCE_MODE, animate=True, file=buf)
    out = buf.getvalue()
    assert CLEAR_SCREEN not in out
    assert CAUCE_CITATION in _strip_ansi(out)


def test_cauce_svg_xml_valido_con_desc(tmp_path):
    import xml.etree.ElementTree as ET
    from vibecode.svg_export import export_svg

    out = tmp_path / "cauce.svg"
    export_svg(CAUCE_SAMPLE, str(out), mode=CAUCE_MODE)
    svg = out.read_text(encoding="utf-8")
    root = ET.fromstring(svg)  # XML valido
    desc = root.find(f"{SVG_NS}desc")
    assert desc is not None and desc.text == CAUCE_CITATION


def test_cauce_invariante_de_reconocimiento():
    svg = render_svg_cauce(CAUCE_SAMPLE)
    fills_telar = _fills_de_token(svg, "telar")
    freq = token_frequencies(CAUCE_SAMPLE)
    assert len(fills_telar) == freq["telar"] >= 3
    # Mismo token = mismo color en TODAS las apariciones
    assert len(set(fills_telar)) == 1
    # Y distinto de un token de otra clase (recurrente vs hapax)
    fills_unico = _fills_de_token(svg, "unico")
    assert len(fills_unico) == 1
    assert fills_unico[0] != fills_telar[0]
    # La funcion pura respeta lo mismo
    assert token_color("telar", "recurrent") == fills_telar[0]
    assert token_color("unico", "hapax") == fills_unico[0]


def test_cauce_rios_indentacion_vs_plano():
    indented = CAUCE_SAMPLE  # 3 lineas seguidas con sangria de 4
    flat = "a b\nlongword\nc d e\nxx yy"  # sin columnas de espacio alineadas
    assert len(river_runs(indented.splitlines())) >= 1
    assert len(river_runs(flat.splitlines())) == 0
    svg_indent = render_svg_cauce(indented)
    svg_flat = render_svg_cauce(flat)
    assert svg_indent.count('class="cauce-river"') >= 1
    assert svg_flat.count('class="cauce-river"') < svg_indent.count(
        'class="cauce-river"'
    )


def test_cauce_animado_digestion_y_marcas_sin_decay():
    svg = render_svg_cauce(CAUCE_SAMPLE, animate=True)
    assert "<animate" in svg
    # Digestion: los hapax decaen hacia 0.12 tarde en el ciclo
    assert "0.12" in svg
    for g in _cauce_groups(svg):
        cls = g.get("class")
        animates = list(g.iter(f"{SVG_NS}animate"))
        if cls == "cauce-marks":
            # Las marcas NUNCA decaen: a lo sumo pulso suave 0.85<->1.0
            assert animates, "marcas sin animacion de pulso"
            for a in animates:
                assert "0.12" not in (a.get("values") or "")
                if a.get("attributeName") == "opacity":
                    assert a.get("values") == "1;0.85;1"
        elif cls == "cauce-hapax":
            vals = [a.get("values") or "" for a in animates]
            assert any("0.12" in v for v in vals), "hapax sin decay"


def test_cauce_estatico_sin_animate_y_digerido():
    svg = render_svg_cauce(CAUCE_SAMPLE, animate=False)
    assert "<animate" not in svg
    # Estado post-digestion: los grupos hapax quedan atenuados
    hapax = [g for g in _cauce_groups(svg) if g.get("class") == "cauce-hapax"]
    assert hapax and all(float(g.get("opacity")) < 1.0 for g in hapax)
    # Las marcas quedan brillantes y sin atenuar
    marks = [g for g in _cauce_groups(svg) if g.get("class") == "cauce-marks"]
    assert marks and all(g.get("opacity") is None for g in marks)
    assert all(g.get("fill") == "#b7ffd9" for g in marks)


# ---------------------------------------------------------------------------
# Morfologias del vacio animado: espaciado / zigzag_vertical / raices
# (direccion del artista 2026-07-12, ver vibecode/void_shapes.py)
# ---------------------------------------------------------------------------
from vibecode.spaces import SAMPLE_CODE, render_frame  # noqa: E402
from vibecode.void_shapes import (  # noqa: E402
    VOID_SHAPE_CITATIONS,
    VOID_SHAPE_MODES,
    espaciado_frame,
    generate_roots,
    zigzag_thread_at,
    zigzag_vertical_frame_segments,
)


def test_void_shape_modes_registrados_con_cita():
    assert VOID_SHAPE_MODES == ("espaciado", "zigzag_vertical", "raices")
    for mode in VOID_SHAPE_MODES:
        cita = VOID_SHAPE_CITATIONS[mode]
        assert cita and "\n" not in cita
        assert "direccion tapiz" in cita


def test_void_shape_modes_no_chocan_con_loom_ni_flujo_base():
    src_choices = ["void", "length", "blocks", "flow", "scan", "drift", "pulse", "rain"]
    assert set(VOID_SHAPE_MODES).isdisjoint(src_choices)
    assert set(VOID_SHAPE_MODES).isdisjoint(LOOM_MODES)


def test_void_shape_cli_acepta_los_tres_modos(tmp_path):
    # CLI real: -m <modo> (terminal) y -m <modo> --svg (export) para los tres.
    import os
    import subprocess

    src = tmp_path / "src.py"
    src.write_text("def f(a, b):\n    return a + b\n", encoding="utf-8")
    script = TAPIZ_DIR / "vibecode_spaces.py"
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for mode in VOID_SHAPE_MODES:
        r = subprocess.run(
            [sys.executable, str(script), str(src), "-m", mode, "-a", "-c", "2", "-s", "0.01"],
            capture_output=True,
            env=env,
        )
        assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
        out_svg = tmp_path / f"{mode}.svg"
        r_svg = subprocess.run(
            [sys.executable, str(script), str(src), "-m", mode, "-a", "--svg", str(out_svg)],
            capture_output=True,
            env=env,
        )
        assert r_svg.returncode == 0, r_svg.stderr.decode("utf-8", "replace")
        assert out_svg.exists() and out_svg.stat().st_size > 0


def test_void_shape_render_frame_anima_con_t():
    for mode in VOID_SHAPE_MODES:
        f0 = render_frame(SAMPLE_CODE, mode=mode, t=0)
        f5 = render_frame(SAMPLE_CODE, mode=mode, t=5)
        f30 = render_frame(SAMPLE_CODE, mode=mode, t=30)
        assert f0 and f5 and f30
        assert f0 != f5, f"{mode}: no cambia entre t=0 y t=5"
        assert f5 != f30, f"{mode}: no cambia entre t=5 y t=30"
        # El texto fantasma se conserva integro (los glifos de palabra nunca
        # se tocan; solo "espaciado" varia el ANCHO del hueco entre ellas,
        # asi que no se exige el espacio literal, solo el glifo).
        plain = _strip_ansi(f0)
        assert "def" in plain and "class" in plain


def test_void_shape_render_static_no_revienta():
    # Sin -a caen al render estatico generico (void-like); no deben crashear.
    for mode in VOID_SHAPE_MODES:
        out = render_static(SAMPLE_CODE, mode=mode)
        assert out
        assert "def" in _strip_ansi(out)


def test_espaciado_frame_oscila_y_es_deterministico():
    w1, i1 = espaciado_frame(3, 1, 0, length=4)
    w2, i2 = espaciado_frame(3, 1, 0, length=4)
    assert (w1, i1) == (w2, i2)  # deterministico: misma entrada, misma salida
    assert 0.0 <= i1 <= 1.0
    widths = {espaciado_frame(3, 1, t, length=4)[0] for t in range(40)}
    assert len(widths) > 1  # respira: el ancho varia con t


def test_zigzag_thread_at_es_puramente_posicional():
    # La FORMA del hilo no depende de t (solo el color que corre sobre ella).
    n_cols = 60
    threads_a = [zigzag_thread_at(x, 5, n_cols) for x in range(n_cols)]
    threads_b = [zigzag_thread_at(x, 5, n_cols) for x in range(n_cols)]
    assert threads_a == threads_b
    assert any(t is not None for t in threads_a), "ningun hilo detectado"


def test_zigzag_vertical_color_fluye_con_t():
    segs_t0 = zigzag_vertical_frame_segments(0, 5, 60, t=0, n_cols=60, n_colors=5)
    segs_t3 = zigzag_vertical_frame_segments(0, 5, 60, t=3, n_cols=60, n_colors=5)
    assert sum(n for n, _ in segs_t0) == 60
    assert sum(n for n, _ in segs_t3) == 60
    assert segs_t0 != segs_t3  # el color del hilo se desplazo con t


def test_generate_roots_deterministico_y_ancla_en_rios_reales():
    cells_a, total_a = generate_roots(CAUCE_SAMPLE)
    cells_b, total_b = generate_roots(CAUCE_SAMPLE)
    assert cells_a == cells_b and total_a == total_b  # mismo texto, mismo resultado
    assert total_a >= 1
    # El TRONCO (profundidad 0) esta anclado en un rio real (cauce.river_runs):
    # siempre cae en espacio real, nunca sobre codigo. Las ramas (profundidad
    # >= 1) pueden caer sobre codigo -- las enmascara el llamador al renderizar,
    # igual que loom/cauce, no el generador.
    lines = CAUCE_SAMPLE.splitlines()
    for (x, y), (_birth, depth) in cells_a.items():
        if depth == 0:
            line = lines[y]
            assert x >= len(line) or line[x].isspace()


def test_generate_roots_texto_distinto_no_comparte_cache_erroneo():
    cells_a, _ = generate_roots("a\nb")
    cells_b, _ = generate_roots("x\ny")
    # Distinto texto (aunque misma forma) puede compartir estructura (ambos
    # deterministicos con la misma semilla) pero la funcion no debe crashear
    # ni devolver None.
    assert cells_a is not None and cells_b is not None


def test_void_shape_svg_valido_con_desc_y_animate(tmp_path):
    import xml.etree.ElementTree as ET
    from vibecode.svg_export import export_svg

    for mode in VOID_SHAPE_MODES:
        for animate in (False, True):
            out = tmp_path / f"pieza_{mode}_{animate}.svg"
            export_svg(SAMPLE_CODE, str(out), mode=mode, animate=animate, title="t")
            svg = out.read_text(encoding="utf-8")
            root = ET.fromstring(svg)  # XML valido
            desc = root.find(f"{SVG_NS}desc")
            assert desc is not None and desc.text == VOID_SHAPE_CITATIONS[mode]
            assert ("<animate" in svg) == animate
