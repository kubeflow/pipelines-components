"""OCI (Open Container Initiative) validation utilities."""

import re

# Tag pattern: first char is alphanumeric or underscore; last char must also be
# alphanumeric or underscore (no trailing dot/hyphen); max 128 chars total.
_TAG_PATTERN = re.compile(r"[\w](?:[\w.-]{0,126}[\w])?", re.ASCII)

# Image name pattern: first char is lowercase alphanumeric or underscore;
# subsequent chars may be alphanumeric (any case), underscore, dot, or hyphen.
IMAGE_NAME_REGEX = r"[a-z0-9_][A-Za-z0-9_.-]*"
_IMAGE_NAME_PATTERN = re.compile(IMAGE_NAME_REGEX, re.ASCII)


def validate_tag(tag: str) -> None:
    """Validate an OCI container tag, raising ValueError if invalid."""
    if not _TAG_PATTERN.fullmatch(tag):
        raise ValueError(f"Invalid container tag: {tag!r}")


def validate_image_name(name: str) -> None:
    """Validate an OCI image name component, raising ValueError if invalid."""
    if not _IMAGE_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid image name: {name!r}")
