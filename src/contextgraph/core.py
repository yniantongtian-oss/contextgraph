from __future__ import annotations

import ast
import math
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import networkx as nx
from rich.console import Console

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    SEMANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional extras
    np = None
    SentenceTransformer = None
    SEMANTIC_AVAILABLE = False


SOURCE_EXTENSIONS = {
    ".py": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

DEFAULT_EXCLUDED_DIRS = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "build",
        "dist",
        "env",
        "node_modules",
        "site-packages",
        "venv",
    }
)

_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^a-zA-Z0-9]+")


def _terms(value: str) -> set[str]:
    expanded = _WORD_BOUNDARY.sub(" ", value)
    return {part.lower() for part in _NON_WORD.split(expanded) if len(part) > 1}


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


class _PythonIndexVisitor(ast.NodeVisitor):
    def __init__(self, source: str) -> None:
        self.source = source
        self.scope: list[str] = []
        self.callers: list[str] = []
        self.symbols: list[dict[str, Any]] = []
        self.imports: set[str] = set()
        self.calls: list[tuple[str | None, str]] = []

    def _visit_symbol(self, node: ast.AST, name: str, kind: str) -> None:
        qualname = ".".join([*self.scope, name])
        source_segment = ast.get_source_segment(self.source, node) or ""
        self.symbols.append(
            {
                "name": name,
                "qualname": qualname,
                "kind": kind,
                "lineno": getattr(node, "lineno", 1),
                "end_lineno": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "source": source_segment,
            }
        )
        self.scope.append(name)
        self.callers.append(qualname)
        self.generic_visit(node)
        self.callers.pop()
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._visit_symbol(node, node.name, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        kind = "method" if self.scope else "function"
        self._visit_symbol(node, node.name, kind)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        kind = "method" if self.scope else "function"
        self._visit_symbol(node, node.name, kind)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        self.imports.update(alias.name for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module:
            self.imports.add(node.module)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _call_name(node.func)
        if name:
            caller = self.callers[-1] if self.callers else None
            self.calls.append((caller, name))
        self.generic_visit(node)


class CodeContextGraph:
    """Build and query a lightweight, Python-first code relationship graph."""

    def __init__(
        self,
        *,
        console: Console | None = None,
        excluded_dirs: Iterable[str] | None = None,
        max_file_bytes: int = 1_000_000,
    ) -> None:
        self.graph = nx.DiGraph()
        self.files: dict[str, dict[str, Any]] = {}
        self.embeddings: dict[str, Any] = {}
        self.model: Any = None
        self.semantic_enabled = False
        self.console = console or Console()
        self.excluded_dirs = set(excluded_dirs or DEFAULT_EXCLUDED_DIRS)
        self.max_file_bytes = max_file_bytes
        self.root_path: Path | None = None
        self.load_errors: list[str] = []
        self.parse_errors: list[str] = []

    def load_project(
        self,
        root_path: str | Path,
        languages: Sequence[str] | None = None,
    ) -> int:
        """Load supported source files and return the number of files indexed."""
        root = Path(root_path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Project path does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Project path is not a directory: {root}")

        requested = {language.lower() for language in (languages or ["python"])}
        self.root_path = root
        self.files.clear()
        self.graph.clear()
        self.embeddings.clear()
        self.load_errors.clear()
        self.parse_errors.clear()

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            relative = file_path.relative_to(root)
            if self._is_excluded(relative):
                continue

            language = SOURCE_EXTENSIONS.get(file_path.suffix.lower())
            if not language or ("all" not in requested and language not in requested):
                continue

            try:
                if file_path.stat().st_size > self.max_file_bytes:
                    self.load_errors.append(f"Skipped oversized file: {relative.as_posix()}")
                    continue
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                self.load_errors.append(f"{relative.as_posix()}: {exc}")
                continue

            relative_path = relative.as_posix()
            self.files[relative_path] = {
                "path": file_path,
                "language": language,
                "content": content,
                "size": len(content),
                "name": file_path.name,
            }

        self.console.print(f"[green]Loaded {len(self.files)} source files from {root}[/]")
        return len(self.files)

    def _is_excluded(self, relative_path: Path) -> bool:
        return any(
            part.startswith(".") or part in self.excluded_dirs for part in relative_path.parts
        )

    @staticmethod
    def _file_node(relative_path: str) -> str:
        return f"file:{relative_path}"

    @staticmethod
    def _symbol_node(relative_path: str, qualname: str) -> str:
        return f"symbol:{relative_path}::{qualname}"

    def build_graph(self) -> int:
        """Build graph nodes and edges; return the total node count."""
        self.graph.clear()
        self.embeddings.clear()
        self.parse_errors.clear()

        visitors: dict[str, _PythonIndexVisitor] = {}
        simple_name_index: dict[str, list[str]] = defaultdict(list)
        local_name_index: dict[tuple[str, str], list[str]] = defaultdict(list)

        for relative_path, metadata in self.files.items():
            file_node = self._file_node(relative_path)
            self.graph.add_node(
                file_node,
                type="file",
                name=metadata["name"],
                path=relative_path,
                language=metadata["language"],
                source=metadata["content"],
            )

            if metadata["language"] != "python":
                continue

            try:
                tree = ast.parse(metadata["content"], filename=relative_path)
            except SyntaxError as exc:
                self.parse_errors.append(f"{relative_path}:{exc.lineno or 1}: {exc.msg}")
                continue

            visitor = _PythonIndexVisitor(metadata["content"])
            visitor.visit(tree)
            visitors[relative_path] = visitor

            for symbol in visitor.symbols:
                symbol_node = self._symbol_node(relative_path, symbol["qualname"])
                self.graph.add_node(
                    symbol_node,
                    type=symbol["kind"],
                    name=symbol["name"],
                    qualname=symbol["qualname"],
                    path=relative_path,
                    lineno=symbol["lineno"],
                    end_lineno=symbol["end_lineno"],
                    source=symbol["source"],
                    language="python",
                )
                self.graph.add_edge(file_node, symbol_node, relation="defines")
                simple_name_index[symbol["name"]].append(symbol_node)
                local_name_index[(relative_path, symbol["name"])].append(symbol_node)

            for module in sorted(visitor.imports):
                module_node = f"module:{module}"
                self.graph.add_node(module_node, type="module", name=module)
                self.graph.add_edge(file_node, module_node, relation="imports")

        for relative_path, visitor in visitors.items():
            file_node = self._file_node(relative_path)
            for caller_qualname, called_name in visitor.calls:
                caller_node = (
                    self._symbol_node(relative_path, caller_qualname)
                    if caller_qualname
                    else file_node
                )
                candidates = local_name_index.get((relative_path, called_name), [])
                if not candidates:
                    global_candidates = simple_name_index.get(called_name, [])
                    candidates = global_candidates if len(global_candidates) == 1 else []
                for target_node in candidates:
                    if caller_node != target_node:
                        self.graph.add_edge(caller_node, target_node, relation="calls")

        self.console.print(
            f"[green]Built graph with {self.graph.number_of_nodes()} nodes and "
            f"{self.graph.number_of_edges()} edges[/]"
        )
        return self.graph.number_of_nodes()

    def enable_semantic_search(self, model_name: str = "all-MiniLM-L6-v2") -> bool:
        """Load an optional local sentence-transformer model."""
        if not SEMANTIC_AVAILABLE:
            self.console.print(
                "[yellow]Semantic dependencies are not installed. "
                "Run: pip install 'contextgraph-ai[semantic]'[/]"
            )
            return False

        try:
            self.model = SentenceTransformer(model_name)
        except Exception as exc:  # pragma: no cover - model/network dependent
            self.console.print(f"[red]Failed to load semantic model: {exc}[/]")
            return False

        self.semantic_enabled = True
        self.embeddings.clear()
        self.console.print(f"[green]Semantic search enabled with {model_name}[/]")
        return True

    def _candidate_nodes(self) -> list[str]:
        return [
            node_id
            for node_id, data in self.graph.nodes(data=True)
            if data.get("type") in {"file", "function", "method", "class"}
        ]

    def _node_text(self, node_id: str) -> str:
        data = self.graph.nodes[node_id]
        return "\n".join(
            str(value)
            for value in (
                data.get("name", ""),
                data.get("qualname", ""),
                data.get("path", ""),
                data.get("source", ""),
            )
            if value
        )

    def _compute_embeddings(self, node_ids: Sequence[str]) -> None:
        if not self.semantic_enabled or self.model is None:
            return
        missing = [node_id for node_id in node_ids if node_id not in self.embeddings]
        if not missing:
            return
        texts = [self._node_text(node_id)[:4_000] for node_id in missing]
        vectors = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        self.embeddings.update(dict(zip(missing, vectors, strict=True)))

    def _get_relevance_score(
        self,
        node_id: str,
        query: str,
        query_terms: set[str],
        query_embedding: Any | None = None,
    ) -> float:
        data = self.graph.nodes[node_id]
        name_terms = _terms(str(data.get("name", "")))
        qualname_terms = _terms(str(data.get("qualname", "")))
        path_terms = _terms(str(data.get("path", "")))
        source = str(data.get("source", ""))
        source_lower = source.lower()

        name_overlap = len(query_terms & (name_terms | qualname_terms))
        path_overlap = len(query_terms & path_terms)
        content_overlap = sum(1 for term in query_terms if term in source_lower)

        score = 0.0
        score += 3.0 * name_overlap / max(len(query_terms), 1)
        score += 1.2 * path_overlap / max(len(query_terms), 1)
        score += min(content_overlap, 6) * 0.25
        if query.lower().strip() and query.lower().strip() in source_lower:
            score += 1.0

        if query_embedding is not None and np is not None and node_id in self.embeddings:
            node_embedding = self.embeddings[node_id]
            denominator = float(np.linalg.norm(query_embedding) * np.linalg.norm(node_embedding))
            if denominator > 0:
                similarity = float(np.dot(query_embedding, node_embedding) / denominator)
                score += max(similarity, 0.0) * 2.5

        degree = self.graph.degree(node_id)
        score += min(math.log1p(degree) / 5.0, 0.5)
        return score

    def _render_node(self, node_id: str) -> tuple[str, str | None]:
        data = self.graph.nodes[node_id]
        node_type = str(data.get("type", "node"))
        path = data.get("path")
        source = str(data.get("source", "")).strip()
        if node_type == "file":
            header = f"# File: {path}\n"
        else:
            qualname = data.get("qualname", data.get("name", node_id))
            header = f"# {node_type.title()}: {qualname} ({path}:{data.get('lineno', 1)})\n"
        return header + source + "\n", str(path) if path else None

    def query_context(
        self,
        query: str,
        max_tokens: int = 2_000,
        include_graph_summary: bool = True,
        use_semantic: bool = False,
    ) -> dict[str, Any]:
        """Return scored source context constrained by an approximate token budget."""
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        query_terms = _terms(query)
        if not query_terms:
            raise ValueError("query must contain at least one searchable term")

        candidate_nodes = self._candidate_nodes()
        if not candidate_nodes:
            return {
                "context": "",
                "relevant_nodes": [],
                "relevant_files": [],
                "scores": {},
                "estimated_tokens": 0,
                "total_candidates": 0,
                "graph_summary": "Graph contains no queryable source nodes.",
            }

        query_embedding = None
        if use_semantic and self.semantic_enabled and self.model is not None:
            self._compute_embeddings(candidate_nodes)
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]

        scored_nodes = [
            (
                node_id,
                self._get_relevance_score(
                    node_id,
                    query,
                    query_terms,
                    query_embedding,
                ),
            )
            for node_id in candidate_nodes
        ]
        scored_nodes = [item for item in scored_nodes if item[1] > 0]
        scored_nodes.sort(
            key=lambda item: (
                item[1],
                self.graph.nodes[item[0]].get("type") != "file",
            ),
            reverse=True,
        )

        char_limit = max_tokens * 4
        remaining = char_limit
        selected: list[tuple[str, float, str]] = []
        selected_files: list[str] = []
        symbol_paths: set[str] = set()

        for node_id, score in scored_nodes:
            data = self.graph.nodes[node_id]
            path = str(data.get("path", ""))
            if data.get("type") == "file" and path in symbol_paths:
                continue

            block, block_path = self._render_node(node_id)
            if remaining < 80:
                break
            if len(block) > remaining:
                marker = "\n... [truncated to token budget]\n"
                block = block[: max(0, remaining - len(marker))].rstrip() + marker
            if not block.strip():
                continue

            selected.append((node_id, score, block))
            remaining -= len(block)
            if block_path and block_path not in selected_files:
                selected_files.append(block_path)
            if data.get("type") != "file" and path:
                symbol_paths.add(path)

        context = "\n".join(block for _, _, block in selected).strip()
        result: dict[str, Any] = {
            "context": context,
            "relevant_nodes": [node_id for node_id, _, _ in selected],
            "relevant_files": selected_files,
            "scores": {node_id: round(score, 4) for node_id, score, _ in selected},
            "estimated_tokens": math.ceil(len(context) / 4),
            "total_candidates": len(scored_nodes),
        }
        if include_graph_summary:
            result["graph_summary"] = (
                f"Graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges; selected "
                f"{len(selected)} of {len(scored_nodes)} scored candidates."
            )
        return result

    def get_graph_stats(self) -> dict[str, Any]:
        type_counts: dict[str, int] = defaultdict(int)
        for _, data in self.graph.nodes(data=True):
            type_counts[str(data.get("type", "unknown"))] += 1
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "files_loaded": len(self.files),
            "node_types": dict(sorted(type_counts.items())),
            "load_errors": len(self.load_errors),
            "parse_errors": len(self.parse_errors),
            "semantic_enabled": self.semantic_enabled,
        }
