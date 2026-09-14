"""Tests offline para flujo.analyze.export (save_aco / save_ase).

Round-trip: cada test escribe el binario y lo vuelve a parsear con
struct segun el spec que el propio codigo implementa (ACO v1, ASE minimo),
no solo verifica que el archivo existe.
"""

from pathlib import Path
import struct

import flujo.paths  # noqa: F401
import flujo.analyze.export as export_mod


# ---------------- helpers ----------------

def _palette(colors_rgb):
    return {"colors": [{"rgb": list(rgb)} for rgb in colors_rgb]}


def _parse_aco(path: Path):
    """Parsea .aco v1 devolviendo lista de tuplas (r16,g16,b16) 0-65535."""
    data = path.read_bytes()
    version, count = struct.unpack(">HH", data[0:4])
    assert version == 1
    offset = 4
    out = []
    for _ in range(count):
        space, r, g, b, tail = struct.unpack(">HHHHH", data[offset:offset + 10])
        assert space == 0
        assert tail == 0
        out.append((r, g, b))
        offset += 10
    assert offset == len(data)
    return out


def _parse_ase(path: Path):
    """Parsea .ase minimo devolviendo lista de (name, (r,g,b) floats 0-1)."""
    data = path.read_bytes()
    assert data[0:4] == b"ASEF"
    ver_major, ver_minor = struct.unpack(">HH", data[4:8])
    assert (ver_major, ver_minor) == (1, 0)
    (num_blocks,) = struct.unpack(">I", data[8:12])
    offset = 12
    blocks = []
    for _ in range(num_blocks):
        (block_type,) = struct.unpack(">H", data[offset:offset + 2])
        assert block_type == 0x0001
        offset += 2
        (block_len,) = struct.unpack(">I", data[offset:offset + 4])
        offset += 4
        block_start = offset
        (name_len,) = struct.unpack(">H", data[offset:offset + 2])
        offset += 2
        name_bytes = data[offset:offset + (name_len - 1) * 2]
        name = name_bytes.decode("utf-16be")
        offset += (name_len - 1) * 2
        offset += 2  # null terminator (2 bytes utf-16be)
        model = data[offset:offset + 4]
        assert model == b"RGB "
        offset += 4
        r, g, b = struct.unpack(">fff", data[offset:offset + 12])
        offset += 12
        (color_type,) = struct.unpack(">H", data[offset:offset + 2])
        assert color_type == 2
        offset += 2
        assert offset - block_start == block_len
        blocks.append((name, (r, g, b)))
    assert offset == len(data)
    return blocks


# ---------------- save_aco ----------------

def test_save_aco_una_paleta_round_trip(tmp_path):
    palette = _palette([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    out_path = tmp_path / "paleta.aco"
    ok = export_mod.save_aco(palette, out_path)
    assert ok is True
    assert out_path.exists()

    colors = _parse_aco(out_path)
    assert len(colors) == 3
    assert colors[0] == (255 * 257, 0, 0)
    assert colors[1] == (0, 255 * 257, 0)
    assert colors[2] == (0, 0, 255 * 257)


def test_save_aco_un_solo_color(tmp_path):
    palette = _palette([(128, 64, 32)])
    out_path = tmp_path / "uno.aco"
    ok = export_mod.save_aco(palette, out_path)
    assert ok is True
    colors = _parse_aco(out_path)
    assert colors == [(128 * 257, 64 * 257, 32 * 257)]


def test_save_aco_muchos_colores(tmp_path):
    rgbs = [(i % 256, (i * 3) % 256, (i * 7) % 256) for i in range(50)]
    palette = _palette(rgbs)
    out_path = tmp_path / "muchos.aco"
    ok = export_mod.save_aco(palette, out_path)
    assert ok is True
    colors = _parse_aco(out_path)
    assert len(colors) == 50
    for (r, g, b), (pr, pg, pb) in zip(colors, rgbs):
        assert (r, g, b) == (pr * 257, pg * 257, pb * 257)


def test_save_aco_valores_extremos_0_y_255(tmp_path):
    palette = _palette([(0, 0, 0), (255, 255, 255)])
    out_path = tmp_path / "extremos.aco"
    ok = export_mod.save_aco(palette, out_path)
    assert ok is True
    colors = _parse_aco(out_path)
    assert colors[0] == (0, 0, 0)
    assert colors[1] == (65535, 65535, 65535)


def test_save_aco_paleta_vacia_devuelve_false_sin_archivo(tmp_path):
    out_path = tmp_path / "vacia.aco"
    ok = export_mod.save_aco({"colors": []}, out_path)
    assert ok is False
    assert not out_path.exists()


def test_save_aco_directorio_inexistente_devuelve_false(tmp_path):
    palette = _palette([(1, 2, 3)])
    out_path = tmp_path / "no_existe" / "paleta.aco"
    ok = export_mod.save_aco(palette, out_path)
    assert ok is False
    assert not out_path.exists()


# ---------------- save_ase ----------------

def test_save_ase_una_paleta_round_trip(tmp_path):
    palette = _palette([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
    out_path = tmp_path / "paleta.ase"
    ok = export_mod.save_ase(palette, out_path, name="Test")
    assert ok is True
    assert out_path.exists()

    blocks = _parse_ase(out_path)
    assert len(blocks) == 3
    names = [b[0] for b in blocks]
    assert names == ["Test 1", "Test 2", "Test 3"]

    r, g, b = blocks[0][1]
    assert abs(r - 1.0) < 1e-6 and abs(g - 0.0) < 1e-6 and abs(b - 0.0) < 1e-6


def test_save_ase_un_solo_color(tmp_path):
    palette = _palette([(51, 102, 153)])
    out_path = tmp_path / "uno.ase"
    ok = export_mod.save_ase(palette, out_path, name="Solo")
    assert ok is True
    blocks = _parse_ase(out_path)
    assert len(blocks) == 1
    name, (r, g, b) = blocks[0]
    assert name == "Solo 1"
    assert abs(r - 51 / 255.0) < 1e-6
    assert abs(g - 102 / 255.0) < 1e-6
    assert abs(b - 153 / 255.0) < 1e-6


def test_save_ase_muchos_colores(tmp_path):
    rgbs = [(i % 256, (i * 5) % 256, (i * 11) % 256) for i in range(40)]
    palette = _palette(rgbs)
    out_path = tmp_path / "muchos.ase"
    ok = export_mod.save_ase(palette, out_path)
    assert ok is True
    blocks = _parse_ase(out_path)
    assert len(blocks) == 40
    for (name, (r, g, b)), (pr, pg, pb) in zip(blocks, rgbs):
        assert abs(r - pr / 255.0) < 1e-6
        assert abs(g - pg / 255.0) < 1e-6
        assert abs(b - pb / 255.0) < 1e-6


def test_save_ase_valores_extremos_0_y_255(tmp_path):
    palette = _palette([(0, 0, 0), (255, 255, 255)])
    out_path = tmp_path / "extremos.ase"
    ok = export_mod.save_ase(palette, out_path)
    assert ok is True
    blocks = _parse_ase(out_path)
    r0, g0, b0 = blocks[0][1]
    r1, g1, b1 = blocks[1][1]
    assert (r0, g0, b0) == (0.0, 0.0, 0.0)
    assert abs(r1 - 1.0) < 1e-6 and abs(g1 - 1.0) < 1e-6 and abs(b1 - 1.0) < 1e-6


def test_save_ase_nombre_por_defecto(tmp_path):
    palette = _palette([(10, 20, 30)])
    out_path = tmp_path / "default.ase"
    ok = export_mod.save_ase(palette, out_path)
    assert ok is True
    blocks = _parse_ase(out_path)
    assert blocks[0][0] == "Flujo Palette 1"


def test_save_ase_paleta_vacia_devuelve_false_sin_archivo(tmp_path):
    out_path = tmp_path / "vacia.ase"
    ok = export_mod.save_ase({"colors": []}, out_path)
    assert ok is False
    assert not out_path.exists()


def test_save_ase_directorio_inexistente_devuelve_false(tmp_path):
    palette = _palette([(1, 2, 3)])
    out_path = tmp_path / "no_existe" / "paleta.ase"
    ok = export_mod.save_ase(palette, out_path)
    assert ok is False
    assert not out_path.exists()
