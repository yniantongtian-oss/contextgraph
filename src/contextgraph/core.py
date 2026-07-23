import ast
 import os
 from pathlib import Path
 from typing import List, Dict, Any, Optional
 import networkx as nx
 from rich.console import Console

 console = Console()


 class CodeContextGraph:
     """Main class for building and querying code intelligence graphs."""
 
     def __init__(self):
         self.graph = nx.DiGraph()
         self.files: Dict[str, Dict] = {}  # file_path -> metadata
         self.console = Console()
 
     def load_project(self, root_path: str, languages: Optional[List[str]] = None):
         """Scan and load source files from a project directory."""
         if languages is None:
             languages = ["python"]
 
         root = Path(root_path).resolve()
         self.root_path = root
 
         for ext, lang in {".py": "python",
                       ".c": "c", ".h": "c",
                       ".cpp": "cpp", ".hpp": "cpp",
                       ".js": "javascript",
                       ".ts": "typescript"}.items():
             if lang in languages or "all" in languages:
                 for file_path in root.rglob(f"*{ext}"):
                     if any(part.startswith(".") for part in file_path.parts):
                         continue  # skip hidden dirs
                     try:
                         with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                             content = f.read()
                         self.files[str(file_path)] = {
                             "language": lang,
                             "content": content,
                             "size": len(content)
                         }
                     except Exception:
                         pass
 
         self.console.print(f"[green]Loaded {len(self.files)} files from {root}")
 
     def build_graph(self):
         """Build the code relationship graph. Currently focuses on Python."""
         self.graph.clear()
 
         for file_path, meta in self.files.items():
             if meta["language"] != "python":
                 continue
 
             try:
                 tree = ast.parse(meta["content"], filename=file_path)
             except SyntaxError:
                 continue
 
             # Add file node
             self.graph.add_node(file_path, type="file", language="python")
 
             for node in ast.walk(tree):
                 if isinstance(node, ast.FunctionDef):
                     func_name = node.name
                     node_id = f"{file_path}::{func_name}"
                     self.graph.add_node(node_id, type="function", name=func_name, file=file_path)
                     self.graph.add_edge(file_path, node_id, relation="defines")
 
                     # Simple call detection (basic)
                     for subnode in ast.walk(node):
                         if isinstance(subnode, ast.Call):
                             if isinstance(subnode.func, ast.Name):
                                 called = subnode.func.id
                                 called_id = f"{file_path}::{called}"
                                 if self.graph.has_node(called_id):
                                     self.graph.add_edge(node_id, called_id, relation="calls")
 
                 elif isinstance(node, ast.Import):
                     for alias in node.names:
                         self.graph.add_edge(file_path, alias.name, relation="imports")
 
                 elif isinstance(node, ast.ImportFrom):
                     if node.module:
                         self.graph.add_edge(file_path, node.module, relation="imports_from")
 
         self.console.print(f"[green]Built graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
 
     def query_context(self, query: str, max_tokens: int = 2000, include_graph_summary: bool = True) -> Dict[str, Any]:
         """Retrieve relevant context based on query and token budget."""
         # Simple keyword-based relevance for MVP
         relevant = []
         query_lower = query.lower()
 
         for node_id, data in self.graph.nodes(data=True):
             if data.get("type") == "function":
                 name = data.get("name", "").lower()
                 if any(word in name for word in query_lower.split()):
                     relevant.append(node_id)
 
         # Fallback: include some file-level nodes
         if not relevant:
             for file_path in list(self.files.keys())[:5]:
                 relevant.append(file_path)
 
         # Build context string (very basic token estimation)
         context_parts = []
         total_chars = 0
         approx_token_limit = max_tokens * 4  # rough char to token
 
         for node_id in relevant[:10]:  # limit for MVP
             if node_id in self.files:
                 content = self.files[node_id]["content"][:500]  # truncate
                 context_parts.append(f"# File: {Path(node_id).name}\n{content}")
                 total_chars += len(content)
             elif "::" in node_id:
                 # function node
                 context_parts.append(f"# Function: {node_id}")
 
             if total_chars > approx_token_limit:
                 break
 
         context_str = "\n\n".join(context_parts)
 
         result = {
             "context": context_str,
             "relevant_nodes": relevant,
             "estimated_tokens": len(context_str) // 4
         }
 
         if include_graph_summary:
             result["graph_summary"] = f"Graph has {self.graph.number_of_nodes()} nodes. " \
                                        f"Relevant entities found for query: {len(relevant)}"
 
         return result
 
     def get_graph_stats(self) -> Dict[str, Any]:
         return {
             "nodes": self.graph.number_of_nodes(),
             "edges": self.graph.number_of_edges(),
             "files_loaded": len(self.files)
         }
