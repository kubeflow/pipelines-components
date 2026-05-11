"""Tests for the yoda_data_processor component."""

import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from ..component import add_yoda_prefix, prepare_yoda_dataset
from .support import InMemoryDataset, read_saved_rows, sample_rows


class TestYodaDataProcessorUnitTests:
    """Unit tests for component logic."""

    def test_add_yoda_prefix_updates_prompt_without_mutating_input(self):
        """Test the prompt transformation directly with a representative row."""
        example = {
            "prompt": "Train yourself to let go of everything you fear to lose.",
            "completion": "Let go of everything you fear to lose, train yourself to.",
        }

        transformed = add_yoda_prefix(example)

        assert transformed == {
            "prompt": "Translate the following to Yoda speak: Train yourself to let go of everything you fear to lose.",
            "completion": "Let go of everything you fear to lose, train yourself to.",
        }
        assert example["prompt"] == "Train yourself to let go of everything you fear to lose."

    def test_component_writes_prefixed_train_and_eval_datasets(self, tmp_path: Path):
        """Test the component against a small in-memory dataset fixture."""
        mock_load_dataset = mock.Mock(return_value=InMemoryDataset(sample_rows()))
        fake_datasets_module = types.ModuleType("datasets")
        fake_datasets_module.load_dataset = mock_load_dataset

        train_output = SimpleNamespace(path=str(tmp_path / "train"))
        eval_output = SimpleNamespace(path=str(tmp_path / "eval"))

        with mock.patch.dict("sys.modules", {"datasets": fake_datasets_module}):
            prepare_yoda_dataset.python_func(
                yoda_input_dataset="test-dataset",
                yoda_train_dataset=train_output,
                yoda_eval_dataset=eval_output,
                train_split_ratio=0.6,
            )

        mock_load_dataset.assert_called_once_with("test-dataset", split="train")

        train_rows = read_saved_rows(Path(train_output.path))
        eval_rows = read_saved_rows(Path(eval_output.path))
        combined_rows = train_rows + eval_rows

        assert len(train_rows) == 3
        assert len(eval_rows) == 2
        assert all(set(row) == {"prompt", "completion"} for row in combined_rows)
        assert all(row["prompt"].startswith("Translate the following to Yoda speak: ") for row in combined_rows)
        assert {
            (row["prompt"], row["completion"])
            for row in combined_rows
        } == {
            (
                f"Translate the following to Yoda speak: {row['sentence']}",
                row["translation_extra"],
            )
            for row in sample_rows()
        }
