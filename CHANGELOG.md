# Changelog

All notable changes will be documented here.

## [Unreleased]

### Fixed

- Corrected invalid top-level indentation in the core module, CLI, tests, and example.
- Removed CI logic that converted failing tests into successful workflow runs.
- Avoided the already-occupied `contextgraph` PyPI distribution name.

### Added

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
