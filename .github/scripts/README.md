# CI Scripts

This directory contains scripts used in CI workflows.

## Directory Structure

```text
.github/scripts/
├── <script_name>/       # Each script has its own directory
│   ├── <script_name>.py # The script itself (run by workflows)
│   └── tests/           # Optional: unit tests for this script
│       └── test_<script_name>.py
├── utils/               # Shared utilities for common helpers
└── README.md
```

## Scripts vs Unit Tests

- **Scripts** (`<script_name>/<script_name>.py`) are executed directly by workflows
- **Unit tests** (`<script_name>/tests/test_*.py`) verify the scripts work correctly and are run by `scripts-tests.yml`

## Adding a New Script

1. Create a new directory for your script:

   ```bash
   mkdir -p .github/scripts/my_script
   ```

2. Add your script file:

   ```text
   .github/scripts/my_script/my_script.py
   ```

3. If your script needs unit tests, add them in a `tests/` subdirectory:

   ```text
   .github/scripts/my_script/tests/test_my_script.py
   ```

4. If your tests need fixtures (test data/mocks), add them in a `fixtures/` subdirectory:

   ```text
   .github/scripts/my_script/tests/fixtures/
   ```

5. If your script needs its own workflow, create one in `.github/workflows/` that runs the script directly.

## Running Unit Tests Locally

Unit tests are discovered from `*/tests/` directories only:

```bash
cd .github/scripts
uv run pytest */tests/ -v --tb=short
```

## Conventions

- **Scripts** live at `<script_name>/<script_name>.py`
- **Unit tests** live at `<script_name>/tests/test_*.py`
- `fixtures/` directories contain test data/mocks
- Only files in `*/tests/` directories are run by `scripts-tests.yml`
