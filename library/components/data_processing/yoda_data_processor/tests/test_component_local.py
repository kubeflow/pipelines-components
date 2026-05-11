"""Tests for the yoda_data_processor component."""

import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from ..component import prepare_yoda_dataset
from .support import InMemoryDataset, read_saved_rows, sample_rows


class TestYodaDataProcessorLocalRunner:
    """Test local component execution without a live network dependency."""

    def test_local_execution_writes_expected_outputs(self, setup_and_teardown_subprocess_runner, tmp_path: Path):
        """Exercise the component locally with a stub datasets module and assert on outputs."""
        mock_load_dataset = mock.Mock(return_value=InMemoryDataset(sample_rows()))
        fake_datasets_module = types.ModuleType("datasets")
        fake_datasets_module.load_dataset = mock_load_dataset

        train_output = SimpleNamespace(path=str(tmp_path / "train"))
        eval_output = SimpleNamespace(path=str(tmp_path / "eval"))

        with mock.patch.dict("sys.modules", {"datasets": fake_datasets_module}):
            prepare_yoda_dataset.python_func(
                yoda_train_dataset=train_output,
                yoda_eval_dataset=eval_output,
            )

        mock_load_dataset.assert_called_once_with("dvgodoy/yoda_sentences", split="train")

        train_rows = read_saved_rows(Path(train_output.path))
        eval_rows = read_saved_rows(Path(eval_output.path))

        assert Path(train_output.path).exists()
        assert Path(eval_output.path).exists()
        assert len(train_rows) == 4
        assert len(eval_rows) == 1
        assert train_rows + eval_rows
        assert all(row["prompt"].startswith("Translate the following to Yoda speak: ") for row in train_rows + eval_rows)
