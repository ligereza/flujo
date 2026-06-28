import json
import subprocess
import sys
import zipfile
from pathlib import Path

from flujo.dashboard import ItemScore, Priority, render_html
from flujo.export.zipper import export_flyer
from flujo.flyer.import_email import extract_instagram_links as flyer_ig_links
from flujo.index import db as index_db
from flujo.intake.email_parser import parse_pedido_text
from flujo.web.hub import HubRequestHandler


def test_hub_static_resolver_rejects_traversal_and_non_public_root_files(tmp_path):
    root = tmp_path / "root"
    context = root / "context"
    svg = root / "svg"
    root.mkdir()
    context.mkdir()
    svg.mkdir()
    (context / "flujo_hub.html").write_text("hub", encoding="utf-8")
    (svg / "ok.svg").write_text("<svg></svg>", encoding="utf-8")
    (root / "pyproject.toml").write_text("secret-ish", encoding="utf-8")
    (root / "src_secret.py").write_text("secret-ish", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")

    handler = HubRequestHandler.__new__(HubRequestHandler)
    handler.root = root
    handler.context_path = context

    assert handler._resolve_static_file("flujo_hub.html") == context / "flujo_hub.html"
    assert handler._resolve_static_file("svg/ok.svg") == svg / "ok.svg"
    assert handler._resolve_static_file("pyproject.toml") is None
    assert handler._resolve_static_file("src_secret.py") is None
    assert handler._resolve_static_file("../secret.txt") is None
    assert handler._resolve_static_file("%2e%2e/secret.txt") is None
    assert handler._resolve_static_file("..\\secret.txt") is None


def test_export_zip_contains_generated_tool_scripts(tmp_path):
    project = tmp_path / "flyer"
    for sub in ("input", "analysis", "working", "ai"):
        (project / sub).mkdir(parents=True)
    (project / "manifest.json").write_text(
        json.dumps({"instagram": {"owner": "demo", "shortcode": "ABC"}}), encoding="utf-8"
    )

    zip_path = export_flyer(project)

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    assert "working/compose.jsx" in names
    assert "ai/compose_ai.jsx" in names
    assert "working/blender_setup.py" in names
    assert "LEEME.txt" in names


def test_parse_pedido_detects_non_flyer_tools():
    assert parse_pedido_text("Necesito plano para stand con 12 voluntarios")["tool"] == "plano"
    assert parse_pedido_text("cotización para evento masivo")["tool"] == "cotizaciones"
    assert parse_pedido_text("cartelera historia 1080x1920")["tipo"] == "cartelera"


def test_flyer_import_supports_user_prefixed_and_scheme_less_instagram_urls():
    links = flyer_ig_links(
        "instagram.com/user/p/ABC123/ y https://www.instagram.com/otra/reels/XYZ789/?utm=x"
    )
    assert links == [
        {"kind": "p", "code": "ABC123", "url": "https://www.instagram.com/p/ABC123"},
        {"kind": "reel", "code": "XYZ789", "url": "https://www.instagram.com/reel/XYZ789"},
    ]


def test_index_queries_initialize_schema_on_fresh_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(index_db, "repo_root", lambda: tmp_path)
    assert index_db.list_flyers() == []
    assert index_db.find_duplicates() == []


def test_render_generator_preserves_unknown_braces_in_text(tmp_path):
    cfg = {
        "project": {"slug": "braces"},
        "canvas": {"width": 200, "height": 100},
        "palette": {"ink": "#000", "cream": "#fff"},
        "background": "cream",
        "documents": [
            {
                "id": "doc",
                "title": "Doc",
                "elements": [
                    {
                        "type": "text",
                        "content": "Precio {especial}",
                        "x": 10,
                        "y": 10,
                        "size": 12,
                        "fill": "ink",
                    }
                ],
            }
        ],
    }
    config = tmp_path / "config.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "tools" / "piezas_vectoriales" / "scripts" / "generar_desde_json.py"
    proc = subprocess.run([sys.executable, str(script), str(config)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    svg = tmp_path / "salida_generada" / "01_editables_svg" / "doc_editable.svg"
    assert "Precio {especial}" in svg.read_text(encoding="utf-8")


def test_dashboard_html_escapes_dynamic_fields(tmp_path):
    item = ItemScore(
        type="job",
        path=tmp_path / "<path>",
        name="<script>alert(1)</script>",
        score=90,
        priority=Priority.ALTA,
        reason="bad <b>html</b>",
    )
    html = render_html([item])
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "bad &lt;b&gt;html&lt;/b&gt;" in html
