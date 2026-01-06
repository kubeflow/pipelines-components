# Utility Scripts

This directory contains utility scripts for the project.

## Directory Structure

```text
scripts/
├── <script_name>/       # Each script has its own directory
│   ├── <script_name>.py # The script itself (or a module with multiple files)
│   └── tests/           # Optional: unit tests for this script
│       └── test_<script_name>.py
├── lib/                 # Shared libraries
└── README.md
```

## Common Libraries (`scripts/lib/`)

Shared utilities used across multiple scripts:

| Module               | Description                                                                          |
|----------------------|--------------------------------------------------------------------------------------|
| `base_image.py`      | Base image extraction and validation (allowlists, prefix checks)                     |
| `discovery.py`       | Asset discovery for KFP components/pipelines (path resolution, target normalization) |
| `kfp_compilation.py` | KFP module loading, compilation, and runtime decorator discovery                     |
| `parsing.py`         | AST-based utilities for finding decorated functions                                  |

### Usage

```python
# From a script in scripts/<script_name>/<script_name>.py
from ..lib.discovery import get_repo_root, discover_assets
from ..lib.kfp_compilation import load_module_from_path, compile_and_get_yaml
from ..lib.parsing import find_pipeline_functions
from ..lib.base_image import extract_base_images, is_valid_base_image
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

## Import Conventions

Scripts are organized as Python packages using `__init__.py` files. Tests use relative imports to import from their parent module.

### Package Structure

Each script directory must have:

- `__init__.py` in the script directory (can be empty)
- `__init__.py` in the `tests/` subdirectory (can be empty)

```text
scripts/
├── my_script/
│   ├── __init__.py          # Required (can be empty)
│   ├── my_script.py
│   └── tests/
│       ├── __init__.py      # Required (can be empty)
│       └── test_my_script.py
```

### Import Pattern

Tests use relative imports to access the parent module:

```python
# In scripts/my_script/tests/test_my_script.py
from ..my_script import my_function, MyClass
```

For scripts with multiple modules:

```python
# In scripts/my_script/tests/test_utils.py
from ..utils import helper_function
from ..my_script import main
```

This pattern ensures imports work correctly for both IDE static analysis and pytest runtime.
