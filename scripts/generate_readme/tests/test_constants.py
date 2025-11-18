"""Tests for constants.py module."""

from ..constants import (
    CUSTOM_CONTENT_MARKER,
    logger,
)


class TestConstants:
    """Tests for module constants."""
    
    def test_custom_content_marker_format(self):
        """Test that custom content marker is in HTML comment format."""
        assert CUSTOM_CONTENT_MARKER.startswith('<!--')
        assert CUSTOM_CONTENT_MARKER.endswith('-->')
        assert 'custom-content' in CUSTOM_CONTENT_MARKER
    
    def test_logger_exists(self):
        """Test that logger is configured."""
        import logging
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_logger_name(self):
        """Test that logger has correct name."""
        # Logger should have a name from the constants module
        assert 'constants' in logger.name

