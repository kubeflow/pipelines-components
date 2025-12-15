from google.auth.exceptions import InvalidValue
from typing import Any

from kfp import dsl
import kfp.compiler


@dsl.component(
    packages_to_install=["datasets"],
)
def prepare_yoda_dataset(
        yoda_input_dataset: str,
        yoda_train_dataset: dsl.Output[dsl.Dataset],
        yoda_eval_dataset: dsl.Output[dsl.Dataset],
        operation_map: dict[str, Any] = {"rename_column": {"sentence":"prompt"}},
        train_split_ratio: float = 0.8,
):
    """Prepare the training and evaluation datasets by downloading and preprocessing.

    Downloads the yoda_sentences dataset from HuggingFace, renames columns to match
    the expected format for training (prompt/completion), splits into train/eval sets,
    and saves them as output artifacts.

    Args:
        yoda_input_dataset (str): Dataset to download from HuggingFace
        yoda_train_dataset (dsl.Output[dsl.Dataset]): Output dataset for training.
        yoda_eval_dataset (dsl.Output[dsl.Dataset]): Output dataset for evaluation.
        operation_map (dict): Specify list of operations you want to perform on the data set before splitting it e.g. {"rename_column": {"sentence":"prompt"}, "remove_columns": "translation"}
        train_split_ratio (float): Ratio of data to use for training (0.0-1.0).
                                  Defaults to 0.8 (80% train, 20% eval).
    """
    from datasets import load_dataset

    print(f"Downloading and loading the dataset from {yoda_input_dataset}")
    dataset = load_dataset(yoda_input_dataset, split="train")
    if operation_map:
        for operation_name, operation_value in operation_map.items():
            print(f'Performing operation: "{operation_name}"')
            if operation_name == 'rename_column':
                if type(operation_value) != dict:
                    raise RuntimeError(f'Dict value is required to perform operation "{operation_name}"')
                for key, value in operation_value.items():
                    dataset = dataset.rename_column(key, value)
            elif operation_name == "remove_columns":
                if type(operation_value) == str:
                    dataset = dataset.remove_columns(["translation"])
                elif type(operation_value) == list:
                    dataset = dataset.remove_columns("translation")
                else:
                    raise RuntimeError(f'Only list and str type are allowed to perform "{operation_name}" operation')
            else:
                raise InvalidValue(f'Unrecogonized operation value "{operation_name}"')

    # Add prefix to prompts
    print("Adding Yoda speak prefix to prompts")
    def add_yoda_prefix(example):
        example["prompt"] = (
                "Translate the following to Yoda speak: " + example["prompt"]
        )
        return example

    dataset = dataset.map(add_yoda_prefix)

    # Split the dataset into train and eval sets
    print(
        f"Splitting dataset with {len(dataset)} rows into train ({train_split_ratio:.1%}) and eval ({(1-train_split_ratio):.1%}) sets"
    )
    split_dataset = dataset.train_test_split(test_size=1 - train_split_ratio, seed=42)

    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]

    print(f"Train set: {len(train_dataset)} rows")
    print(f"Eval set: {len(eval_dataset)} rows")

    # Save both datasets
    print(f"Saving train dataset to {yoda_train_dataset.path}")
    train_dataset.save_to_disk(yoda_train_dataset.path)

    print(f"Saving eval dataset to {yoda_eval_dataset.path}")
    eval_dataset.save_to_disk(yoda_eval_dataset.path)


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(
        prepare_yoda_dataset,
        package_path=__file__.replace(".py", "_component.yaml"),
    )