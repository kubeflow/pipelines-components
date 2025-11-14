"""Constants and shared configuration for the generate_readme package."""

import logging

# Set up logger
logger = logging.getLogger(__name__)

# Custom content marker for preserving user-added content
CUSTOM_CONTENT_MARKER = '<!-- custom-content -->'

# Google-style docstring regex pattern for parsing argument lines: "arg_name (type): description"
GOOGLE_ARG_REGEX_PATTERN = r'\s*(\w+)\s*\(([^)]+)\):\s*(.*)'

