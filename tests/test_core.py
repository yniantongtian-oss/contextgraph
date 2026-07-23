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
