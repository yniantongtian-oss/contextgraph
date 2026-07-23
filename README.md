# ContextGraph

[![PyPI](https://img.shields.io/pypi/v/contextgraph?color=blue)](https://pypi.org/project/contextgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/yniantongtian-oss/contextgraph?style=social)](https://github.com/yniantongtian-oss/contextgraph)

**Build and query intelligent code graphs for better LLM and AI agent context retrieval.**

ContextGraph turns codebases into structured, queryable graphs so that AI coding assistants and agents can retrieve only the most relevant context — dramatically improving accuracy while reducing token waste.

## Why This Matters in 2026

AI coding tools (Claude Code, Cursor, Continue.dev, local models) are exploding in popularity. The biggest remaining bottleneck is **context quality**:

- Feeding entire large repositories wastes tokens and introduces noise
- Models often miss critical related functions or files
- Developers waste time manually curating context

ContextGraph solves this by building a **code intelligence graph** and providing smart, scored, token-aware retrieval.

It is designed as infrastructure that works with any LLM or agent framework.

## Key Features

- **Graph Construction**: Automatically extracts functions, classes, imports, and call relationships
- **Smart Retrieval**: Keyword + graph importance + optional semantic similarity scoring
- **Token Budget Aware**: Respects your `max_tokens` limit with intelligent truncation
- **Semantic Search** (optional): Powered by `sentence-transformers` — runs fully locally (great with RTX GPUs)
- **CLI + Python API**: Easy to use in terminal or integrate into agents
- **Local-first**: No cloud, no data leaving your machine
- **Extensible**: Designed for future multi-language (C/C++, JS/TS) and framework-aware support

## Installation

```bash
pip install contextgraph
```

With semantic search support:

```bash
pip install "contextgraph[semantic]"
```

## Quick Start

### 1. Scan a project

```bash
contextgraph scan ./my-backend-project
```

### 2. Query for relevant context

```bash
contextgraph query "user authentication or JWT handling" --budget 1800 --project ./my-backend-project
```

### 3. Generate optimized prompt for any LLM

```bash
contextgraph prompt "Add rate limiting to the login endpoint" --max-tokens 1600
```

The generated prompt can be copied directly into Claude, GPT-5.6, local models (via Ollama, vLLM, etc.), or Cursor/Continue.dev.

## Python API Example

```python
from contextgraph import CodeContextGraph

cg = CodeContextGraph()
cg.load_project("./large-codebase")
cg.build_graph()

# Enable semantic search (recommended)
cg.enable_semantic_search()   # loads small local model

results = cg.query_context(
    query="database connection pooling or async session handling",
    max_tokens=2000,
    use_semantic=True
)

print(results["context"])          # Ready-to-use context
print(results["scores"])           # Relevance scores
print(results.get("graph_summary"))
```

## How the Query Algorithm Works

1. **Keyword matching** on function/file names and content
2. **Graph importance** (node degree / centrality)
3. **Semantic similarity** (optional, using local embeddings)
4. **Token budget pruning** with smart truncation

This hybrid approach gives much better results than pure keyword or pure embedding search.

## Examples

See the `examples/` directory for:
- Small realistic backend project demo
- Data processing script example
- Integration with local LLM workflows

## Development & Contributing

```bash
git clone https://github.com/yniantongtian-oss/contextgraph.git
cd contextgraph
pip install -e ".[dev,semantic]"
```

We welcome contributions especially in:
- Better multi-language parsing (tree-sitter)
- Framework-specific heuristics
- Benchmarks and real-world usage reports
- Integration examples with popular coding agents

## Roadmap

- [ ] Stronger multi-language support (C/C++, TypeScript)
- [ ] Framework-aware context boosting
- [ ] Persistent graph storage
- [ ] VS Code / Continue.dev extension hooks
- [ ] Public benchmarks on popular open-source projects

## License

MIT
