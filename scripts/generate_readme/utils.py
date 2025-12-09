"""Utility functions for README generation."""

import re


def format_title(title: str) -> str:
    """Format a title from snake_case, kebab-case, or camelCase to Title Case.

    Args:
        title: The title to format.

    Returns:
        Formatted title in Title Case with spaces.
    """
    # First, handle camelCase by inserting spaces before capitals
    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)

    # Replace underscores and hyphens with spaces
    title = title.replace('_', ' ').replace('-', ' ')

    # Split into words and capitalize each
    words = title.split()
    formatted_words = []

    for word in words:
        # Keep known acronyms in uppercase
        if word.upper() in ['KFP', 'API', 'URL', 'ID', 'UI', 'CI', 'CD']:
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word.capitalize())

    return ' '.join(formatted_words)

