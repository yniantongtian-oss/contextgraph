import json
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


def test_pack_command_exports_ranked_budget(tmp_path: Path) -> None:
    (tmp_path / "billing.py").write_text(
        "class BillingService:\n    def total(self):\n        return 1\n",
        encoding="utf-8",
    )
    output = tmp_path / "pack.json"
    result = runner.invoke(
        app,
        [
            "pack",
            "billing total",
            "--project",
            str(tmp_path),
            "--budget",
            "300",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["budget"] == 300
    assert document["estimated_tokens"] <= 300
    assert document["items"]
    scores = [item["score"] for item in document["items"]]
    assert scores == sorted(scores, reverse=True)
    assert document["items"][0]["rank"] == 1
    assert "billing.py" in document["relevant_files"]
    assert document["context"].count("def total") == 1


def test_pack_stdout_is_json(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def hello(): return 1\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["pack", "hello", "--project", str(tmp_path), "--budget", "100"],
    )
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document["budget"] == 100
    assert document["estimated_tokens"] <= 100
    assert "def hello" in document["context"]


def test_pack_command_rejects_nonpositive_budget(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def hello(): return 1\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["pack", "hello", "--project", str(tmp_path), "--budget", "0"],
    )
    assert result.exit_code != 0


def test_scan_surfaces_parse_errors(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def (\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "bad.py" in result.output


def test_help_lists_pack_and_mcp() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    assert "pack" in result.output
    assert "mcp" in result.output


def test_load_mcp_main_points_at_server() -> None:
    from contextgraph.cli import _load_mcp_main
    from contextgraph.mcp_server import main

    assert _load_mcp_main() is main


def test_mcp_command_starts_server(monkeypatch) -> None:
    import contextgraph.cli as cli

    started: dict[str, bool] = {}
    monkeypatch.setattr(cli, "_load_mcp_main", lambda: lambda: started.setdefault("ok", True))
    result = runner.invoke(app, ["mcp"])
    assert result.exit_code == 0, result.output
    assert started["ok"] is True


def test_mcp_command_reports_missing_extra(monkeypatch) -> None:
    import contextgraph.cli as cli

    def missing():
        raise ImportError("mcp")

    monkeypatch.setattr(cli, "_load_mcp_main", missing)
    result = runner.invoke(app, ["mcp"])
    assert result.exit_code == 2, result.output
    assert "contextgraph-ai[mcp]" in result.output


def test_query_prints_bracketed_text_literally(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def authenticate(): return True\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["query", "authenticate [token]", "--project", str(tmp_path), "--budget", "80"],
    )
    assert result.exit_code == 0, result.output
    assert "authenticate [token]" in result.output
