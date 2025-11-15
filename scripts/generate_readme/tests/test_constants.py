"""Tests for constants.py module."""

from ..constants import (
    CUSTOM_CONTENT_MARKER,
    GOOGLE_ARG_REGEX_PATTERN,
    logger,
)


class TestConstants:
    """Tests for module constants."""
    
    def test_custom_content_marker_format(self):
        """Test that custom content marker is in HTML comment format."""
        assert CUSTOM_CONTENT_MARKER.startswith('<!--')
        assert CUSTOM_CONTENT_MARKER.endswith('-->')
        assert 'custom-content' in CUSTOM_CONTENT_MARKER
    
    def test_google_arg_regex_pattern_valid(self):
        """Test that the Google arg regex pattern matches valid argument lines."""
        import re
        
        # Test valid argument lines
        valid_lines = [
            "param1 (str): Description here.",
            "  param_name (int): Another description.",
            "long_parameter_name (List[str]): Complex type description.",
        ]
        
        for line in valid_lines:
            match = re.match(GOOGLE_ARG_REGEX_PATTERN, line)
            assert match is not None, f"Failed to match: {line}"
    
    def test_google_arg_regex_pattern_captures_groups(self):
        """Test that the regex captures parameter name, type, and description."""
        import re
        
        line = "  param_name (str): This is the description."
        match = re.match(GOOGLE_ARG_REGEX_PATTERN, line)
        
        assert match is not None
        groups = match.groups()
        assert len(groups) == 3
        assert groups[0] == 'param_name'  # Parameter name
        assert groups[1] == 'str'  # Type
        assert groups[2] == 'This is the description.'  # Description
    
    def test_google_arg_regex_pattern_invalid(self):
        """Test that the regex doesn't match invalid lines."""
        import re
        
        invalid_lines = [
            "not a parameter line",
            "missing_parens str: description",
            "(str): missing name",
        ]
        
        for line in invalid_lines:
            match = re.match(GOOGLE_ARG_REGEX_PATTERN, line)
            assert match is None, f"Should not match: {line}"
    
    def test_logger_exists(self):
        """Test that logger is configured."""
        import logging
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_logger_name(self):
        """Test that logger has correct name."""
        # Logger should have a name from the constants module
        assert 'constants' in logger.name

