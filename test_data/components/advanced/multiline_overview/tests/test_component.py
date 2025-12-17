"""Tests for process_data."""

from ..component import process_data


def test_process_data_uppercase():
    """Test that data is converted to uppercase."""
    result = process_data.python_func(input_data="hello world")
    assert result == "HELLO WORLD"


def test_process_data_already_uppercase():
    """Test with already uppercase data."""
    result = process_data.python_func(input_data="ALREADY UPPER")
    assert result == "ALREADY UPPER"


def test_process_data_empty():
    """Test with empty string."""
    result = process_data.python_func(input_data="")
    assert result == ""


def test_process_data_special_chars():
    """Test with special characters."""
    result = process_data.python_func(input_data="hello-123_world!")
    assert result == "HELLO-123_WORLD!"
