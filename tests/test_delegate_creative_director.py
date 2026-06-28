from typer.testing import CliRunner

from flujo.cli import app
from flujo.web.hub import HubRequestHandler


runner = CliRunner()


def test_delegate_creative_director_prompt_includes_strategy_and_review():
    result = runner.invoke(app, ["delegate", "creative-director", "Pulir la identidad visual del hub para un lanzamiento premium"])

    assert result.exit_code == 0, result.output
    assert "Creative Director" in result.output
    assert "Estrategia de lanzamiento" in result.output
    assert "revisar outputs" in result.output.lower()


def test_hub_delegate_handler_supports_creative_director_role():
    handler = HubRequestHandler.__new__(HubRequestHandler)
    handler.root = None
    result = handler._handle_delegate({"role_id": "creative-director", "task": "Mejorar la narrativa visual"})

    assert result["role"]["id"] == "creative-director"
    assert "Creative Director" in result["full_prompt"]
    assert "Estrategia de lanzamiento" in result["full_prompt"]
