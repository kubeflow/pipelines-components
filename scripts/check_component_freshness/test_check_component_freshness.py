"""Tests for component freshness checker."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from .check_component_freshness import FRESH_DAYS, STALE_DAYS, categorize, parse_date, scan_repo


class TestParsing:
    """Tests for parse_date function."""

    def test_parse_iso_z(self):
        """Test parsing ISO 8601 date with Z timezone."""
        dt = parse_date("2025-11-13T00:00:00Z")
        assert dt.year == 2025 and dt.month == 11 and dt.day == 13

    def test_parse_iso_offset(self):
        """Test parsing ISO 8601 date with offset timezone."""
        dt = parse_date("2025-11-14 00:00:00+00:00")
        assert dt.year == 2025 and dt.month == 11 and dt.day == 14

    def test_parse_date_only(self):
        """Test parsing date only."""
        dt = parse_date("2025-11-15")
        assert dt.year == 2025 and dt.month == 11 and dt.day == 15

    def test_invalid_date(self):
        """Test invalid date."""
        with pytest.raises(ValueError):
            parse_date("invalid-date")


class TestCategorize:
    """Tests for categorize function."""

    def test_fresh(self):
        """Test fresh category."""
        assert categorize(100) == "fresh"
        assert categorize(FRESH_DAYS - 1) == "fresh"

    def test_warning(self):
        """Test warning category."""
        assert categorize(FRESH_DAYS) == "warning"
        assert categorize(STALE_DAYS - 1) == "warning"

    def test_stale(self):
        """Test stale category."""
        assert categorize(STALE_DAYS) == "stale"
        assert categorize(500) == "stale"


class TestScanRepo:
    """Tests for scan_repo function."""

    def create_metadata(self, tmpdir: Path, name: str, days_ago: int, subdir: str = "components"):
        """Helper to create test metadata files in components/ or pipelines/.

        Args:
            tmpdir: The temporary directory to create the metadata file in.
            name: The name of the component.
            days_ago: The number of days ago to set the lastVerified timestamp to.
            subdir: The subdirectory to create the metadata file in (components or pipelines).
        """
        # Create proper directory structure: subdir/category/name/metadata.yaml
        comp_dir = tmpdir / subdir / "test_category" / name
        comp_dir.mkdir(parents=True)
        date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (comp_dir / "metadata.yaml").write_text(yaml.dump({"name": name, "lastVerified": date}))

    def test_categorizes_correctly(self):
        """Test categorizes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self.create_metadata(tmp, "fresh-comp", 100)
            self.create_metadata(tmp, "warning-comp", 300)
            self.create_metadata(tmp, "stale-comp", 400)

            results = scan_repo(tmp)

            assert len(results["fresh"]) == 1
            assert len(results["warning"]) == 1
            assert len(results["stale"]) == 1
            assert results["fresh"][0]["name"] == "fresh-comp"
            assert results["warning"][0]["name"] == "warning-comp"
            assert results["stale"][0]["name"] == "stale-comp"

    def test_handles_missing_field(self):
        """Test handles missing field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            comp_dir = tmp / "components" / "test_category" / "invalid"
            comp_dir.mkdir(parents=True)
            (comp_dir / "metadata.yaml").write_text(yaml.dump({"name": "no-date"}))

            results = scan_repo(tmp)
            assert len(results["fresh"]) == 0
            assert len(results["warning"]) == 0
            assert results["stale"][0]["name"] == "no-date"
            assert results["stale"][0]["last_verified"] == "unknown"
            assert results["stale"][0]["age_days"] == 0

    def test_scans_pipelines_directory(self):
        """Test script scans pipelines directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            self.create_metadata(tmp, "my-pipeline", 100, subdir="pipelines")
            results = scan_repo(tmp)
            assert len(results["fresh"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
