from __future__ import annotations

from typer.testing import CliRunner

from video_to_llm.cli import app


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "stream" in result.output

