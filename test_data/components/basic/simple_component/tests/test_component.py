"""Tests for simple_component."""

from ..component import simple_component


def test_simple_component_basic():
    """Test basic functionality of simple_component."""
    result = simple_component.python_func(input_text="test", count=3)
    assert result == "testtesttest"


def test_simple_component_single():
    """Test with count of 1."""
    result = simple_component.python_func(input_text="hello", count=1)
    assert result == "hello"


def test_simple_component_zero():
    """Test with count of 0."""
    result = simple_component.python_func(input_text="test", count=0)
    assert result == ""
