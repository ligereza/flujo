"""Tests estáticos del runner seguro de airdrops."""
from pathlib import Path


def test_runner_no_invoca_bash_para_apply_checkpoint():
    source = Path("scripts/run_airdrop_checks.py").read_text(encoding="utf-8")
    assert '["bash", "scripts/apply_airdrop.sh"' not in source
    assert '["bash", "scripts/checkpoint.sh"' not in source
    assert "scan_airdrop" in source
    assert "apply_airdrop" in source
    assert "run_auto_checkpoint" in source


def test_runner_documenta_logs_de_error():
    source = Path("scripts/run_airdrop_checks.py").read_text(encoding="utf-8")
    assert "_logs" in source
    assert "airdrop_error_" in source


def test_runner_no_prioriza_scripts_sobre_src():
    source = Path("scripts/run_airdrop_checks.py").read_text(encoding="utf-8")
    assert 'sys.path.insert(0, str(ROOT / "scripts"))' not in source
    assert "_ensure_src_first" in source


def test_runner_carga_flujo_airdrop_aunque_scripts_este_en_path(monkeypatch):
    """Regresión: scripts/flujo.py no debe sombrear al paquete src/flujo."""
    import importlib.util
    import sys

    scripts = str(Path("scripts").resolve())
    src = str(Path("src").resolve())
    original = list(sys.path)
    try:
        # Simular el caso de Windows: scripts/ aparece antes que src/.
        sys.modules.pop("flujo", None)
        sys.path[:] = [p for p in sys.path if p not in (scripts, src)]
        sys.path.insert(0, scripts)
        sys.path.insert(1, src)

        spec = importlib.util.spec_from_file_location(
            "run_airdrop_checks_under_test", Path("scripts/run_airdrop_checks.py")
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        import flujo.airdrop as airdrop

        assert hasattr(airdrop, "scan_airdrop")
        assert "src" in str(Path(airdrop.__file__).as_posix())
    finally:
        sys.path[:] = original
        sys.modules.pop("run_airdrop_checks_under_test", None)


def test_runner_expone_skip_push():
    source = Path("scripts/run_airdrop_checks.py").read_text(encoding="utf-8")
    assert "--skip-push" in source
    assert "push=not args.skip_push" in source
