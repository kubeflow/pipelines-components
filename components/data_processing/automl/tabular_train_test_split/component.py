from typing import NamedTuple, Optional

from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
)
def tabular_train_test_split(  # noqa: D417
    dataset_path: str,
    label_column: str,
    workspace_path: str,
    sampled_test_dataset: dsl.Output[dsl.Dataset],
    split_config: Optional[dict] = None,
    task_type: str = "regression",
    selection_train_size: float = 0.3,
) -> NamedTuple(
    "outputs", sample_row=str, split_config=dict, models_selection_train_path=str, extra_train_data_path=str
):
    """Splits a tabular (CSV) dataset into test, selection-train, and extra-train sets for AutoML workflows.

    The Train Test Split component takes a single CSV dataset and splits it into three sets:

    1. **Test set** (default 20%): written to the sampled_test_dataset S3 artifact for evaluation.

    2. **Selection train set** (default 30% of the 80% train portion): written to the PVC workspace for model selection.

    3. **Extra train set** (remaining 70% of the 80% train portion): written to the PVC workspace for refit_full.

    For **regression** tasks the split is random; for **binary** and **multiclass** tasks the split is **stratified**
    by the label column by default, so that class proportions are preserved in all splits.

    By default, the split configuration uses:

      - `test_size`: 0.2 (20% of data for testing)

      - `random_state`: 42 (for reproducibility).

      - `stratify`: True for "binary" and "multiclass" tasks, otherwise None

    You can override these by providing the `split_config` dictionary with the corresponding keys.

    Args:
        dataset_path: Path to the input CSV dataset (on PVC workspace).
        task_type: Machine learning task type: "binary", "multiclass", or "regression" (default).
        label_column: Name of the label/target column.
        workspace_path: PVC workspace directory where train CSVs will be written.
        split_config: Split configuration dictionary. Available keys: "test_size" (float), "random_state" (int), "stratify" (bool).
        sampled_test_dataset: Output dataset artifact for the test split.
        selection_train_size: Fraction of the train portion used for model selection (default 0.3).

    Raises:
        ValueError: If the task_type is not one of "binary", "multiclass", or "regression".

    Returns:
        NamedTuple: Contains a sample row, split config, and paths to selection-train and extra-train CSVs.
    """  # noqa: E501
    if task_type not in {"multiclass", "binary", "regression"}:
        raise ValueError(f"Invalid task_type: '{task_type}'. Must be one of: 'binary', 'multiclass', or 'regression'.")
    from pathlib import Path

    import pandas as pd
    from sklearn.model_selection import train_test_split

    # Set default values
    DEFAULT_RANDOM_STATE = 42
    DEFAULT_TEST_SIZE = 0.2

    split_config = split_config or {}
    test_size = split_config.get("test_size", DEFAULT_TEST_SIZE)
    random_state = split_config.get("random_state", DEFAULT_RANDOM_STATE)

    if not sampled_test_dataset.uri or not sampled_test_dataset.uri.endswith(".csv"):
        sampled_test_dataset.uri = (sampled_test_dataset.uri or "sampled_test_dataset") + ".csv"

    X = pd.read_csv(dataset_path)
    # Features and target
    y = X[label_column]
    X.drop(columns=[label_column], inplace=True)

    stratify_effective = task_type != "regression" and split_config.get("stratify", True)

    # Primary split: train vs test
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        stratify=(y if stratify_effective else None),
        random_state=random_state,
    )

    # Secondary split: selection train vs extra train
    X_sel, X_extra, y_sel, y_extra = train_test_split(
        X_train,
        y_train,
        test_size=(1 - selection_train_size),
        stratify=(y_train if stratify_effective else None),
        random_state=random_state,
    )

    X_y_sel = pd.concat([X_sel, y_sel], axis=1)
    X_y_extra = pd.concat([X_extra, y_extra], axis=1)
    X_y_test = pd.concat([X_test, y_test], axis=1)

    # Remove full_dataset from PVC — no longer needed after splitting
    dataset_file = Path(dataset_path)
    if dataset_file.is_file():
        dataset_file.unlink()

    # Write selection train and extra train to PVC workspace
    datasets_dir = Path(workspace_path) / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    models_selection_train_path = str(datasets_dir / "models_selection_train.csv")
    extra_train_data_path = str(datasets_dir / "extra_train_dataset.csv")
    X_y_sel.to_csv(models_selection_train_path, index=False)
    X_y_extra.to_csv(extra_train_data_path, index=False)

    # Write test to S3 artifact
    X_y_test.to_csv(sampled_test_dataset.path, index=False)

    # Dumps to json string to avoid NaN in the output json
    # Format: '[{"col1": "val1","col2":"val2"},{"col1":"val3","col2":"val4"}]'
    sample_row = X_y_test.head(1).to_json(orient="records")
    return NamedTuple(
        "outputs", sample_row=str, split_config=dict, models_selection_train_path=str, extra_train_data_path=str
    )(
        sample_row=sample_row,
        split_config={
            "test_size": test_size,
            "random_state": random_state,
            "stratify": stratify_effective,
        },
        models_selection_train_path=models_selection_train_path,
        extra_train_data_path=extra_train_data_path,
    )


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        tabular_train_test_split,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
