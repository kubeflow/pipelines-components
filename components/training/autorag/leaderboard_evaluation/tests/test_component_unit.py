"""Tests for the leaderboard_evaluation component."""

import json
from pathlib import Path
from unittest import mock

import pytest

from ..component import leaderboard_evaluation


class TestLeaderboardEvaluationUnitTests:
    """Unit tests for leaderboard_evaluation success and failure paths."""

    def test_component_function_exists(self):
        """Component factory exists and exposes python_func."""
        assert callable(leaderboard_evaluation)
        assert hasattr(leaderboard_evaluation, "python_func")

    def test_missing_rag_patterns_dir_raises_file_not_found(self, tmp_path):
        """Non-existing rag_patterns input path raises FileNotFoundError."""
        html_artifact = mock.MagicMock(path=str(tmp_path / "out.html"))
        with pytest.raises(FileNotFoundError, match="rag_patterns path is not a directory"):
            leaderboard_evaluation.python_func(
                rag_patterns=str(tmp_path / "missing"),
                html_artifact=html_artifact,
                optimization_metric="faithfulness",
            )

    def test_generates_html_from_pattern_json(self, tmp_path):
        """Valid pattern directory produces non-empty HTML leaderboard."""
        rag_patterns_dir = tmp_path / "patterns"
        pattern_dir = rag_patterns_dir / "pattern_a"
        pattern_dir.mkdir(parents=True)
        (pattern_dir / "pattern.json").write_text(
            json.dumps(
                {
                    "name": "pattern_a",
                    "scores": {
                        "faithfulness": {"mean": 0.95},
                        "answer_correctness": {"mean": 0.83},
                    },
                    "settings": {
                        "chunking": {"method": "recursive", "chunk_size": 512, "chunk_overlap": 64},
                        "embedding_model": "embed-1",
                        "retrieval": {"method": "vector", "number_of_chunks": 5, "search_mode": "vector"},
                        "foundation_model": "gen-1",
                    },
                }
            ),
            encoding="utf-8",
        )
        html_artifact = mock.MagicMock(path=str(tmp_path / "leaderboard.html"))

        leaderboard_evaluation.python_func(
            rag_patterns=str(rag_patterns_dir),
            html_artifact=html_artifact,
            optimization_metric="faithfulness",
        )

        html_text = Path(html_artifact.path).read_text(encoding="utf-8")
        assert "RAG Patterns Leaderboard" in html_text
        assert "pattern_a" in html_text
        assert "faithfulness" in html_text
