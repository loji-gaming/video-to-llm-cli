from __future__ import annotations

import json

from typer.testing import CliRunner

from video_to_llm.cli import app


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "analyze" in result.output
    assert "stream" in result.output


def test_cli_short_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["-h"])

    assert result.exit_code == 0
    assert "analyze" in result.output


def test_cli_help_llm() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help-llm"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema"] == "video-to-llm/help-v1"
    assert payload["program"] == "video-to-llm"
    assert "analyze" in payload["commands"]
    assert "stream" in payload["commands"]
