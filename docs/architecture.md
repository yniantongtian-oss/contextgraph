# Architecture

## Pipeline

1. `load_project` discovers supported source files, applies exclusions, enforces a per-file size limit, and stores repository-relative metadata.
2. `build_graph` adds file nodes and parses Python files with `ast`.
3. A first pass registers classes, functions, methods, and imports.
4. A second pass resolves each call to one unambiguous target.
5. `query_context` and `pack_context` score queryable nodes and render source snippets under an approximate token budget.
6. The CLI and the optional stdio MCP server call those methods. They do not implement a second ranker.

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
- `calls`: caller symbol or file to one resolvable target symbol

Bare-name calls prefer a nested function in the caller, then a unique module-level function in the same file, then a single local symbol, then a globally unique symbol. Attribute calls such as `self.save()` prefer a symbol in the enclosing class. When more than one target remains plausible, the edge is omitted.

## Retrieval scoring

The alpha scorer combines:

- overlap with symbol and qualified names
- overlap with repository-relative file paths
- source-content term matches
- exact phrase bonus
- bounded graph-degree importance
- optional cosine similarity from a local sentence-transformer

The scorer is heuristic, not a correctness proof. Benchmarks should measure retrieval recall, context precision, token use, and stability.

Equal scores prefer a symbol over its file, then the repository-relative node id, so packs are stable across runs.

## Context packing

`pack_context` fills the budget in rank order. A chosen node suppresses any later candidate whose line span contains it or sits inside it, so a file, class, and method are not copied over one another. A container that does not fit is skipped when a stricter hit inside it is still available; otherwise it is truncated and marked. Blocks that fit in the remaining characters are kept even when that remainder is small. Separator characters between blocks count toward the budget. The published token estimate is `ceil(len(context) / 4)` for the packed text only.

## Known limitations

- Python only for structural parsing
- no full type inference or dynamic dispatch resolution
- ambiguous cross-file calls are intentionally left unresolved
- approximate token counting uses four characters per token
- the MCP server keeps one index in memory per project path until `build_graph` runs again
- incremental indexing and persistent storage are not implemented
