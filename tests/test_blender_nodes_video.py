"""Tests de sintaxis/simbolos de la variante VIDEO del grafo de nodos
(sin Blender/bpy -- bpy solo se importa dentro de funciones, igual que en
blender_nodes.py, asi que el modulo es importable en CI normal).

No prueba render real (eso exige Blender + GPU, fuera de CI); prueba que
la superficie publica que usa blender_nodes_video_seq.py existe y que el
parser de argumentos se comporta igual que el de blender_nodes.py.
"""
import pytest

from flujo.eventos import blender_nodes as bn
from flujo.eventos import blender_nodes_video as bnv
from flujo.eventos import blender_nodes_video_seq as bnvs


def test_reusa_helpers_de_blender_nodes():
    # La variante video NO redefine el grafo probado; lo importa como
    # modulo hermano (sys.path insert), asi que la identidad de modulo
    # difiere del import de paquete pero el CODIGO FUENTE es el mismo
    # archivo -- eso es lo que garantiza que no hay grafo duplicado.
    assert bnv.bn.__file__ == bn.__file__
    assert bnvs.bn.__file__ == bn.__file__
    assert bnvs.bnv.__file__ == bnv.__file__
    # mismas etiquetas de grafo (contrato de idempotencia compartido)
    assert bnv.bn.LBL_CONTENIDO == bn.LBL_CONTENIDO
    assert bnv.bn.LBL_MEZCLA == bn.LBL_MEZCLA
    assert bnv.bn.WINDOW_UV == bn.WINDOW_UV


def test_build_flyer_nodes_video_existe_y_es_funcion():
    assert callable(bnv.build_flyer_nodes_video)
    assert callable(bnv.swap_existing_movie_nodes)
    assert callable(bnv.video_mapping)
    assert callable(bnv.describe_video_layout)


def test_parse_args_video_requiere_input():
    with pytest.raises(SystemExit):
        bnv._parse_args(["blender", "--"])


def test_parse_args_video_defaults():
    args = bnv._parse_args(["blender", "--", "--input", "clip.mp4"])
    assert args["input"] == "clip.mp4"
    assert args["frame_start"] == 1
    assert args["frame_end"] is None
    assert args["fps"] is None
    assert args["layout"] == bnv.VIDEO_LAYOUT_FITWIDTH


def test_parse_args_video_frame_range_son_enteros():
    args = bnv._parse_args([
        "blender", "--", "--input", "clip.mp4",
        "--frame-start", "1", "--frame-end", "600", "--fps", "30",
    ])
    assert args["frame_start"] == 1
    assert args["frame_end"] == 600
    assert args["fps"] == 30.0


def test_parse_args_video_accepts_fitwidth_fade():
    args = bnv._parse_args([
        "blender", "--", "--input", "clip.mp4", "--layout", "fitwidth_fade",
    ])
    assert args["layout"] == "fitwidth_fade"


def test_parse_args_seq_requiere_input_y_out_dir():
    with pytest.raises(SystemExit):
        bnvs._parse_args(["blender", "--", "--input", "clip.mp4"])


def test_parse_args_seq_defaults():
    args = bnvs._parse_args([
        "blender", "--", "--input", "clip.mp4", "--out-dir", "frames/",
    ])
    assert args["input"] == "clip.mp4"
    assert args["out_dir"] == "frames/"
    assert args["frame_start"] == 1
    assert args["min_size"] == 20000
    assert args["persistent_data"] is True


def test_parse_args_seq_accepts_layout_and_issue_flow():
    args = bnvs._parse_args([
        "blender", "--", "--input", "clip.mp4", "--out-dir", "frames/",
        "--layout", "fitwidth_fade", "--issue-flow", "video_other_aspect",
    ])
    assert args["layout"] == "fitwidth_fade"
    assert args["issue_flow"] == "video_other_aspect"


def test_parse_args_seq_can_disable_persistent_data():
    args = bnvs._parse_args([
        "blender", "--", "--input", "clip.mp4", "--out-dir", "frames/",
        "--no-persistent-data",
    ])
    assert args["persistent_data"] is False
