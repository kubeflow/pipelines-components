# Utility Scripts

This directory contains utility scripts for the project.

## Directory Structure

```text
scripts/
├── <script_name>/       # Each script has its own directory
│   ├── <script_name>.py # The script itself (or a module with multiple files)
│   └── tests/           # Optional: unit tests for this script
│       └── test_<script_name>.py
├── utils/               # Shared utilities for common helpers
└── README.md
```

## Scripts vs Unit Tests

- **Scripts** (`<script_name>/<script_name>.py`) are executed directly or imported as modules
- **Unit tests** (`<script_name>/tests/test_*.py`) verify the scripts work correctly and are run by `scripts-tests.yml`

## Adding a New Script

1. Create a new directory for your script:

   ```bash
   mkdir -p scripts/my_script
   ```

2. Add your script file:

   ```text
   scripts/my_script/my_script.py
   ```

3. If your script needs unit tests, add them in a `tests/` subdirectory:

   ```text
   scripts/my_script/tests/test_my_script.py
   ```

4. If your tests need resources (test data/mocks), add them in a `resources/` subdirectory:

   ```text
   scripts/my_script/tests/resources/
   ```

## Running Unit Tests Locally

Unit tests are discovered from `*/tests/` directories only:

```bash
cd scripts
uv run pytest */tests/ -v --tb=short
```

## Conventions

- **Scripts** live at `<script_name>/<script_name>.py` (or as a module with multiple files)
- **Unit tests** live at `<script_name>/tests/test_*.py`
- `resources/` directories contain test data/mocks
- Only files in `*/tests/` directories are run by `scripts-tests.yml`
- The `.github/scripts/` directory follows the same structure and testing conventions for CI-only scripts
