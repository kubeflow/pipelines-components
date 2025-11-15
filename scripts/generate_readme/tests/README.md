# Generate README Tests

Comprehensive unit tests for the `generate_readme` package.

## Running Tests

From the project root:

```bash
# Run all tests
pytest scripts/generate_readme/tests/

# Run with verbose output
pytest scripts/generate_readme/tests/ -v

# Run with coverage
pytest scripts/generate_readme/tests/ --cov=scripts.generate_readme

# Run specific test file
pytest scripts/generate_readme/tests/test_metadata_parser.py

# Run specific test class
pytest scripts/generate_readme/tests/test_metadata_parser.py::TestComponentMetadataParser

# Run specific test
pytest scripts/generate_readme/tests/test_metadata_parser.py::TestComponentMetadataParser::test_find_function_with_dsl_component
```

## Test Structure

```
tests/
├── __init__.py                  # Package initialization
├── conftest.py                  # Shared fixtures
├── test_cli.py                  # CLI argument parsing and validation tests
├── test_constants.py            # Constants and configuration tests
├── test_content_generator.py    # README content generation tests
├── test_metadata_parser.py      # Metadata extraction tests
└── test_writer.py               # Main generator orchestration tests
```

## Test Coverage

### test_writer.py
- Initialization with component/pipeline directories
- Custom content extraction and preservation
- README file generation
- Output file customization
- Verbose logging
- Overwrite protection
- Complete end-to-end generation

### test_metadata_parser.py
- Google-style docstring parsing
- Type annotation handling
- Component decorator detection (@dsl.component, @component, @kfp.dsl.component)
- Pipeline decorator detection (@dsl.pipeline, @pipeline, @kfp.dsl.pipeline)
- Function finding in AST
- Metadata extraction from decorated functions

### test_content_generator.py
- YAML metadata loading
- Section generation (title, overview, inputs/outputs, usage examples, metadata)
- Component vs pipeline differentiation
- Usage example generation with correct types
- Custom content preservation
- Edge cases (empty metadata, missing fields)

### test_cli.py
- Directory validation (component and pipeline)
- Argument parsing (--component, --pipeline, --verbose, --overwrite, --output)
- Error handling for invalid paths
- Short flag support (-v, -o)
- Help message display

### test_constants.py
- Constant value validation
- Regex pattern testing
- Logger configuration

## Dependencies

Tests require:
- `pytest` - Testing framework
- `pytest-cov` (optional) - Coverage reporting
- `kfp` - Kubeflow Pipelines SDK (for fixtures)
- `pyyaml` - YAML parsing

Install test dependencies:
```bash
pip install pytest pytest-cov
```

## Test Categories

Tests are organized by module and cover:

1. **Unit Tests**: Test individual functions and methods in isolation
2. **Integration Tests**: Test interaction between modules
3. **Edge Case Tests**: Test boundary conditions and error handling
4. **Fixture Tests**: Validate test fixtures and setup

## Writing New Tests

When adding new functionality:

1. Add test fixtures to `conftest.py` if they're reusable
2. Create new test file or add to existing file in the appropriate module
3. Follow naming convention: `test_<module_name>.py`
4. Use descriptive test names: `test_<function_name>_<scenario>`
5. Include docstrings explaining what each test validates
6. Use appropriate fixtures from `conftest.py`

Example:
```python
def test_new_feature_success_case(component_dir):
    """Test that new feature works correctly with valid input."""
    # Arrange
    generator = MyClass(component_dir)
    
    # Act
    result = generator.new_feature()
    
    # Assert
    assert result is not None
    assert "expected" in result
```

