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


def test_bundle_command_exports_structured_context(tmp_path: Path) -> None:
    import json

    (tmp_path / "service.py").write_text(
        "def authorize(request):\n    return bool(request)\n",
        encoding="utf-8",
    )
    output = tmp_path / "result" / "source-bundle.json"
    result = runner.invoke(
        app,
        [
            "bundle",
            "authorize",
            "--project",
            str(tmp_path),
            "--max-tokens",
            "300",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["task"] == "authorize"
    assert "authorize" in document["context"]
    assert isinstance(document["relevant_files"], list)
    assert document["estimated_tokens"] >= 0
