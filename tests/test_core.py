from pathlib import Path

import pytest

from contextgraph import CodeContextGraph


def _write_project(root: Path) -> None:
    (root / "auth.py").write_text(
        """
class AuthService:
    def login(self, username: str) -> str:
        return build_token(username)


def build_token(username: str) -> str:
    return f"token:{username}"
""".strip(),
        encoding="utf-8",
    )
    (root / "main.py").write_text(
        """
from auth import AuthService


def run() -> str:
    return AuthService().login("demo")
""".strip(),
        encoding="utf-8",
    )


def test_load_and_build_graph_indexes_symbols_and_calls(tmp_path: Path) -> None:
    _write_project(tmp_path)
    graph = CodeContextGraph()

    assert graph.load_project(tmp_path) == 2
    graph.build_graph()

    stats = graph.get_graph_stats()
    assert stats["files_loaded"] == 2
    assert stats["node_types"]["class"] == 1
    assert stats["node_types"]["method"] == 1
    assert stats["node_types"]["function"] == 2

    login_node = "symbol:auth.py::AuthService.login"
    token_node = "symbol:auth.py::build_token"
    assert graph.graph.has_edge(login_node, token_node)
    assert graph.graph.edges[login_node, token_node]["relation"] == "calls"


def test_query_returns_source_and_respects_budget(tmp_path: Path) -> None:
    _write_project(tmp_path)
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()

    result = graph.query_context("login authentication", max_tokens=100)

    assert "AuthService.login" in result["context"]
    assert "auth.py" in result["relevant_files"]
    assert result["estimated_tokens"] <= 100
    assert result["scores"]


def test_hidden_and_dependency_directories_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "visible.py").write_text("def visible(): return True", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("def secret(): return True", encoding="utf-8")
    dependencies = tmp_path / "node_modules"
    dependencies.mkdir()
    (dependencies / "vendor.py").write_text("def vendor(): return True", encoding="utf-8")

    graph = CodeContextGraph()
    graph.load_project(tmp_path)

    assert set(graph.files) == {"visible.py"}


def test_invalid_project_path_is_rejected(tmp_path: Path) -> None:
    graph = CodeContextGraph()
    with pytest.raises(FileNotFoundError):
        graph.load_project(tmp_path / "missing")


def test_invalid_query_inputs_are_rejected(tmp_path: Path) -> None:
    _write_project(tmp_path)
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()

    with pytest.raises(ValueError, match="max_tokens"):
        graph.query_context("login", max_tokens=0)
    with pytest.raises(ValueError, match="searchable term"):
        graph.query_context("--")


def test_nested_and_async_symbols_and_relative_imports(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "util.py").write_text(
        """
async def fetch(url: str) -> str:
    return url


def helper() -> int:
    def inner() -> int:
        return 1
    return inner()
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "pkg" / "app.py").write_text(
        """
from .util import fetch, helper


async def main() -> str:
    helper()
    return await fetch("x")
""".strip(),
        encoding="utf-8",
    )

    graph = CodeContextGraph()
    assert graph.load_project(tmp_path) >= 2
    graph.build_graph()
    stats = graph.get_graph_stats()
    kinds = stats["node_types"]
    assert kinds.get("function", 0) + kinds.get("method", 0) >= 3
    # nested function should be indexed when present
    node_names = [data.get("name") for _, data in graph.graph.nodes(data=True)]
    assert "fetch" in node_names
    assert "helper" in node_names


def test_empty_project_query_is_safe(tmp_path: Path) -> None:
    graph = CodeContextGraph()
    assert graph.load_project(tmp_path) == 0
    graph.build_graph()
    result = graph.query_context("anything", max_tokens=50)
    assert result["estimated_tokens"] <= 50
    assert isinstance(result["relevant_files"], list)


def test_malformed_python_is_skipped_or_tolerated(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def broken(\n", encoding="utf-8")
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    # At least the valid file should contribute a symbol.
    names = [data.get("name") for _, data in graph.graph.nodes(data=True)]
    assert "ok" in names
