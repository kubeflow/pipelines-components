# CI Scripts

This directory contains scripts used in CI workflows.

This directory follows the same structure and conventions as `scripts/`. For directory structure, conventions, and how to add new scripts, see [scripts/README.md](../../scripts/README.md).

## Running Unit Tests Locally

```bash
cd .github/scripts
uv run pytest */tests/ -v --tb=short
```
