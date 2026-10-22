# Changelog

All notable changes will be documented here.

## [Unreleased]

### Fixed

- Call edges no longer attach every same-named symbol in a file. Bare calls prefer the nested or module-level function, and `self.method()` stays on the enclosing class. Ambiguous names are left unresolved.
- Context packing no longer repeats a file, class, and method over the same lines, and a short later hit can still use leftover budget under 80 characters.
- `contextgraph scan` prints parse and load failures, and those messages are included in the statistics JSON.
- `pack` and `bundle` write index progress to stderr and print JSON without terminal wrapping, so a stdout document can be piped.
- Query text that contains square brackets is printed literally.
- Corrected the `bundle` command example so the shell continuations are single backslashes.
- Corrected invalid top-level indentation in the core module, CLI, tests, and example.
- Removed CI logic that converted failing tests into successful workflow runs.
- Avoided the already-occupied `contextgraph` PyPI distribution name.

### Added

- `contextgraph pack --budget N` exports ranked source that fits an approximate token budget, with per-item rank, score, path, and line span.
- Optional `contextgraph-ai[mcp]` extra: a stdio MCP server (`contextgraph mcp`) with `build_graph`, `query_context`, and `pack_context`, built on the official MCP Python SDK.
- Claude Code and Cursor configuration examples for that server.
- Regression coverage for nested and async symbols, relative imports, empty projects, and malformed Python.
- Two-pass Python symbol indexing with classes, methods, functions, imports, and resolvable call edges.
- Repository-relative node identifiers and richer graph statistics.
- Token-budgeted symbol source rendering and optional semantic scoring.
- CLI smoke tests, core behavior tests, coverage enforcement, package validation, and Python 3.13 CI.
- Contribution, security, architecture, task-state, and agent-maintenance documentation.

### Changed

- Updated checkout and Python setup actions to v7 and allowed Rich 15.
- Aligned the local branch coverage gate with CI at 80%.
- Distribution name is now `contextgraph-ai`; the import package remains `contextgraph`.
- Semantic search is opt-in in the CLI to avoid unexpected model downloads.
- Project status is correctly marked as alpha.

## [0.1.0] - Unreleased

Initial public alpha.
