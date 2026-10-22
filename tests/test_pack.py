from pathlib import Path

import pytest

from contextgraph import CodeContextGraph


def _index(tmp_path: Path, source: str, name: str = "code.py") -> CodeContextGraph:
    (tmp_path / name).write_text(source.strip() + "\n", encoding="utf-8")
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    return graph


def _call_edges(graph: CodeContextGraph) -> set[tuple[str, str]]:
    return {
        (source, target)
        for source, target, data in graph.graph.edges(data=True)
        if data.get("relation") == "calls"
    }


def test_pack_ranks_and_stays_inside_budget(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
def billing_total():
    return 1


def unrelated():
    return 0
""",
    )
    packed = graph.pack_context("billing total", max_tokens=80)
    assert packed["budget"] == 80
    assert packed["estimated_tokens"] <= 80
    assert packed["items"]
    assert packed["items"][0]["id"] == "symbol:code.py::billing_total"
    assert [item["rank"] for item in packed["items"]] == list(range(1, len(packed["items"]) + 1))
    scores = [item["score"] for item in packed["items"]]
    assert scores == sorted(scores, reverse=True)


def test_pack_does_not_duplicate_nested_source(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
class AuthService:
    def login(self):
        return True
""",
        name="auth.py",
    )
    packed = graph.pack_context("AuthService login", max_tokens=400)
    assert packed["context"].count("def login") == 1
    assert packed["estimated_tokens"] <= 400


def test_pack_skips_oversized_file_when_symbol_fits(tmp_path: Path) -> None:
    padding = "note = 'accounting'\n" * 80
    graph = _index(
        tmp_path,
        padding
        + """
def accounting_total():
    return 1
""",
        name="accounting.py",
    )
    packed = graph.pack_context("accounting", max_tokens=80)
    ids = [item["id"] for item in packed["items"]]
    assert "symbol:accounting.py::accounting_total" in ids
    assert "file:accounting.py" not in ids
    assert packed["estimated_tokens"] <= 80
    assert packed["context"].count("def accounting_total") == 1


def test_pack_truncates_a_file_that_is_the_only_hit(tmp_path: Path) -> None:
    graph = _index(tmp_path, "value = 1\n" * 80, name="accounting.py")
    packed = graph.pack_context("accounting", max_tokens=40)
    assert packed["items"]
    assert packed["items"][0]["id"] == "file:accounting.py"
    assert packed["items"][0]["truncated"] is True
    assert "truncated to token budget" in packed["context"]
    assert packed["estimated_tokens"] <= 40


@pytest.mark.parametrize("budget", [1, 20, 50, 80])
def test_pack_never_exceeds_budget(tmp_path: Path, budget: int) -> None:
    graph = _index(
        tmp_path,
        """
def billing_total():
    return "accounting"


def accounting_note():
    return "billing"
""",
        name="accounting.py",
    )
    packed = graph.pack_context("billing accounting", max_tokens=budget)
    assert packed["estimated_tokens"] <= budget


def test_short_later_hit_uses_remaining_budget(tmp_path: Path) -> None:
    filler = "A" * 60
    graph = _index(
        tmp_path,
        f'''
def alpha():
    """{filler}"""
    return 1


def beta():
    return 2
''',
        name="mod.py",
    )
    wide = graph.pack_context("alpha beta", max_tokens=2000)
    assert "def alpha" in wide["context"]
    assert "def beta" in wide["context"]
    first_tokens = wide["items"][0]["estimated_tokens"]
    tight = graph.pack_context("alpha beta", max_tokens=first_tokens + 18)
    assert "def beta" in tight["context"]
    assert tight["estimated_tokens"] <= first_tokens + 18


def test_attribute_call_prefers_enclosing_method(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
def save():
    return "function"


class Store:
    def save(self):
        return "method"

    def run(self):
        return self.save()
""",
    )
    assert _call_edges(graph) == {("symbol:code.py::Store.run", "symbol:code.py::Store.save")}


def test_bare_call_prefers_module_function_over_same_named_method(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
def save():
    return "function"


class Store:
    def save(self):
        return "method"

    def run(self):
        return save()
""",
    )
    assert _call_edges(graph) == {("symbol:code.py::Store.run", "symbol:code.py::save")}


def test_ambiguous_attribute_call_is_unresolved(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
class A:
    def save(self):
        return 1


class B:
    def save(self):
        return 2


def run(obj):
    return obj.save()
""",
    )
    assert _call_edges(graph) == set()


def test_nested_call_resolves_to_inner_function(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
def outer():
    def inner():
        return 1
    return inner()
""",
    )
    assert _call_edges(graph) == {("symbol:code.py::outer", "symbol:code.py::outer.inner")}


def test_direct_recursion_does_not_add_a_self_edge(tmp_path: Path) -> None:
    graph = _index(
        tmp_path,
        """
def recur():
    return recur()
""",
    )
    assert _call_edges(graph) == set()


def test_ambiguous_cross_file_call_is_unresolved(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def save():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def save():\n    return 2\n", encoding="utf-8")
    (tmp_path / "c.py").write_text("def run():\n    return save()\n", encoding="utf-8")
    graph = CodeContextGraph()
    graph.load_project(tmp_path)
    graph.build_graph()
    assert _call_edges(graph) == set()


def test_oversized_file_records_a_load_error(tmp_path: Path) -> None:
    (tmp_path / "big.py").write_text("def big():\n    return 1\n", encoding="utf-8")
    graph = CodeContextGraph(max_file_bytes=1)
    assert graph.load_project(tmp_path) == 0
    assert any("oversized" in message for message in graph.load_errors)
    assert graph.get_graph_stats()["load_error_messages"] == graph.load_errors


def test_pack_rejects_invalid_budget_and_query(tmp_path: Path) -> None:
    graph = _index(tmp_path, "def account():\n    return 1")
    with pytest.raises(ValueError, match="integer"):
        graph.pack_context("account", max_tokens=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="searchable term"):
        graph.pack_context("--")
