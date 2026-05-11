"""Shared test helpers for yoda_data_processor tests."""

import json
import random
from pathlib import Path


class InMemoryDataset:
    """A tiny dataset double that preserves transformation behavior."""

    def __init__(self, rows: list[dict[str, str]]):
        """Initialize the dataset with a copy of the provided rows."""
        self.rows = [dict(row) for row in rows]

    def __len__(self) -> int:
        """Return the number of rows in the dataset."""
        return len(self.rows)

    def rename_column(self, old_name: str, new_name: str) -> "InMemoryDataset":
        """Return a dataset with one column renamed."""
        return InMemoryDataset(
            [
                {
                    (new_name if key == old_name else key): value
                    for key, value in row.items()
                }
                for row in self.rows
            ]
        )

    def remove_columns(self, columns: list[str]) -> "InMemoryDataset":
        """Return a dataset without the requested columns."""
        columns_to_remove = set(columns)
        return InMemoryDataset(
            [
                {
                    key: value
                    for key, value in row.items()
                    if key not in columns_to_remove
                }
                for row in self.rows
            ]
        )

    def map(self, transform) -> "InMemoryDataset":
        """Return a dataset with the transform applied to each row."""
        return InMemoryDataset([transform(dict(row)) for row in self.rows])

    def train_test_split(self, test_size: float, seed: int) -> dict[str, "InMemoryDataset"]:
        """Split the dataset deterministically into train and test subsets."""
        shuffled_rows = [dict(row) for row in self.rows]
        random.Random(seed).shuffle(shuffled_rows)

        test_count = min(len(shuffled_rows), max(1, int(round(len(shuffled_rows) * test_size))))
        split_index = len(shuffled_rows) - test_count
        return {
            "train": InMemoryDataset(shuffled_rows[:split_index]),
            "test": InMemoryDataset(shuffled_rows[split_index:]),
        }

    def save_to_disk(self, path: str) -> None:
        """Persist rows in a simple JSONL file within the output directory."""
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)
        with output_dir.joinpath("data.jsonl").open("w", encoding="utf-8") as handle:
            for row in self.rows:
                handle.write(json.dumps(row) + "\n")


def sample_rows() -> list[dict[str, str]]:
    """Return a representative input dataset for Yoda processor tests."""
    return [
        {
            "sentence": "Train yourself to let go of everything you fear to lose.",
            "translation_extra": "Let go of everything you fear to lose, train yourself to.",
            "translation": "unused-1",
        },
        {
            "sentence": "Do or do not. There is no try.",
            "translation_extra": "Do or do not. Try, there is not.",
            "translation": "unused-2",
        },
        {
            "sentence": "Named must your fear be before banish it you can.",
            "translation_extra": "Before banish it you can, named must your fear be.",
            "translation": "unused-3",
        },
        {
            "sentence": "Wars not make one great.",
            "translation_extra": "Great, wars make one not.",
            "translation": "unused-4",
        },
        {
            "sentence": "Pass on what you have learned.",
            "translation_extra": "What you have learned, pass on.",
            "translation": "unused-5",
        },
    ]


def read_saved_rows(path: Path) -> list[dict[str, str]]:
    """Load the saved JSONL rows from a component output directory."""
    data_file = path / "data.jsonl"
    return [
        json.loads(line)
        for line in data_file.read_text(encoding="utf-8").splitlines()
        if line
    ]
