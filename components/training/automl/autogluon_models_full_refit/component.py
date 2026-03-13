import pathlib
from typing import NamedTuple, Optional

from kfp import dsl

_NOTEBOOKS_DIR = str(pathlib.Path(__file__).parent / "notebook_templates")


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
    packages_to_install=[
        "autogluon.tabular==1.5.0",
        "catboost==1.2.8",
        "fastai==2.8.5",
        "lightgbm==4.6.0",
        "torch==2.9.1",
        "xgboost==3.1.3",
    ],
    embedded_artifact_path=_NOTEBOOKS_DIR,
)
def autogluon_models_full_refit(
    model_name: str,
    test_dataset: dsl.Input[dsl.Dataset],
    predictor_path: str,
    pipeline_name: str,
    run_id: str,
    sample_row: str,
    model_artifact: dsl.Output[dsl.Model],
    notebooks: dsl.EmbeddedInput[dsl.Dataset],
    sampling_config: Optional[dict] = None,
    split_config: Optional[dict] = None,
    model_config: Optional[dict] = None,
    extra_train_data_path: str = "",
) -> NamedTuple("outputs", model_name=str):
    """Refit a specific AutoGluon model on the full training dataset.

    This component takes a trained AutoGluon TabularPredictor, loaded from
    predictor_path, and refits a specific model, identified by model_name, on
    the full training data. When extra_train_data_path is provided, the extra
    training data is loaded and passed to refit_full as train_data_extra. The
    test_dataset is used for evaluation and for writing metrics. The refitted
    model is saved with the suffix "_FULL" appended to model_name.

    Artifacts are written under model_artifact.path in a directory named
    <model_name>_FULL (e.g. LightGBM_BAG_L1_FULL). The layout is:

      - model_artifact.path / <model_name>_FULL / predictor /
      TabularPredictor (predictor.pkl inside); clone with only the refitted model.

      - model_artifact.path / <model_name>_FULL / metrics / metrics.json
      (evaluation results; leaderboard component reads this via display_name/metrics/metrics.json).

      - model_artifact.path / <model_name>_FULL / metrics / feature_importance.json

      - model_artifact.path / <model_name>_FULL / metrics / confusion_matrix.json
      (classification only).

      - model_artifact.path / <model_name>_FULL / notebooks / automl_predictor_notebook.ipynb

    Artifact metadata: display_name (<model_name>_FULL), context (data_config,
    task_type, label_column, model_config, location, metrics), and
    context.location.notebook (path to the notebook). Supported problem types:
    regression, binary, multiclass; any other raises ValueError.

    This component is typically used in a two-stage training pipeline where
    models are first trained on sampled data for exploration, then the best
    candidates are refitted on the full dataset for optimal performance.

    Args:
        model_name: Name of the model to refit (must exist in predictor); refitted model saved with "_FULL" suffix.
        test_dataset: Dataset artifact (CSV) for evaluation and metrics; format should match initial training data.
        predictor_path: Path to the trained TabularPredictor containing model_name.
        sampling_config: Data sampling config (stored in artifact metadata).
        split_config: Data split config (stored in artifact metadata).
        model_config: Model training config (stored in artifact metadata).
        pipeline_name: Pipeline run name; last hyphen-separated segment used in the generated notebook.
        run_id: Pipeline run ID (used in the generated notebook).
        sample_row: JSON list of row objects for example input in the notebook; label column is stripped.
        model_artifact: Output Model; artifacts under model_artifact.path/<model_name>_FULL (predictor/, metrics/, notebooks/).
        extra_train_data_path: Optional path to extra training data CSV (on PVC workspace) passed to refit_full.
        notebooks: Embedded notebook templates (injected by the runtime from the component's embedded_artifact_path).

    Returns:
        NamedTuple with model_name (refitted name with "_FULL" suffix); artifacts written to model_artifact.

    Raises:
        FileNotFoundError: If predictor path or test_dataset path cannot be found.
        ValueError: If predictor load fails, model_name not in predictor, refit fails, or invalid problem_type.
        KeyError: If required model files are missing from the predictor.

    Example:
        from kfp import dsl
        from components.training.automl.autogluon_models_full_refit import (
            autogluon_models_full_refit,
        )

        @dsl.pipeline(name="model-refit-pipeline")
        def refit_pipeline(test_data, predictor_path, pipeline_name, run_id):
            refitted = autogluon_models_full_refit(
                model_name="LightGBM_BAG_L1",
                test_dataset=test_data,
                predictor_path=predictor_path,
                sampling_config={},
                split_config={},
                model_config={},
                pipeline_name=pipeline_name,
                run_id=run_id,
                sample_row='[{"feature1": 1, "target": 1.0}]',
                model_artifact=dsl.Output(type="Model"),
            )
            return refitted.model_name

    """  # noqa: E501
    import json
    import os
    from pathlib import Path

    import pandas as pd
    from autogluon.tabular import TabularPredictor

    sampling_config = sampling_config or {}
    split_config = split_config or {}
    model_config = model_config or {}

    test_dataset_df = pd.read_csv(test_dataset.path)
    extra_train_df = pd.read_csv(extra_train_data_path) if extra_train_data_path else None

    predictor = TabularPredictor.load(predictor_path)

    # save refitted model to output artifact
    model_name_full = model_name + "_FULL"
    output_path = Path(model_artifact.path) / model_name_full

    # set the name of the model artifact and its metadata
    model_artifact.metadata["display_name"] = model_name_full
    model_artifact.metadata["context"] = {}
    model_artifact.metadata["context"]["data_config"] = {
        "sampling_config": sampling_config,
        "split_config": split_config,
    }

    model_artifact.metadata["context"]["task_type"] = predictor.problem_type
    model_artifact.metadata["context"]["label_column"] = predictor.label

    model_artifact.metadata["context"]["model_config"] = model_config
    model_artifact.metadata["context"]["location"] = {
        "model_directory": f"{model_name_full}",
        "predictor": f"{model_name_full}/predictor/predictor.pkl",
    }

    # clone the predictor to the output artifact path and delete unnecessary models
    predictor_clone = predictor.clone(path=output_path / "predictor", return_clone=True, dirs_exist_ok=True)
    predictor_clone.delete_models(models_to_keep=[model_name])

    # refit on training + validation data, optionally with extra training data
    predictor_clone.refit_full(model=model_name, train_data_extra=extra_train_df)

    predictor_clone.set_model_best(model=model_name_full, save_trainer=True)
    predictor_clone.save_space()

    eval_results = predictor_clone.evaluate(test_dataset_df)
    model_artifact.metadata["context"]["metrics"] = {"test_data": eval_results}
    feature_importance = predictor_clone.feature_importance(test_dataset_df)

    # save evaluation results to output artifact
    os.makedirs(str(output_path / "metrics"), exist_ok=True)
    with (output_path / "metrics" / "metrics.json").open("w") as f:
        json.dump(eval_results, f)

    # save feature importance to output artifact
    with (output_path / "metrics" / "feature_importance.json").open("w") as f:
        json.dump(feature_importance.to_dict(), f)

    # generate confusion matrix for classification problem types
    if predictor.problem_type in {"binary", "multiclass"}:
        from autogluon.core.metrics import confusion_matrix

        confusion_matrix_res = confusion_matrix(
            solution=test_dataset_df[predictor.label],
            prediction=predictor_clone.predict(test_dataset_df),
            output_format="pandas_dataframe",
        )
        with (output_path / "metrics" / "confusion_matrix.json").open("w") as f:
            json.dump(confusion_matrix_res.to_dict(), f)

    # Notebook generation

    # NOTE: The generated notebook expects that a connection secret is available in the environment where it is run.
    # This connection should provide the same environment variables as required by the pipeline input secret,
    # i.e. AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, and AWS_DEFAULT_REGION,
    # plus the variable AWS_S3_BUCKET for S3 bucket access.

    problem_type = predictor.problem_type
    match problem_type:
        case "regression":
            notebook_file = "regression_notebook.ipynb"
        case "binary" | "multiclass":
            notebook_file = "classification_notebook.ipynb"
        case _:
            raise ValueError(f"Invalid problem type: {problem_type}")

    import os

    with open(os.path.join(notebooks.path, notebook_file), "r", encoding="utf-8") as f:
        notebook = json.load(f)

    # Improved retrieve_pipeline_name: trims only the run id or suffix
    def retrieve_pipeline_name(pipeline_name: str) -> str:
        """Attempts to infer the original pipeline name from a name that may have a run id or suffix at the end.

        Removes only the last dash-separated element (the run id or variant),
        handling trailing dashes gracefully to avoid dropping real name segments.
        If only a single element exists, returns as is.
        """
        if not pipeline_name:
            return pipeline_name
        # Strip trailing dashes for robust splitting
        name = pipeline_name.rstrip("-")
        if "-" not in name:
            return name
        tokens = name.split("-")
        if len(tokens) <= 1:
            return tokens[0] if tokens else ""
        return "-".join(tokens[:-1])

    pipeline_name = retrieve_pipeline_name(pipeline_name)

    # Replace <REPLACE_RUN_ID>, <REPLACE_PIPELINE_NAME>, <REPLACE_MODEL_NAME>, <REPLACE_SAMPLE_ROW> anywhere in code cells. # noqa: E501
    def replace_placeholder_in_notebook(notebook, replacements):
        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            # Replace in every string of the source list
            new_source = []
            for line in cell.get("source", []):
                for placeholder, value in replacements.items():
                    line = line.replace(placeholder, value)
                new_source.append(line)
            cell["source"] = new_source
        return notebook

    sample_row_list = json.loads(sample_row)

    # remove label column from sample row
    sample_row_formatted = [
        {col: value for col, value in row.items() if col != predictor.label} for row in sample_row_list
    ]

    replacements = {
        "<REPLACE_RUN_ID>": run_id,
        "<REPLACE_PIPELINE_NAME>": pipeline_name,
        "<REPLACE_MODEL_NAME>": model_name_full,
        "<REPLACE_SAMPLE_ROW>": str(sample_row_formatted),
    }
    notebook = replace_placeholder_in_notebook(notebook, replacements)

    notebook_path = output_path / "notebooks"
    notebook_path.mkdir(parents=True, exist_ok=True)
    with (notebook_path / "automl_predictor_notebook.ipynb").open("w", encoding="utf-8") as f:
        json.dump(notebook, f)

    model_artifact.metadata["context"]["location"]["notebook"] = (
        f"{model_name_full}/notebooks/automl_predictor_notebook.ipynb"
    )

    return NamedTuple("outputs", model_name=str)(model_name=model_name_full)


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        autogluon_models_full_refit,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
