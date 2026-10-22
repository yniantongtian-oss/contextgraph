import json
from pathlib import Path

import anyio
import pytest
from mcp import Client

from contextgraph.mcp_server import create_server, main


def _invoke(server, name: str, arguments: dict):
    async def run():
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            result = await client.call_tool(name, arguments)
            return listed, result

    return anyio.run(run)


def test_server_exposes_build_query_and_pack(tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text(
        "def login():\n    return 'token'\n",
        encoding="utf-8",
    )
    server = create_server()
    listed, built = _invoke(server, "build_graph", {"project": str(tmp_path)})
    names = {tool.name for tool in listed.tools}
    assert names == {"build_graph", "query_context", "pack_context"}
    stats = built.structured_content
    assert stats is not None
    assert stats["files_loaded"] == 1
    assert stats["project"] == str(tmp_path.resolve())

    _listed, queried = _invoke(
        server,
        "query_context",
        {"query": "login token", "project": str(tmp_path), "budget": 200},
    )
    preview = queried.structured_content
    assert preview is not None
    assert queried.is_error is False
    assert "login" in preview["context"]
    assert preview["estimated_tokens"] <= 200

    _listed, packed = _invoke(
        server,
        "pack_context",
        {"query": "login token", "project": str(tmp_path), "budget": 200},
    )
    document = packed.structured_content
    assert document is not None
    assert document["budget"] == 200
    assert document["estimated_tokens"] <= 200
    assert document["items"][0]["rank"] == 1
    assert document["items"][0]["score"] >= document["items"][-1]["score"]
    json.dumps(document)


def test_query_reuses_index_until_rebuild(tmp_path: Path) -> None:
    source = tmp_path / "auth.py"
    source.write_text("def login():\n    return 1\n", encoding="utf-8")
    server = create_server()
    _invoke(server, "build_graph", {"project": str(tmp_path)})
    source.unlink()

    _listed, queried = _invoke(
        server,
        "query_context",
        {"query": "login", "project": str(tmp_path), "budget": 100},
    )
    assert "def login" in queried.structured_content["context"]

    _listed, rebuilt = _invoke(server, "build_graph", {"project": str(tmp_path)})
    assert rebuilt.structured_content["files_loaded"] == 0
    _listed, after = _invoke(
        server,
        "query_context",
        {"query": "login", "project": str(tmp_path), "budget": 100},
    )
    assert after.structured_content["relevant_nodes"] == []


def test_build_reports_syntax_errors(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("def (\n", encoding="utf-8")
    server = create_server()
    _listed, result = _invoke(server, "build_graph", {"project": str(tmp_path)})
    messages = result.structured_content["parse_error_messages"]
    assert any("bad.py" in message for message in messages)


def test_pack_rejects_invalid_budget(tmp_path: Path) -> None:
    (tmp_path / "auth.py").write_text("def login():\n    return 1\n", encoding="utf-8")
    server = create_server()
    _listed, result = _invoke(
        server,
        "pack_context",
        {"query": "login", "project": str(tmp_path), "budget": 0},
    )
    assert result.is_error is True


def test_missing_project_is_a_tool_error(tmp_path: Path) -> None:
    server = create_server()
    _listed, result = _invoke(
        server,
        "build_graph",
        {"project": str(tmp_path / "missing")},
    )
    assert result.is_error is True


def test_semantic_flag_reports_missing_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "auth.py").write_text("def login():\n    return 1\n", encoding="utf-8")
    monkeypatch.setattr(
        "contextgraph.mcp_server.CodeContextGraph.enable_semantic_search",
        lambda self, model_name="all-MiniLM-L6-v2": False,
    )
    server = create_server()
    _listed, result = _invoke(
        server,
        "query_context",
        {"query": "login", "project": str(tmp_path), "semantic": True},
    )
    assert result.is_error is True
    assert "semantic" in result.content[0].text.lower()


def test_main_uses_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    import contextgraph.mcp_server as mcp_server

    server = create_server()

    def run(transport: str = "stdio") -> None:
        server.transport = transport  # type: ignore[attr-defined]

    monkeypatch.setattr(server, "run", run)
    monkeypatch.setattr(mcp_server, "create_server", lambda: server)
    main()
    assert server.transport == "stdio"  # type: ignore[attr-defined]
