# Simple Component ✨

## Overview 🧾

Processes input text a specified number of times.

This is a simple component used for testing the README generator.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_text` | `str` | `None` | The text to process. |
| `count` | `int` | `None` | Number of times to repeat the operation. |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `str` | The processed result. |

## Usage Examples 🧪

```python
"""Example pipelines demonstrating usage of simple_component."""

from kfp import dsl
from kfp_components.components.basic.simple_component import simple_component


@dsl.pipeline(name="simple-component-example")
def example_pipeline(text: str = "hello", repeat_count: int = 3):
    """Example pipeline using simple_component.

    Args:
        text: Text to process.
        repeat_count: Number of times to repeat.
    """
    simple_component(input_text=text, count=repeat_count)

```

## Metadata 🗂️

- **Name**: Simple Component
- **Description**: A basic component with required parameters
- **Documentation**: https://example.com/simple-component
- **Tags**:
  - testing
  - basic
- **Owners**:
  - Approvers:
    - HumairAK
    - mprahl
