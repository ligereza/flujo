from pathlib import Path

from flujo.datadrops import ingest_datadrop_reference


def test_ingest_datadrop_reference_accepts_pdf(tmp_path: Path) -> None:
    source_pdf = Path("datadrops/etiquetas/ETIQUETAS.RELIEVE.comroess.pdf")

    output_dir = ingest_datadrop_reference(source_pdf, target_dir=tmp_path / "drop")

    assert output_dir.exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / source_pdf.name).exists()
    assert (output_dir / "analysis").exists()
