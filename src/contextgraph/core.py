import ast
 import os
 from pathlib import Path
 from typing import List, Dict, Any, Optional, Tuple
 import networkx as nx
 from rich.console import Console
 import math

 try:
     from sentence_transformers import SentenceTransformer
     import numpy as np
     SEMANTIC_AVAILABLE = True
 except ImportError:
     SEMANTIC_AVAILABLE = False
     SentenceTransformer = None
     np = None

 console = Console()


 class CodeContextGraph:
     """Main class for building and querying code intelligence graphs."""
 
     def __init__(self):
         self.graph = nx.DiGraph()
         self.files: Dict[str, Dict] = {}
         self.embeddings: Dict[str, Any] = {}  # node_id -> embedding
         self.model = None
         self.semantic_enabled = False
         self.console = Console()
 
     def load_project(self, root_path: str, languages: Optional[List[str]] = None):
         """Scan and load source files from a project directory."""
         if languages is None:
             languages = ["python"]
 
         root = Path(root_path).resolve()
         self.root_path = root
         self.files.clear()
         self.graph.clear()
         self.embeddings.clear()
 
         extensions = {
             ".py": "python",
             ".c": "c", ".h": "c",
             ".cpp": "cpp", ".hpp": "cpp",
             ".js": "javascript",
             ".ts": "typescript",
         }
 
         for ext, lang in extensions.items():
             if lang in languages or "all" in languages:
                 for file_path in root.rglob(f"*{ext}"):
                     if any(part.startswith(".") for part in file_path.parts if part != root.name):
                         continue
                     try:
                         with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                             content = f.read()
                         self.files[str(file_path)] = {
                             "language": lang,
                             "content": content,
                             "size": len(content),
                             "name": file_path.name
                         }
                     except Exception:
                         pass
 
         self.console.print(f"[green]Loaded {len(self.files)} files from {root}")
 
     def build_graph(self):
         """Build the code relationship graph (Python-focused for MVP)."""
         self.graph.clear()
         self.embeddings.clear()
 
         for file_path, meta in self.files.items():
             if meta["language"] != "python":
                 continue
 
             try:
                 tree = ast.parse(meta["content"], filename=file_path)
             except SyntaxError:
                 continue
 
             self.graph.add_node(file_path, type="file", language="python", name=meta["name"])
 
             for node in ast.walk(tree):
                 if isinstance(node, ast.FunctionDef):
                     func_name = node.name
                     node_id = f"{file_path}::{func_name}"
                     self.graph.add_node(
                         node_id,
                         type="function",
                         name=func_name,
                         file=file_path,
                         lineno=node.lineno
                     )
                     self.graph.add_edge(file_path, node_id, relation="defines")
 
                     # Basic call detection
                     for subnode in ast.walk(node):
                         if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name):
                             called = subnode.func.id
                             called_id = f"{file_path}::{called}"
                             if self.graph.has_node(called_id):
                                 self.graph.add_edge(node_id, called_id, relation="calls")
 
                 elif isinstance(node, (ast.Import, ast.ImportFrom)):
                     for alias in getattr(node, 'names', []):
                         mod = alias.name if hasattr(alias, 'name') else getattr(node, 'module', '')
                         if mod:
                             self.graph.add_edge(file_path, mod, relation="imports")
 
         self.console.print(f"[green]Built graph with {self.graph.number_of_nodes()} nodes")
 
     def _get_relevance_score(self, node_id: str, query: str, query_embedding: Optional[Any] = None) -> float:
         """Calculate relevance score for a node."""
         data = self.graph.nodes.get(node_id, {})
         name = data.get("name", "").lower()
         query_lower = query.lower()
 
         # Keyword score
         keyword_score = 0.0
         query_words = set(query_lower.split())
         name_words = set(name.split("_") + name.split())
         common = len(query_words & name_words)
         if common > 0:
             keyword_score = common / max(len(query_words), 1) * 2.0
 
         # Content keyword bonus (simple)
         if node_id in self.files:
             content_lower = self.files[node_id]["content"].lower()[:2000]
             content_matches = sum(1 for w in query_words if w in content_lower)
             keyword_score += content_matches * 0.1
 
         # Semantic score (if available)
         semantic_score = 0.0
         if self.semantic_enabled and query_embedding is not None and node_id in self.embeddings:
             node_emb = self.embeddings[node_id]
             # cosine similarity
             sim = np.dot(query_embedding, node_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(node_emb) + 1e-8)
             semantic_score = float(sim) * 3.0  # weight semantic higher when enabled
 
         # Graph importance (degree)
         degree = self.graph.degree(node_id) if self.graph.has_node(node_id) else 0
         importance = min(degree / 10.0, 1.0) * 0.5
 
         total_score = keyword_score + semantic_score + importance
         return max(total_score, 0.0)
 
     def enable_semantic_search(self, model_name: str = "all-MiniLM-L6-v2"):
         """Enable semantic search using sentence-transformers (local)."""
         if not SEMANTIC_AVAILABLE:
             self.console.print("[yellow]sentence-transformers not installed. Run: pip install 'contextgraph[semantic]'[/]")
             return False
 
         try:
             self.model = SentenceTransformer(model_name)
             self.semantic_enabled = True
             self.console.print(f"[green]Semantic search enabled with model: {model_name}")
             return True
         except Exception as e:
             self.console.print(f"[red]Failed to load model: {e}")
             return False
 
     def _compute_embeddings(self):
         """Compute embeddings for all function and file nodes."""
         if not self.semantic_enabled or self.model is None:
             return
 
         texts = []
         node_ids = []
 
         for node_id, data in self.graph.nodes(data=True):
             if data.get("type") in ["function", "file"]:
                 if node_id in self.files:
                     text = self.files[node_id]["content"][:1500]
                 else:
                     text = data.get("name", "")
                 texts.append(text)
                 node_ids.append(node_id)
 
         if not texts:
             return
 
         embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
         for nid, emb in zip(node_ids, embeddings):
             self.embeddings[nid] = emb
 
         self.console.print(f"[green]Computed embeddings for {len(self.embeddings)} nodes")
 
     def query_context(
         self,
         query: str,
         max_tokens: int = 2000,
         include_graph_summary: bool = True,
         use_semantic: bool = True
     ) -> Dict[str, Any]:
         """Retrieve relevant context. Improved scoring + optional semantic search."""
         if self.graph.number_of_nodes() == 0:
             return {"context": "", "relevant_nodes": [], "estimated_tokens": 0}
 
         query_embedding = None
         if use_semantic and self.semantic_enabled:
             if not self.embeddings:
                 self._compute_embeddings()
             if self.model is not None:
                 query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
 
         # Score all candidate nodes
         scored_nodes: List[Tuple[str, float]] = []
         for node_id in self.graph.nodes():
             score = self._get_relevance_score(node_id, query, query_embedding)
             if score > 0:
                 scored_nodes.append((node_id, score))
 
         # Sort by score descending
         scored_nodes.sort(key=lambda x: x[1], reverse=True)
 
         # Select top nodes within token budget
         selected = []
         total_chars = 0
         char_limit = max_tokens * 3.5  # conservative char-to-token ratio
 
         for node_id, score in scored_nodes:
             if node_id in self.files:
                 content = self.files[node_id]["content"]
                 # Truncate long files intelligently
                 if len(content) > 800:
                     content = content[:600] + "\n... [truncated]"
                 addition = f"# File: {Path(node_id).name}\n{content}\n"
             else:
                 addition = f"# {self.graph.nodes[node_id].get('type', 'node').title()}: {node_id}\n"
 
             if total_chars + len(addition) > char_limit:
                 break
             selected.append((node_id, score, addition))
             total_chars += len(addition)
 
         context_str = "\n\n".join([item[2] for item in selected])
 
         result = {
             "context": context_str,
             "relevant_nodes": [item[0] for item in selected],
             "scores": {item[0]: round(item[1], 3) for item in selected},
             "estimated_tokens": len(context_str) // 3,
             "total_candidates": len(scored_nodes)
         }
 
         if include_graph_summary:
             result["graph_summary"] = (
                 f"Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges. "
                 f"Top relevant: {len(selected)} / {len(scored_nodes)} candidates."
             )
 
         return result
 
     def get_graph_stats(self) -> Dict[str, Any]:
         return {
             "nodes": self.graph.number_of_nodes(),
             "edges": self.graph.number_of_edges(),
             "files_loaded": len(self.files),
             "semantic_enabled": self.semantic_enabled
         }
