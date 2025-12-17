"""Tests for optional_params."""

from ..component import optional_params


def test_required_param_only():
    """Test with only required parameter."""
    result = optional_params.python_func(required_param="test")
    assert result == "test"


def test_with_optional_text():
    """Test with optional text parameter."""
    result = optional_params.python_func(required_param="hello", optional_text=" world")
    assert result == "hello world"


def test_with_max_length():
    """Test with max_length parameter."""
    result = optional_params.python_func(required_param="a" * 150, max_length=50)
    assert len(result) == 50


def test_none_optional_text():
    """Test with explicitly None optional text."""
    result = optional_params.python_func(required_param="test", optional_text=None)
    assert result == "test"
