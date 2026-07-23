# ContextGraph

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Build and query intelligent code graphs for better LLM and AI agent context retrieval.**

ContextGraph helps AI coding assistants and agents understand large codebases more effectively by constructing a structured graph of code relationships and retrieving only the most relevant context within token budgets.

## Why ContextGraph Now?

In 2026, the fastest-growing area on GitHub is AI coding tools and agent infrastructure. Projects focused on code intelligence, context management, and making LLMs actually useful on real-world codebases are gaining massive traction.

Current pain points:
- Token waste and context pollution when feeding entire codebases to models
- AI coding assistants (Claude, Cursor, Continue.dev, local models) often retrieve irrelevant code
- Lack of structured, queryable representation of code relationships

ContextGraph solves this by turning code into a queryable graph and providing smart, token-aware context extraction.

## Key Features

- Multi-language support (Python first, extensible to C/C++, JS/TS)
- Automatic code graph construction (imports, calls, definitions, dependencies)
- Intelligent context retrieval with token budget control
- Graph summary generation for better LLM understanding
- Clean CLI + Python API
- Local-first, no cloud dependency
- Ready for semantic enhancement with local embeddings

## Quick Start

### Installation

```bash
pip install contextgraph
```

For development:

```bash
git clone https://github.com/yniantongtian-oss/contextgraph.git
cd contextgraph
pip install -e ".[dev]"
```

### CLI Usage

```bash
# Scan a project and build the graph
contextgraph scan ./my-project --output graph.json

# Query for relevant context
contextgraph query "authentication or database connection logic" --budget 2000 --project ./my-project

# Generate optimized prompt for LLM
contextgraph prompt "Refactor the user service for better error handling" --max-tokens 1500
```

### Python API

```python
from contextgraph import CodeContextGraph

cg = CodeContextGraph()
cg.load_project("./my-large-codebase")
cg.build_graph()

results = cg.query_context(
    query="user authentication flow or database models",
    max_tokens=1800,
    include_graph_summary=True
)

print(results["context"])  # Ready to paste into Claude, GPT, or local model
print(results["relevant_files"])
```

## How It Works

1. **Scan** — Recursively finds source files
2. **Parse** — Extracts functions, classes, imports, and call relationships
3. **Graph** — Builds a NetworkX directed graph of code entities and relationships
4. **Query** — Ranks and selects the most relevant nodes within your token budget
5. **Output** — Returns clean context + graph summary optimized for LLMs

## Roadmap

- Semantic search layer using local embeddings (sentence-transformers)
- Improved multi-language support (tree-sitter)
- Framework-specific heuristics (FastAPI, React, PyTorch, etc.)
- Standard interfaces for easy integration with popular coding agents
- Visualization (Mermaid, Graphviz)

## Contributing

Contributions are welcome! Especially:
- Better parsers for C/C++ and JavaScript/TypeScript
- Integration examples with Continue.dev, Cursor, Claude Code
- Benchmarks on real-world codebases

Open an issue or pull request.

## License

MIT License
