import json
from pathlib import Path

from flujo.export.illustrator import (
    prepare_supplement_contraportadas_for_illustrator,
    prepare_supplement_job_assets,
    prepare_svg_for_illustrator,
)


def test_prepare_svg_for_illustrator_creates_package(tmp_path: Path) -> None:
    svg_dir = tmp_path / "svg_src"
    svg_dir.mkdir()
    svg_file = svg_dir / "pieza.svg"
    svg_file.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" fill="#000"/></svg>', encoding="utf-8")

    output_dir = tmp_path / "out"
    package_dir = prepare_svg_for_illustrator(svg_file, output_dir=output_dir, project_name="demo")

    assert package_dir.exists()
    assert (package_dir / "svg" / "pieza.svg").exists()
    assert (package_dir / "import_svg.jsx").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "manifest.json").exists()


def test_prepare_supplement_contraportadas_for_illustrator_creates_package(tmp_path: Path) -> None:
    """The package carries the APPROVED contraportadas, copied, not re-rendered.

    Rewritten 2026-07-26: it used to render each piece from a second, unapproved
    base template. Now the design is the user's own .ai export and the package
    just copies it.
    """
    from flujo.export.illustrator import _contraportada_aprobada
    from flujo.comercial.suplementos_config import get_suplemento

    package_dir = prepare_supplement_contraportadas_for_illustrator(
        ["IMPULSO", "Creatina Monohidratada"],
        output_dir=tmp_path / "out",
        project_name="suplementos_rd",
    )

    assert package_dir.exists()
    assert (package_dir / "svg" / "impulso_final.svg").exists()
    assert (package_dir / "svg" / "creatina_monohidratada_final.svg").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "illustrator_artboards.jsx").exists()

    # byte-for-byte the approved piece: the export never redraws the design
    aprobada = _contraportada_aprobada(get_suplemento("IMPULSO").id)
    assert (package_dir / "svg" / "impulso_final.svg").read_bytes() == aprobada.read_bytes()

    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["type"] == "supplement_contraportadas"
    # Datadrops are private/local inputs and are not part of the standalone
    # repository. The portable manifest keeps the field but leaves it empty.
    assert manifest["datadrop_reference"]["id"] == ""


def test_prepare_supplement_job_assets_generates_flow_artifacts(tmp_path: Path) -> None:
    job_dir = tmp_path / "jobs" / "2026-06-28_test"
    job_dir.mkdir(parents=True)

    result = prepare_supplement_job_assets(
        job_dir,
        request_text="Pedido de contraportada para Impulso",
        document_size=(1800, 1200),
    )

    assert result["created"] is True
    assert (job_dir / "flows" / "contraportada.svg").exists()
    assert (job_dir / "flows" / "illustrator_package" / "2026-06-28_test" / "illustrator_artboards.jsx").exists()
    assert result["document_size"] == [1800, 1200]


def test_prepare_supplement_job_assets_dynamic_fallback_and_brief(tmp_path: Path) -> None:
    job_dir = tmp_path / "jobs" / "2026-06-28_test_fallback"
    job_dir.mkdir(parents=True)

    result = prepare_supplement_job_assets(
        job_dir,
        request_text="Pedido de contraportada para POST FIESTA. Brief: Energia ultra recargada para la noche",
    )

    assert result["created"] is True
    assert result["supplement"] == "POST FIESTA"

    svg_path = Path(result["svg_path"])
    assert svg_path.exists()
    svg_content = svg_path.read_text(encoding="utf-8")
    assert "POST" in svg_content
    assert "FIESTA" in svg_content

    # THE POINT OF THIS TEST (rewritten 2026-07-26): a free-text brief must NOT
    # reach a supplement piece. `brief` is an EVENTS concept -- it configures the
    # plano/rider text -- and supplements take their copy from the file the RD
    # manager sends, which wins over anything typed in a request. Before this,
    # the brief was painted straight into the artwork.
    assert "Energia ultra recargada para la noche" not in svg_content
