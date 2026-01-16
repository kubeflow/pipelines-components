"""Tests for OCI validation utilities."""

import pytest

from ..oci import validate_image_name, validate_tag


class TestValidateTag:
    """Tests for OCI container tag validation."""

    @pytest.mark.parametrize(
        "tag",
        [
            "latest",
            "v1.0.0",
            "v1.11.0",
            "abc123def456789",
            "abc123def456789012345678901234567890123",
            "main",
            "1.0",
            "1",
            "_private",
            "my_tag",
            "my.tag",
            "my-tag",
            "My.Tag-1_0",
            "a" * 128,
        ],
    )
    def test_valid_tags(self, tag: str):
        """Accepts valid OCI container tags."""
        validate_tag(tag)

    @pytest.mark.parametrize(
        "tag",
        [
            "",
            "tag/with/slash",
            "tag:with:colon",
            "tag with space",
            ".starts-with-dot",
            "-starts-with-hyphen",
            "a" * 129,
            "café",
            "日本語",
            "tag@version",
            "tag#1",
            "tag!",
            "ends-with-dot.",
            "ends-with-hyphen-",
            "v1.0.",
            "release-",
        ],
    )
    def test_invalid_tags(self, tag: str):
        """Rejects invalid OCI container tags."""
        with pytest.raises(ValueError, match="Invalid container tag"):
            validate_tag(tag)


class TestValidateImageName:
    """Tests for OCI image name validation."""

    @pytest.mark.parametrize(
        "name",
        [
            "example",
            "my-component",
            "api_server",
            "v1.0",
            "0config",
            "_private",
            "ds-pipelines-api-server",
            "component.name",
            "a",
            "abc123",
        ],
    )
    def test_valid_image_names(self, name: str):
        """Accepts valid OCI image names."""
        validate_image_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "Uppercase",
            "-starts-with-hyphen",
            ".starts-with-dot",
            "name/with/slash",
            "name:with:colon",
            "name with space",
            "café",
            "日本語",
            "name@version",
        ],
    )
    def test_invalid_image_names(self, name: str):
        """Rejects invalid OCI image names."""
        with pytest.raises(ValueError, match="Invalid image name"):
            validate_image_name(name)
