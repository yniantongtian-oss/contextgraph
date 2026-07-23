# Architecture

## Pipeline

1. `load_project` discovers supported source files, applies exclusions, enforces a per-file size limit, and stores repository-relative metadata.
2. `build_graph` adds file nodes and parses Python files with `ast`.
3. A first pass registers classes, functions, methods, and imports.
4. A second pass resolves local or globally unambiguous call targets.
5. `query_context` scores queryable nodes and renders source snippets under an approximate token budget.

## Node identifiers

Identifiers are deliberately repository-relative so results do not expose machine-specific absolute paths and remain comparable across clones.

| Node type | Example |
| --- | --- |
| File | `file:src/api.py` |
| Symbol | `symbol:src/api.py::Router.handle` |
| Module | `module:sqlite3` |

## Relationships

- `defines`: file to class/function/method
- `imports`: file to imported module
- `calls`: caller symbol or file to a resolvable target symbol

## Retrieval scoring

The alpha scorer combines:

- overlap with symbol and qualified names
- overlap with repository-relative file paths
- source-content term matches
- exact phrase bonus
- bounded graph-degree importance
- optional cosine similarity from a local sentence-transformer

The scorer is heuristic, not a correctness proof. Benchmarks should measure retrieval recall, context precision, token use, and stability.

## Known limitations

- Python only for structural parsing
- no full type inference or dynamic dispatch resolution
- ambiguous cross-file calls are intentionally left unresolved
- approximate token counting uses four characters per token
- incremental indexing and persistent storage are not implemented
