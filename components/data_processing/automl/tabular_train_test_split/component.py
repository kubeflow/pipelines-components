from typing import NamedTuple, Optional

from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
)
def tabular_train_test_split(  # noqa: D417
    dataset: dsl.Input[dsl.Dataset],
    label_column: str,
    sampled_train_dataset: dsl.Output[dsl.Dataset],
    sampled_test_dataset: dsl.Output[dsl.Dataset],
    split_config: Optional[dict] = None,
    task_type: str = "regression",
) -> NamedTuple("outputs", sample_row=str, split_config=dict):
    """Splits a tabular (CSV) dataset into train and test sets for AutoML workflows.

    The Train Test Split component takes a single CSV dataset and splits it into training and test sets using scikit-learn's `train_test_split`.
    For **regression** tasks the split is random; for **binary** and **multiclass** tasks the split is **stratified** by the label column by default, so that class proportions are preserved in both splits.
    The component writes the train and test CSVs to the output artifacts and returns a sample row (from the test set) and the split configuration.

    By default, the split configuration uses:
      - `test_size`: 0.3 (30% of data for testing)
      - `random_state`: 42 (for reproducibility)
      - `stratify`: True for "binary" and "multiclass" tasks, otherwise None

    You can override these by providing the `split_config` dictionary with the corresponding keys.

    Args:
        dataset: Input CSV dataset to split.
        task_type: Machine learning task type: "binary", "multiclass", or "regression" (default).
        label_column: Name of the label/target column.
        split_config: Split configuration dictionary. Available keys: "test_size" (float), "random_state" (int), "stratify" (bool).
        sampled_train_dataset: Output dataset artifact for the train split.
        sampled_test_dataset: Output dataset artifact for the test split.

    Raises:
        ValueError: If the task_type is not one of "binary", "multiclass", or "regression".

    Returns:
        NamedTuple: Contains a sample row and a split configuration dictionary.
    """  # noqa: E501
    if task_type not in {"multiclass", "binary", "regression"}:
        raise ValueError(f"Invalid task_type: '{task_type}'. Must be one of: 'binary', 'multiclass', or 'regression'.")
    import pandas as pd
    from sklearn.model_selection import train_test_split

    # Set default values
    DEFAULT_RANDOM_STATE = 42
    DEFAULT_TEST_SIZE = 0.3

    split_config = split_config or {}
    test_size = split_config.get("test_size", DEFAULT_TEST_SIZE)
    random_state = split_config.get("random_state", DEFAULT_RANDOM_STATE)

    sampled_train_dataset.uri += ".csv"
    sampled_test_dataset.uri += ".csv"

    X = pd.read_csv(dataset.path)
    # Features and target
    y = X[label_column]
    X.drop(columns=[label_column], inplace=True)

    stratify_effective = task_type != "regression" and split_config.get("stratify", True)

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        stratify=(y if stratify_effective else None),
        random_state=random_state,
    )

    X_y_train = pd.concat([X_train, y_train], axis=1)
    X_y_test = pd.concat([X_test, y_test], axis=1)
    X_y_train.to_csv(sampled_train_dataset.path, index=False)
    X_y_test.to_csv(sampled_test_dataset.path, index=False)

    # Dumps to json string to avoid NaN in the output json
    # Format: '[{"col1": "val1","col2":"val2"},{"col1":"val3","col2":"val4"}]'
    sample_row = X_y_test.head(1).to_json(orient="records")
    return NamedTuple("outputs", sample_row=str, split_config=dict)(
        sample_row=sample_row,
        split_config={
            "test_size": test_size,
            "random_state": random_state,
            "stratify": stratify_effective,
        },
    )


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        tabular_train_test_split,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
