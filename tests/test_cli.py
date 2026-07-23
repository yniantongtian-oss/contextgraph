from pathlib import Path

from typer.testing import CliRunner

from contextgraph.cli import app

runner = CliRunner()


def test_scan_command(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def hello(): return 'world'", encoding="utf-8")
    output = tmp_path / "stats.json"

    result = runner.invoke(app, ["scan", str(tmp_path), "--output", str(output)])

    assert result.exit_code == 0, result.output
    assert "ContextGraph scan" in result.output
    assert output.exists()


def test_query_command(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def authenticate(): return True", encoding="utf-8")

    result = runner.invoke(
        app,
        ["query", "authenticate", "--project", str(tmp_path), "--budget", "100"],
    )

    assert result.exit_code == 0, result.output
    assert "authenticate" in result.output
