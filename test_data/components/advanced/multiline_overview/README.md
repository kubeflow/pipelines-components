# Multiline Overview Component ✨

## Overview 🧾

Processes data with complex logic.

This component demonstrates a multiline overview section.
It handles various types of input data and applies
transformations based on configurable rules.

The component is designed for flexibility and can be
used in multiple pipeline scenarios.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_data` | `str` | `None` | The data to process. |

## Outputs 📤

| Name | Type | Description |
|------|------|-------------|
| Output | `str` | The processed data. |

## Usage Examples 🧪

```python
"""Example pipelines demonstrating usage of process_data."""

from kfp import dsl
from kfp_components.components.advanced.multiline_overview import process_data


@dsl.pipeline(name="process-data-example")
def example_pipeline(data: str = "sample data"):
    """Example pipeline using process_data.

    This demonstrates the multiline overview component in action.

    Args:
        data: Input data to process.
    """
    process_data(input_data=data)


@dsl.pipeline(name="multi-step-processing")
def multi_step_example():
    """Example with multiple processing steps."""
    process_data(input_data="first")
    process_data(input_data="second")
    process_data(input_data="third")

```

## Metadata 🗂️

- **Name**: Multiline Overview Component
- **Description**: Component with a detailed multiline overview in docstring
- **Documentation**: https://example.com/multiline-overview
- **Tags**:
  - testing
  - advanced
  - documentation
- **Owners**:
  - Approvers:
    - HumairAK
    - mprahl
