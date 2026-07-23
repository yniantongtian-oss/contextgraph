# Repository Agent Guide

## Goal

Keep ContextGraph small, local-first, deterministic by default, and easy to validate.

## Working rules

- Work on a focused branch and open a pull request; do not push broad changes directly to `main`.
- Inspect the smallest relevant scope before editing. Do not scan unrelated large directories without a reason.
- Maintain `docs/task-state.md` during multi-stage work so another session can resume safely.
- Preserve repository-relative graph identifiers and the public `contextgraph` import package.
- Never execute code from a repository being indexed.
- Default features must not require network access or an embedding model.
- Add tests for parser, graph, ranking, token-budget, and CLI behavior that changes.
- Keep logs concise and surface actionable parse/load failures rather than silently swallowing them.

## Validation

```bash
ruff check src tests examples
ruff format --check src tests examples
pytest --cov=contextgraph
python -m build
python -m twine check dist/*
```
