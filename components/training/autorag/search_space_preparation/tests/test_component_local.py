"""Local runner tests for the search_space_preparation component."""

import pytest

from ..component import search_space_preparation


class TestSearchSpacePreparationLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="Requires input artifacts and model APIs; run E2E in pipeline")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        result = search_space_preparation(
            test_data=...,
            extracted_text=...,
            search_space_prep_report=...,
        )
        assert result is not None
