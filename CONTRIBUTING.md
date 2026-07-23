# Contributing

Thanks for helping improve ContextGraph.

## Development setup

```bash
git clone https://github.com/yniantongtian-oss/contextgraph.git
cd contextgraph
python -m pip install -e ".[dev]"
```

## Required checks

Before opening a pull request, run:

```bash
ruff check src tests examples
ruff format --check src tests examples
pytest --cov=contextgraph
python -m build
python -m twine check dist/*
```

## Pull requests

- Keep changes focused and explain the retrieval behavior that changes.
- Add or update tests for bug fixes and public behavior.
- Avoid adding network calls to the default indexing or query path.
- Update `CHANGELOG.md` for user-visible changes.
- Preserve the `contextgraph` import package unless a breaking change is explicitly approved.

## Parser contributions

New language support should define:

1. Which entities and relationships are extracted.
2. How node identifiers remain stable across runs.
3. How syntax errors and unsupported constructs are reported.
4. Fixtures covering representative and adversarial source files.
