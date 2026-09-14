from typer.testing import CliRunner

from flujo.cli import app


runner = CliRunner()


def test_delegate_creative_director_prompt_includes_strategy_and_review():
    result = runner.invoke(app, ["delegate", "creative-director", "Pulir la identidad visual del hub para un lanzamiento premium"])

    assert result.exit_code == 0, result.output
    assert "Creative Director" in result.output
    assert "Estrategia de lanzamiento" in result.output
    output = result.output.lower()
    assert "revisar outputs" in output or "revisa los outputs" in output
