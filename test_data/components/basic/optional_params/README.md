# Optional Parameters Component ✨

## Overview 🧾

Processes text with optional configuration.

This component demonstrates optional parameters with defaults.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `required_param` | `str` | `None` | This parameter is required. |
| `optional_text` | `Optional[str]` | `None` | Optional text to append. |
| `max_length` | `int` | `100` | Maximum length of output. |
| `separator` | `str` | `""` | Separator between texts (empty by default). |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `str` | The processed text. |

## Usage Examples 🧪

```python
"""Example pipelines demonstrating usage of optional_params."""

from kfp import dsl
from kfp_components.components.basic.optional_params import optional_params


@dsl.pipeline(name="optional-params-example")
def example_pipeline(input: str = "test"):
    """Example pipeline using optional_params.

    Args:
        input: Input text to process.
    """
    # Example 1: Using only required parameter
    optional_params(required_param=input)

    # Example 2: Using optional parameters
    optional_params(required_param=input, optional_text=" suffix", max_length=50)

```

## Metadata 🗂️

- **Name**: Optional Parameters Component
- **Description**: Component demonstrating optional parameters with default values
- **Documentation**: https://example.com/optional-params
- **Tags**:
  - testing
  - parameters
- **Owners**:
  - Approvers:
    - HumairAK
    - mprahl
