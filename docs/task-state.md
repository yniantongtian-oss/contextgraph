# Task State

## Current milestone

Prepare a reliable public alpha (`0.1.0`) with importable code, enforced CI, accurate documentation, and a publishable distribution name.

## September 2026 maintenance

- Combined the pending checkout, Python setup, Rich, and regression-test updates.
- Preserved the 80% CI coverage requirement in the local configuration.
- Validation and a fresh CI run are required before merging the maintenance branch.
- Package publication is outside this maintenance task.

## Completed in current maintenance pass

- repaired malformed Python indentation
- strengthened Python graph construction and retrieval
- added core and CLI tests
- hardened CI and package validation
- changed the distribution name to `contextgraph-ai`
- documented architecture, contribution, security, and maintenance rules

## Next priorities

1. Merge the maintenance pull request after CI passes.
2. Configure PyPI trusted publishing for the `pypi` GitHub environment.
3. Publish `0.1.0` only after confirming the distribution name is accepted.
4. Add benchmark fixtures before claiming retrieval-quality or token-savings improvements.

## October 2026 maintenance

- Added a structured JSON source-bundle command for interoperable retrieval.
- Added CLI regression coverage for the new file output.
- Removed provider-specific instruction generation from the command-line interface.
- Verified that structured retrieval preserves source provenance.
- Publishing and incremental indexing remain separate follow-up milestones.
