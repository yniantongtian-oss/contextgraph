from pathlib import Path

import pytest

from contextgraph import CodeContextGraph


def test_empty_directory_exclusions_are_honored(tmp_path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "generated.py").write_text("def generated(): pass\n")
    graph = CodeContextGraph(excluded_dirs=[])
    assert graph.load_project(tmp_path) == 1


def test_unrelated_query_returns_no_source(tmp_path):
    (tmp_path / "code.py").write_text("def authenticate():\n    return True\n")
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    assert graph.query_context("quasar nebula")["relevant_nodes"] == []


def test_unicode_symbols_are_searchable(tmp_path):
    (tmp_path / "code.py").write_text("def 校验账户():\n    return True\n", encoding="utf-8")
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    assert "校验账户" in graph.query_context("校验账户")["context"]


def test_nested_functions_are_not_methods(tmp_path):
    (tmp_path / "code.py").write_text(
        "def outer():\n    async def inner():\n        return 1\n\n"
        "class Service:\n    def method(self):\n"
        "        def helper():\n            return 2\n"
    )
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    kinds = {
        data.get("qualname"): data["type"]
        for _, data in graph.graph.nodes(data=True)
        if "qualname" in data
    }
    assert kinds["outer.inner"] == "function"
    assert kinds["Service.method"] == "method"
    assert kinds["Service.method.helper"] == "function"


@pytest.mark.parametrize("budget", [True, 1.5])
def test_token_budget_requires_an_integer(budget):
    with pytest.raises(ValueError, match="integer"):
        CodeContextGraph().query_context("account", max_tokens=budget)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_file_limit_requires_a_positive_integer(limit):
    with pytest.raises(ValueError, match="positive integer"):
        CodeContextGraph(max_file_bytes=limit)


def test_source_links_do_not_read_external_files(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("PRIVATE_SENTINEL = 42\n")
    link = root / "link.py"
    link.write_text("PRIVATE_SENTINEL = 42\n")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == link or original(self))
    graph = CodeContextGraph()
    assert graph.load_project(root) == 0
