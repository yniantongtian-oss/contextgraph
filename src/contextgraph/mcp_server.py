"""Stdio MCP server for local, ranked code context.

The process speaks MCP on stdin and stdout. It reads source files and parses
Python with ``ast``. It does not import or execute the indexed project.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from rich.console import Console

from .core import CodeContextGraph

_INSTRUCTIONS = (
    "ContextGraph indexes a local repository into a Python code graph and "
    "returns ranked source inside a token budget. Call build_graph after the "
    "tree changes. query_context previews matches. pack_context exports the "
    "packed context. Indexing does not execute project code. Semantic search "
    "stays off unless semantic is true."
)


class _Index:
    """Reuse one in-process graph until the project path changes or a rebuild."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._graph: CodeContextGraph | None = None
        self._project: Path | None = None

    def load(self, project: str, *, rebuild: bool) -> CodeContextGraph:
        root = Path(project).expanduser().resolve()
        with self._lock:
            if not rebuild and self._graph is not None and self._project == root:
                return self._graph
            graph = CodeContextGraph(console=Console(stderr=True, quiet=True))
            try:
                graph.load_project(root)
            except (FileNotFoundError, NotADirectoryError) as exc:
                raise ToolError(str(exc)) from exc
            graph.build_graph()
            self._graph = graph
            self._project = root
            return graph


def _enable_semantic(graph: CodeContextGraph, semantic: bool) -> None:
    if not semantic or graph.semantic_enabled:
        return
    if not graph.enable_semantic_search():
        raise ToolError(
            "Semantic search is unavailable. "
            "Install it with: pip install 'contextgraph-ai[semantic]'"
        )


def _call_retrieval(
    graph: CodeContextGraph,
    action: str,
    query: str,
    budget: int,
    semantic: bool,
) -> dict[str, Any]:
    _enable_semantic(graph, semantic)
    try:
        if action == "pack":
            return graph.pack_context(query, max_tokens=budget, use_semantic=semantic)
        return graph.query_context(query, max_tokens=budget, use_semantic=semantic)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def create_server() -> MCPServer:
    """Build an MCP server that exposes graph build, query, and pack tools."""
    mcp = MCPServer("contextgraph", instructions=_INSTRUCTIONS)
    index = _Index()

    @mcp.tool()
    def build_graph(project: str = ".") -> dict[str, Any]:
        """Index a local project and return graph statistics.

        Reads and parses source under ``project``. Does not execute it. Query
        and pack reuse this index until ``build_graph`` is called again or the
        project path changes.
        """
        graph = index.load(project, rebuild=True)
        stats = graph.get_graph_stats()
        stats["project"] = str(graph.root_path) if graph.root_path is not None else ""
        return stats

    @mcp.tool()
    def query_context(
        query: str,
        project: str = ".",
        budget: int = 2000,
        semantic: bool = False,
    ) -> dict[str, Any]:
        """Rank source for a query and return context inside an approximate token budget."""
        graph = index.load(project, rebuild=False)
        result = _call_retrieval(graph, "query", query, budget, semantic)
        result["load_errors"] = list(graph.load_errors)
        result["parse_errors"] = list(graph.parse_errors)
        return result

    @mcp.tool()
    def pack_context(
        query: str,
        project: str = ".",
        budget: int = 2000,
        semantic: bool = False,
    ) -> dict[str, Any]:
        """Export ranked source that fits an approximate token budget.

        ``budget`` limits the packed context text. Each item records rank, score,
        path, and line span without repeating that source a second time.
        """
        graph = index.load(project, rebuild=False)
        return _call_retrieval(graph, "pack", query, budget, semantic)

    return mcp


def main() -> None:
    """Run the ContextGraph MCP server on stdio."""
    create_server().run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
