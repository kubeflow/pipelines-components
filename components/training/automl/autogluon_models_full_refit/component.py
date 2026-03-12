from typing import NamedTuple, Optional

from kfp import dsl


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
)
def autogluon_models_full_refit(
    model_name: str,
    test_dataset: dsl.Input[dsl.Dataset],
    predictor_path: str,
    pipeline_name: str,
    run_id: str,
    sample_row: str,
    model_artifact: dsl.Output[dsl.Model],
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

    # TODO: Move to build package in next stages
    # NOTE: The generated notebook expects that a connection secret is available in the environment where it is run.
    # This connection should provide the same environment variables as required by the pipeline input secret,
    # i.e. AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, and AWS_DEFAULT_REGION,
    # plus the variable AWS_S3_BUCKET for S3 bucket access.

    REGRESSION = {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "a12d957a-c313-4e92-9578-44f6a48560d5",
                "metadata": {},
                "source": [
                    "![AutoML Banner](data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAxNzk2IDEwMCIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgMTc5NiAxMDA7IiB4bWw6c3BhY2U9InByZXNlcnZlIj4KPHN0eWxlIHR5cGU9InRleHQvY3NzIj4KCS5zdDB7ZmlsbC1ydWxlOmV2ZW5vZGQ7Y2xpcC1ydWxlOmV2ZW5vZGQ7ZmlsbDp1cmwoI1NWR0lEXzFfKTt9Cgkuc3Qxe2ZpbGw6bm9uZTtzdHJva2U6I0ZGRkZGRjtzdHJva2Utd2lkdGg6MjtzdHJva2UtbWl0ZXJsaW1pdDoxMDt9Cgkuc3Qye2ZpbGw6bm9uZTtzdHJva2U6I0ZGRkZGRjtzdHJva2Utd2lkdGg6MS41O3N0cm9rZS1taXRlcmxpbWl0OjEwO30KCS5zdDN7ZmlsbDojRkZGRkZGO30KCS5zdDR7Zm9udC1mYW1pbHk6J0hlbHZldGljYSBOZXVlJywgQXJpYWwsIHNhbnMtc2VyaWY7fQoJLnN0NXtmb250LXNpemU6MzJweDt9Cgkuc3Q2e2ZpbGw6IzNEM0QzRDt9Cgkuc3Q3e2ZpbGw6IzkzOTU5ODt9Cgkuc3Q4e29wYWNpdHk6MC4yO2ZpbGw6dXJsKCNTVkdJRF8yXyk7ZW5hYmxlLWJhY2tncm91bmQ6bmV3O30KCS5zdDl7Zm9udC13ZWlnaHQ6NTAwO30KPC9zdHlsZT4KPHJlY3Qgd2lkdGg9IjE3OTYiIGhlaWdodD0iMTAwIiBmaWxsPSIjMTYxNjE2Ii8+CjxsaW5lYXJHcmFkaWVudCBpZD0iU1ZHSURfMV8iIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIiB4MT0iNDIuODYiIHkxPSI1MCIgeDI9Ijc5LjcxIiB5Mj0iNTAiPgoJPHN0b3Agb2Zmc2V0PSIwIiBzdHlsZT0ic3RvcC1jb2xvcjojRkY2QjZCIi8+Cgk8c3RvcCBvZmZzZXQ9IjAuMjEiIHN0eWxlPSJzdG9wLWNvbG9yOiNFRTAwMDAiLz4KCTxzdG9wIG9mZnNldD0iMC43NSIgc3R5bGU9InN0b3AtY29sb3I6I0NDMDAwMCIvPgoJPHN0b3Agb2Zmc2V0PSIxIiBzdHlsZT0ic3RvcC1jb2xvcjojQUEwMDAwIi8+CjwvbGluZWFyR3JhZGllbnQ+CjwhLS0gQXV0b01MIEljb24vTG9nbyBwbGFjZWhvbGRlciAtIHNpbXBsaWZpZWQgZ2VvbWV0cmljIHNoYXBlIC0tPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNNTIuNCw0NS45YzAtMi4zLDEuOC00LjEsNC4xLTQuMXM0LjEsMS44LDQuMSw0LjFTNTguOCw1MCw1Ni41LDUwbDAsMGMtMi4yLDAuMS00LTEuNy00LjEtMy45CglDNTIuNCw0Niw1Mi40LDQ2LDUyLjQsNDUuOXogTTc3LjUsNTIuNWMtMC44LTEuMS0xLjQtMi4zLTEuOS0zLjVjMS4yLTQuNSwwLjctOC42LTEuOC0xMS45Yy0yLjktMy44LTguMi02LTE0LjUtNi4xCgljLTQuNS0wLjEtOC44LDEuNy0xMiw0LjhjLTMsMy00LjYsNy4yLTQuNSwxMS41Yy0wLjEsMi45LDAuOSw1LjgsMi43LDguMWMwLjgsMC44LDEuMywxLjksMS40LDN2NC41Yy0wLjgsMC41LTEuNCwxLjMtMS40LDIuMwoJYzAuMiwxLjUsMS41LDIuNiwzLDIuNGMxLjItMC4yLDIuMi0xLjEsMi40LTIuNGMwLTEtMC41LTEuOS0xLjQtMi4zdi00LjVjMC0yLTEtMy4zLTEuOS00LjZjLTEuNS0xLjktMi4yLTQuMi0yLjEtNi41CgljMC0zLjUsMS40LTYuOSwzLjgtOS40YzIuNy0yLjcsNi4zLTQuMSwxMC00LjFjNS41LDAsOS44LDEuOSwxMi4xLDVjMiwyLjgsMi41LDYuMywxLjQsOS42Yy0wLjQsMS4yLDAuNiwyLjcsMi4zLDUuNgoJYzAuNiwwLjksMS4yLDEuOSwxLjYsMi45Yy0wLjksMC43LTIsMS4yLTMuMSwxLjVjLTAuNSwwLjQtMC43LDAuOS0wLjgsMS41VjY1YzAsMC40LTAuMSwwLjgtMC40LDEuMWMtMC4zLDAuMi0wLjcsMC4zLTEuMSwwLjMKCWMtMS42LTAuMy0zLjQtMC43LTUuMi0xLjF2LTQuOGMwLjgtMC41LDEuNC0xLjQsMS40LTIuM2MwLTEuNS0xLjItMi43LTIuNy0yLjdzLTIuNywxLjItMi43LDIuN2MwLDEsMC41LDEuOSwxLjQsMi4zdjQuMQoJYy0wLjQtMC4xLTAuNy0wLjEtMS4xLTAuM2MtNC41LTEuMS00LjUtMi42LTQuNS0zLjR2LTguM2MzLjItMC43LDUuNC0zLjUsNS41LTYuN2MtMC4xLTMuOC0zLjMtNi43LTcuMS02LjZjLTMuNiwwLjEtNi40LDMtNi42LDYuNgoJYzAsMy4yLDIuMyw2LDUuNSw2Ljd2OC4zYzAsMiwwLjcsNC42LDYuNiw2LjFjMywwLjgsNiwxLjUsOS4xLDEuOWMwLjMsMCwwLjYsMC4xLDAuOCwwLjFjMSwwLDEuOS0wLjMsMi42LTEKCWMwLjktMC44LDEuNC0xLjksMS40LTMuMXYtNC41YzItMC44LDQuMS0yLDQuMS0zLjdDNzkuNyw1NS45LDc5LDU0LjYsNzcuNSw1Mi41eiIvPgo8Y2lyY2xlIGNsYXNzPSJzdDEiIGN4PSI1Ni41IiBjeT0iNDUuOSIgcj0iNS40Ii8+CjxjaXJjbGUgY2xhc3M9InN0MiIgY3g9IjQ4LjMiIGN5PSI2NSIgcj0iMS42Ii8+CjxjaXJjbGUgY2xhc3M9InN0MiIgY3g9IjY0LjgiIGN5PSI1OC4yIiByPSIxLjYiLz4KPHRleHQgdHJhbnNmb3JtPSJtYXRyaXgoMSAwIDAgMSAxMDEuMDIgNTkuMzMpIiBjbGFzcz0ic3QzIHN0NCBzdDUiPkF1dG9NTDwvdGV4dD4KPHJlY3QgeD0iMjMxLjEiIHk9IjM0IiBjbGFzcz0ic3Q2IiB3aWR0aD0iMSIgaGVpZ2h0PSIzMiIvPgo8dGV4dCB0cmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAxIDI1Ni4yOSA1OS42NikiIGNsYXNzPSJzdDcgc3Q0IHN0NSI+UGFydCBvZiBSZWQgSGF0IE9wZW5TaGlmdCBBSTwvdGV4dD4KPGxpbmVhckdyYWRpZW50IGlkPSJTVkdJRF8yXyIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiIHgxPSI3NzMuOCIgeTE9IjUwIiB4Mj0iMTc5NiIgeTI9IjUwIj4KCTxzdG9wIG9mZnNldD0iMCIgc3R5bGU9InN0b3AtY29sb3I6IzE2MTYxNiIvPgoJPHN0b3Agb2Zmc2V0PSIwLjUyIiBzdHlsZT0ic3RvcC1jb2xvcjojRkY2QjZCIi8+Cgk8c3RvcCBvZmZzZXQ9IjAuNjIiIHN0eWxlPSJzdG9wLWNvbG9yOiNFRTAwMDAiLz4KCTxzdG9wIG9mZnNldD0iMC44OCIgc3R5bGU9InN0b3AtY29sb3I6I0NDMDAwMCIvPgoJPHN0b3Agb2Zmc2V0PSIxIiBzdHlsZT0ic3RvcC1jb2xvcjojQUEwMDAwIi8+CjwvbGluZWFyR3JhZGllbnQ+CjxyZWN0IHg9Ijc3My44IiBjbGFzcz0ic3Q4IiB3aWR0aD0iMTAyMi4yIiBoZWlnaHQ9IjEwMCIvPgo8dGV4dCB0cmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAxIDE0NDguMTY0MSA1OS40NikiIGNsYXNzPSJzdDMgc3Q0IHN0NSBzdDkiPlByZWRpY3RvciBOb3RlYm9vazwvdGV4dD4KPC9zdmc+Cg==)"  # noqa: E501
                ],
            },
            {
                "cell_type": "markdown",
                "id": "0e9aa72f",
                "metadata": {},
                "source": [
                    "## Notebook content\n",
                    "\n",
                    "This notebook lets you review the experiment leaderboard for insights into trained model evaluation quality, load a chosen AutoGluon model from S3, and run predictions. \n",  # noqa: E501
                    "\n",
                    "\n",
                    " \U0001f4a1 **Tips:**\n",
                    "- Ensure the S3 connection to pipeline run results is configured so the notebook can access run artifacts.\n",  # noqa: E501
                    "- The model name must match one of the models listed in the leaderboard (the **model** column).\n",
                    "\n",
                    "### Contents\n",
                    "This notebook contains the following parts:\n",
                    "\n",
                    "**[Setup](#setup)**  \n",
                    "**[Experiment run details](#experiment-run-details)**  \n",
                    "**[Download trained model](#download-trained-model)**  \n",
                    "**[Model insights](#model-insights)**  \n",
                    "**[Load the predictor](#load-the-predictor)**  \n",
                    "**[Predict the values](#predict-the-values)**  \n",
                    "**[Summary and next steps](#summary-and-next-steps)**",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "a7d9cf2b-18cc-4ac9-87af-a74f8bf60322",
                "metadata": {},
                "source": ['<a id="setup"></a>\n', "## Setup"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "5bacd972",
                "metadata": {},
                "outputs": [],
                "source": ["import warnings\n", "\n", 'warnings.filterwarnings("ignore")'],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "cec84205-8ee9-4aaf-a97e-4ef576e7b9da",
                "metadata": {},
                "outputs": [],
                "source": [
                    "%pip install autogluon.tabular==1.5.0 | tail -n 1\n",
                    "%pip install catboost==1.2.8 | tail -n 1\n",
                    "%pip install fastai==2.8.5 | tail -n 1\n",
                    "%pip install lightgbm==4.6.0 | tail -n 1\n",
                    "%pip install torch==2.9.1 | tail -n 1\n",
                    "%pip install xgboost==3.1.3 | tail -n 1\n",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "e8ff506e-f1a3-4990-a979-7790a5105251",
                "metadata": {},
                "source": [
                    '<a id="experiment-run-details"></a>\n',
                    "## Experiment run details\n",
                    "\n",
                    "Set the pipeline name and run ID that identify the training run whose artifacts you want to load. These values are typically available from the pipeline run or workbench.",  # noqa: E501
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "fa7f736d-0b5c-4988-87a5-4d1a5cde0873",
                "metadata": {},
                "outputs": [],
                "source": [
                    'pipeline_name = "<REPLACE_PIPELINE_NAME>"\n',
                    'run_id = "<REPLACE_RUN_ID>"\n',
                    'model_name = "<REPLACE_MODEL_NAME>"',
                ],
            },
            {
                "cell_type": "markdown",
                "id": "54525a94-7799-41cc-822e-91bae88b3b78",
                "metadata": {},
                "source": [
                    '<a id="download-trained-model"></a>\n',
                    "## Download trained model\n",
                    "\n",
                    " \U0001f4cc **Action:** Ensure the S3 connection is added to the workbench so the notebook can access the results.",  # noqa: E501
                ],
            },
            {
                "cell_type": "markdown",
                "id": "fba16ca7-b15f-4d7a-95b4-d3cf73163440",
                "metadata": {},
                "source": ["Download model binaries and metrics."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "e88370df-ecda-453d-913a-9524088ccc36",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import boto3\n",
                    "import os\n",
                    "\n",
                    "s3 = boto3.resource('s3', endpoint_url=os.environ['AWS_S3_ENDPOINT'])\n",
                    "bucket = s3.Bucket(os.environ['AWS_S3_BUCKET'])\n",
                    "\n",
                    'full_refit_prefix = os.path.join(pipeline_name, run_id, "autogluon-models-full-refit")\n',
                    'best_model_subpath = os.path.join("model_artifact", model_name)\n',
                    "best_model_path = None\n",
                    "local_dir = None\n",
                    "\n",
                    "for obj in bucket.objects.filter(Prefix=full_refit_prefix):\n",
                    "    if best_model_subpath in obj.key:\n",
                    "        target = obj.key if local_dir is None else os.path.join(local_dir, obj.key)\n",
                    "        if not os.path.exists(os.path.dirname(target)):\n",
                    "            os.makedirs(os.path.dirname(target))\n",
                    "        if obj.key[-1] == '/':\n",
                    "            continue\n",
                    "        bucket.download_file(obj.key, target)\n",
                    "        best_model_path = os.path.join(obj.key.split(model_name)[0], model_name)\n",
                    "\n",
                    'print("Model artifact stored under", best_model_path)',
                ],
            },
            {
                "cell_type": "markdown",
                "id": "cf53ddb3-14af-44e2-9c5d-6636095cb2b5",
                "metadata": {},
                "source": [
                    '<a id="model-insights"></a>\n',
                    "## Model insights\n",
                    "\n",
                    "Display the metrics and features importances for selected model.",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "1df774b4",
                "metadata": {},
                "source": ["### Metrics\n", "Metrics determined on the basis of test data."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "f71f38c1",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "import json\n",
                    "\n",
                    'with open(os.path.join(best_model_path, "metrics", "metrics.json")) as f:\n',
                    "    metrics = pd.json_normalize(json.load(f))\n",
                    "\n",
                    "metrics",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "cc4f419b-2e28-406c-932b-de43182bef31",
                "metadata": {},
                "source": ["### Feature importance\n", "Top ten are displayed."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "0a7417fa-396f-4d83-ba20-1df01a3c0e2a",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "\n",
                    'feature_importance = pd.read_json(os.path.join(best_model_path, "metrics", "feature_importance.json"))\n',  # noqa: E501
                    "feature_importance.head(10)",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "6686ef6f-3251-43fa-bc9d-a9e911c7908c",
                "metadata": {},
                "source": [
                    '<a id="load-the-predictor"></a>\n',
                    "## Load the predictor\n",
                    "\n",
                    "Load the trained model as a TabularPredictor object.",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "9ebc576f-17eb-49a7-8dcb-6b237dcc2218",
                "metadata": {},
                "outputs": [],
                "source": [
                    "from autogluon.tabular import TabularPredictor\n",
                    "\n",
                    'predictor = TabularPredictor.load(os.path.join(best_model_path, "predictor"))',
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "57cc1e1a-707f-431f-9cb5-1d24e09d1249",
                "metadata": {},
                "outputs": [],
                "source": ["predictor.feature_metadata.to_dict()"],
            },
            {
                "cell_type": "markdown",
                "id": "064c76e4-1b44-4bba-8f2b-3178633a326a",
                "metadata": {},
                "source": [
                    '<a id="predict-the-values"></a>\n',
                    "## Predict the values\n",
                    "\n",
                    "Use sample records to predict values. ",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "d6955253-1891-4ff7-8b3e-ffa338d928f8",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "\n",
                    "score_data = <REPLACE_SAMPLE_ROW>\n",
                    "score_df = pd.DataFrame(data=score_data)\n",
                    "score_df.head()",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "f07e1d71-85e8-4484-877a-5af40547de4f",
                "metadata": {},
                "source": ["Predict the values using `predict` method."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "8441133b-2984-4ea9-92a1-4e427d25ee1b",
                "metadata": {},
                "outputs": [],
                "source": ["predictor.predict(score_df)"],
            },
            {
                "cell_type": "markdown",
                "id": "7ee6d313-4612-4fb9-bee2-b2dcc83772ef",
                "metadata": {},
                "source": [
                    '<a id="summary-and-next-steps"></a>\n',
                    "## Summary and next steps\n",
                    "\n",
                    "**Summary:** This notebook loaded a trained AutoGluon model from S3 and ran predictions on sample data using `predict_proba`.\n",  # noqa: E501
                    "\n",
                    "**Next steps:**\n",
                    "- Run predictions on your own data (ensure columns match the training schema).\n",
                    "- Try another model from the leaderboard by changing `model_name` and re-running the download and load cells.\n",  # noqa: E501
                    "- Optionally create the Predictor online deployment using Kserve custom runtime.",
                ],
            },
            {"cell_type": "markdown", "id": "44a650c8-e5cc-4a2e-bebd-becd73944489", "metadata": {}, "source": ["---"]},
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3.12", "language": "python", "name": "python3"},
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.12.9",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    CLASSIFICATION = {
        "cells": [
            {
                "cell_type": "markdown",
                "id": "a12d957a-c313-4e92-9578-44f6a48560d5",
                "metadata": {},
                "source": [
                    "![AutoML Banner](data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IgoJIHZpZXdCb3g9IjAgMCAxNzk2IDEwMCIgc3R5bGU9ImVuYWJsZS1iYWNrZ3JvdW5kOm5ldyAwIDAgMTc5NiAxMDA7IiB4bWw6c3BhY2U9InByZXNlcnZlIj4KPHN0eWxlIHR5cGU9InRleHQvY3NzIj4KCS5zdDB7ZmlsbC1ydWxlOmV2ZW5vZGQ7Y2xpcC1ydWxlOmV2ZW5vZGQ7ZmlsbDp1cmwoI1NWR0lEXzFfKTt9Cgkuc3Qxe2ZpbGw6bm9uZTtzdHJva2U6I0ZGRkZGRjtzdHJva2Utd2lkdGg6MjtzdHJva2UtbWl0ZXJsaW1pdDoxMDt9Cgkuc3Qye2ZpbGw6bm9uZTtzdHJva2U6I0ZGRkZGRjtzdHJva2Utd2lkdGg6MS41O3N0cm9rZS1taXRlcmxpbWl0OjEwO30KCS5zdDN7ZmlsbDojRkZGRkZGO30KCS5zdDR7Zm9udC1mYW1pbHk6J0hlbHZldGljYSBOZXVlJywgQXJpYWwsIHNhbnMtc2VyaWY7fQoJLnN0NXtmb250LXNpemU6MzJweDt9Cgkuc3Q2e2ZpbGw6IzNEM0QzRDt9Cgkuc3Q3e2ZpbGw6IzkzOTU5ODt9Cgkuc3Q4e29wYWNpdHk6MC4yO2ZpbGw6dXJsKCNTVkdJRF8yXyk7ZW5hYmxlLWJhY2tncm91bmQ6bmV3O30KCS5zdDl7Zm9udC13ZWlnaHQ6NTAwO30KPC9zdHlsZT4KPHJlY3Qgd2lkdGg9IjE3OTYiIGhlaWdodD0iMTAwIiBmaWxsPSIjMTYxNjE2Ii8+CjxsaW5lYXJHcmFkaWVudCBpZD0iU1ZHSURfMV8iIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIiB4MT0iNDIuODYiIHkxPSI1MCIgeDI9Ijc5LjcxIiB5Mj0iNTAiPgoJPHN0b3Agb2Zmc2V0PSIwIiBzdHlsZT0ic3RvcC1jb2xvcjojRkY2QjZCIi8+Cgk8c3RvcCBvZmZzZXQ9IjAuMjEiIHN0eWxlPSJzdG9wLWNvbG9yOiNFRTAwMDAiLz4KCTxzdG9wIG9mZnNldD0iMC43NSIgc3R5bGU9InN0b3AtY29sb3I6I0NDMDAwMCIvPgoJPHN0b3Agb2Zmc2V0PSIxIiBzdHlsZT0ic3RvcC1jb2xvcjojQUEwMDAwIi8+CjwvbGluZWFyR3JhZGllbnQ+CjwhLS0gQXV0b01MIEljb24vTG9nbyBwbGFjZWhvbGRlciAtIHNpbXBsaWZpZWQgZ2VvbWV0cmljIHNoYXBlIC0tPgo8cGF0aCBjbGFzcz0ic3QwIiBkPSJNNTIuNCw0NS45YzAtMi4zLDEuOC00LjEsNC4xLTQuMXM0LjEsMS44LDQuMSw0LjFTNTguOCw1MCw1Ni41LDUwbDAsMGMtMi4yLDAuMS00LTEuNy00LjEtMy45CglDNTIuNCw0Niw1Mi40LDQ2LDUyLjQsNDUuOXogTTc3LjUsNTIuNWMtMC44LTEuMS0xLjQtMi4zLTEuOS0zLjVjMS4yLTQuNSwwLjctOC42LTEuOC0xMS45Yy0yLjktMy44LTguMi02LTE0LjUtNi4xCgljLTQuNS0wLjEtOC44LDEuNy0xMiw0LjhjLTMsMy00LjYsNy4yLTQuNSwxMS41Yy0wLjEsMi45LDAuOSw1LjgsMi43LDguMWMwLjgsMC44LDEuMywxLjksMS40LDN2NC41Yy0wLjgsMC41LTEuNCwxLjMtMS40LDIuMwoJYzAuMiwxLjUsMS41LDIuNiwzLDIuNGMxLjItMC4yLDIuMi0xLjEsMi40LTIuNGMwLTEtMC41LTEuOS0xLjQtMi4zdi00LjVjMC0yLTEtMy4zLTEuOS00LjZjLTEuNS0xLjktMi4yLTQuMi0yLjEtNi41CgljMC0zLjUsMS40LTYuOSwzLjgtOS40YzIuNy0yLjcsNi4zLTQuMSwxMC00LjFjNS41LDAsOS44LDEuOSwxMi4xLDVjMiwyLjgsMi41LDYuMywxLjQsOS42Yy0wLjQsMS4yLDAuNiwyLjcsMi4zLDUuNgoJYzAuNiwwLjksMS4yLDEuOSwxLjYsMi45Yy0wLjksMC43LTIsMS4yLTMuMSwxLjVjLTAuNSwwLjQtMC43LDAuOS0wLjgsMS41VjY1YzAsMC40LTAuMSwwLjgtMC40LDEuMWMtMC4zLDAuMi0wLjcsMC4zLTEuMSwwLjMKCWMtMS42LTAuMy0zLjQtMC43LTUuMi0xLjF2LTQuOGMwLjgtMC41LDEuNC0xLjQsMS40LTIuM2MwLTEuNS0xLjItMi43LTIuNy0yLjdzLTIuNywxLjItMi43LDIuN2MwLDEsMC41LDEuOSwxLjQsMi4zdjQuMQoJYy0wLjQtMC4xLTAuNy0wLjEtMS4xLTAuM2MtNC41LTEuMS00LjUtMi42LTQuNS0zLjR2LTguM2MzLjItMC43LDUuNC0zLjUsNS41LTYuN2MtMC4xLTMuOC0zLjMtNi43LTcuMS02LjZjLTMuNiwwLjEtNi40LDMtNi42LDYuNgoJYzAsMy4yLDIuMyw2LDUuNSw2Ljd2OC4zYzAsMiwwLjcsNC42LDYuNiw2LjFjMywwLjgsNiwxLjUsOS4xLDEuOWMwLjMsMCwwLjYsMC4xLDAuOCwwLjFjMSwwLDEuOS0wLjMsMi42LTEKCWMwLjktMC44LDEuNC0xLjksMS40LTMuMXYtNC41YzItMC44LDQuMS0yLDQuMS0zLjdDNzkuNyw1NS45LDc5LDU0LjYsNzcuNSw1Mi41eiIvPgo8Y2lyY2xlIGNsYXNzPSJzdDEiIGN4PSI1Ni41IiBjeT0iNDUuOSIgcj0iNS40Ii8+CjxjaXJjbGUgY2xhc3M9InN0MiIgY3g9IjQ4LjMiIGN5PSI2NSIgcj0iMS42Ii8+CjxjaXJjbGUgY2xhc3M9InN0MiIgY3g9IjY0LjgiIGN5PSI1OC4yIiByPSIxLjYiLz4KPHRleHQgdHJhbnNmb3JtPSJtYXRyaXgoMSAwIDAgMSAxMDEuMDIgNTkuMzMpIiBjbGFzcz0ic3QzIHN0NCBzdDUiPkF1dG9NTDwvdGV4dD4KPHJlY3QgeD0iMjMxLjEiIHk9IjM0IiBjbGFzcz0ic3Q2IiB3aWR0aD0iMSIgaGVpZ2h0PSIzMiIvPgo8dGV4dCB0cmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAxIDI1Ni4yOSA1OS42NikiIGNsYXNzPSJzdDcgc3Q0IHN0NSI+UGFydCBvZiBSZWQgSGF0IE9wZW5TaGlmdCBBSTwvdGV4dD4KPGxpbmVhckdyYWRpZW50IGlkPSJTVkdJRF8yXyIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiIHgxPSI3NzMuOCIgeTE9IjUwIiB4Mj0iMTc5NiIgeTI9IjUwIj4KCTxzdG9wIG9mZnNldD0iMCIgc3R5bGU9InN0b3AtY29sb3I6IzE2MTYxNiIvPgoJPHN0b3Agb2Zmc2V0PSIwLjUyIiBzdHlsZT0ic3RvcC1jb2xvcjojRkY2QjZCIi8+Cgk8c3RvcCBvZmZzZXQ9IjAuNjIiIHN0eWxlPSJzdG9wLWNvbG9yOiNFRTAwMDAiLz4KCTxzdG9wIG9mZnNldD0iMC44OCIgc3R5bGU9InN0b3AtY29sb3I6I0NDMDAwMCIvPgoJPHN0b3Agb2Zmc2V0PSIxIiBzdHlsZT0ic3RvcC1jb2xvcjojQUEwMDAwIi8+CjwvbGluZWFyR3JhZGllbnQ+CjxyZWN0IHg9Ijc3My44IiBjbGFzcz0ic3Q4IiB3aWR0aD0iMTAyMi4yIiBoZWlnaHQ9IjEwMCIvPgo8dGV4dCB0cmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAxIDE0NDguMTY0MSA1OS40NikiIGNsYXNzPSJzdDMgc3Q0IHN0NSBzdDkiPlByZWRpY3RvciBOb3RlYm9vazwvdGV4dD4KPC9zdmc+Cg==)"  # noqa: E501
                ],
            },
            {
                "cell_type": "markdown",
                "id": "0e9aa72f",
                "metadata": {},
                "source": [
                    "## Notebook content\n",
                    "\n",
                    "This notebook lets you load a chosen AutoGluon model from S3, and run predictions. \n",
                    "\n",
                    "\n",
                    " \U0001f4a1 **Tips:**\n",
                    "- Ensure the S3 connection to pipeline run results is configured so the notebook can access run artifacts.\n",  # noqa: E501
                    "- The model name must match one of the models listed in the leaderboard (the **model** column).\n",
                    "\n",
                    "### Contents\n",
                    "This notebook contains the following parts:\n",
                    "\n",
                    "**[Setup](#setup)**  \n",
                    "**[Experiment run details](#experiment-run-details)**  \n",
                    "**[Download trained model](#download-trained-model)**  \n",
                    "**[Model insights](#model-insights)**  \n",
                    "**[Load the predictor](#load-the-predictor)**  \n",
                    "**[Predict the values](#predict-the-values)**  \n",
                    "**[Summary and next steps](#summary-and-next-steps)**",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "a7d9cf2b-18cc-4ac9-87af-a74f8bf60322",
                "metadata": {},
                "source": ['<a id="setup"></a>\n', "## Setup"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "5bacd972",
                "metadata": {},
                "outputs": [],
                "source": ["import warnings\n", "\n", 'warnings.filterwarnings("ignore")'],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "cec84205-8ee9-4aaf-a97e-4ef576e7b9da",
                "metadata": {},
                "outputs": [],
                "source": [
                    "%pip install autogluon.tabular==1.5.0 | tail -n 1\n",
                    "%pip install catboost==1.2.8 | tail -n 1\n",
                    "%pip install fastai==2.8.5 | tail -n 1\n",
                    "%pip install lightgbm==4.6.0 | tail -n 1\n",
                    "%pip install torch==2.9.1 | tail -n 1\n",
                    "%pip install xgboost==3.1.3 | tail -n 1\n",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "e8ff506e-f1a3-4990-a979-7790a5105251",
                "metadata": {},
                "source": [
                    '<a id="experiment-run-details"></a>\n',
                    "## Experiment run details\n",
                    "\n",
                    "Set the pipeline name and run ID that identify the training run whose artifacts you want to load. These values are typically available from the pipeline run or workbench.",  # noqa: E501
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "fa7f736d-0b5c-4988-87a5-4d1a5cde0873",
                "metadata": {},
                "outputs": [],
                "source": [
                    'pipeline_name = "<REPLACE_PIPELINE_NAME>"\n',
                    'run_id =  "<REPLACE_RUN_ID>"\n',
                    'model_name = "<REPLACE_MODEL_NAME>"',
                ],
            },
            {
                "cell_type": "markdown",
                "id": "54525a94-7799-41cc-822e-91bae88b3b78",
                "metadata": {},
                "source": [
                    '<a id="download-trained-model"></a>\n',
                    "## Download trained model\n",
                    "\n",
                    " \U0001f4cc **Action:** Ensure the S3 connection is added to the workbench so the notebook can access the results.",  # noqa: E501
                ],
            },
            {
                "cell_type": "markdown",
                "id": "fba16ca7-b15f-4d7a-95b4-d3cf73163440",
                "metadata": {},
                "source": ["Download model binaries and metrics."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "e88370df-ecda-453d-913a-9524088ccc36",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import boto3\n",
                    "import os\n",
                    "\n",
                    "s3 = boto3.resource('s3', endpoint_url=os.environ['AWS_S3_ENDPOINT'])\n",
                    "bucket = s3.Bucket(os.environ['AWS_S3_BUCKET'])\n",
                    "\n",
                    'full_refit_prefix = os.path.join(pipeline_name, run_id, "autogluon-models-full-refit")\n',
                    'best_model_subpath = os.path.join("model_artifact", model_name)\n',
                    "best_model_path = None\n",
                    "local_dir = None\n",
                    "\n",
                    "for obj in bucket.objects.filter(Prefix=full_refit_prefix):\n",
                    "    if best_model_subpath in obj.key:\n",
                    "        target = obj.key if local_dir is None else os.path.join(local_dir, obj.key)\n",
                    "        if not os.path.exists(os.path.dirname(target)):\n",
                    "            os.makedirs(os.path.dirname(target))\n",
                    "        if obj.key[-1] == '/':\n",
                    "            continue\n",
                    "        bucket.download_file(obj.key, target)\n",
                    "        best_model_path = os.path.join(obj.key.split(model_name)[0], model_name)\n",
                    "\n",
                    'print("Model artifact stored under", best_model_path)',
                ],
            },
            {
                "cell_type": "markdown",
                "id": "cf53ddb3-14af-44e2-9c5d-6636095cb2b5",
                "metadata": {},
                "source": [
                    '<a id="model-insights"></a>\n',
                    "## Model insights\n",
                    "\n",
                    "Display the metrics, confusion matrix and features importances for selected model.",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "b4d8e270-f49f-4a80-a35a-a81699a88d83",
                "metadata": {},
                "source": ["### Metrics\n", "\n", "Metrics determined on the basis of test data."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "e7bc2f23-3def-4c3b-aa95-d5b25e0bca61",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "import json\n",
                    "\n",
                    'with open(os.path.join(best_model_path, "metrics", "metrics.json")) as f:\n',
                    "    metrics = pd.json_normalize(json.load(f))\n",
                    "\n",
                    "metrics",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "72345abd-b419-4f63-8b0b-6d023ddae73b",
                "metadata": {},
                "source": ["### Confusion matrix"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "bd38da24-a764-48e8-9c0c-9285e5810fe1",
                "metadata": {},
                "outputs": [],
                "source": [
                    'confusion_matrix = pd.read_json(os.path.join(best_model_path, "metrics", "confusion_matrix.json"))\n',  # noqa: E501
                    "confusion_matrix.head()",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "cc4f419b-2e28-406c-932b-de43182bef31",
                "metadata": {},
                "source": ["### Feature importance\n", "Top ten are displayed."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "0a7417fa-396f-4d83-ba20-1df01a3c0e2a",
                "metadata": {},
                "outputs": [],
                "source": [
                    'feature_importance = pd.read_json(os.path.join(best_model_path, "metrics", "feature_importance.json"))\n',  # noqa: E501
                    "feature_importance.head(10)",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "6686ef6f-3251-43fa-bc9d-a9e911c7908c",
                "metadata": {},
                "source": [
                    '<a id="load-the-predictor"></a>\n',
                    "## Load the predictor\n",
                    "\n",
                    "Load the trained model as a TabularPredictor object.",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "9ebc576f-17eb-49a7-8dcb-6b237dcc2218",
                "metadata": {},
                "outputs": [],
                "source": [
                    "from autogluon.tabular import TabularPredictor\n",
                    "\n",
                    'predictor = TabularPredictor.load(os.path.join(best_model_path, "predictor"))',
                ],
            },
            {
                "cell_type": "markdown",
                "id": "064c76e4-1b44-4bba-8f2b-3178633a326a",
                "metadata": {},
                "source": [
                    '<a id="predict-the-values"></a>\n',
                    "## Predict the values\n",
                    "\n",
                    "Use sample records to predict values. ",
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "d6955253-1891-4ff7-8b3e-ffa338d928f8",
                "metadata": {},
                "outputs": [],
                "source": [
                    "import pandas as pd\n",
                    "\n",
                    "score_data = <REPLACE_SAMPLE_ROW>\n",
                    "\n",
                    "score_df = pd.DataFrame(data=score_data)\n",
                    "score_df.head()",
                ],
            },
            {
                "cell_type": "markdown",
                "id": "f07e1d71-85e8-4484-877a-5af40547de4f",
                "metadata": {},
                "source": ["Predict the values using `predict_proba` method."],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "8441133b-2984-4ea9-92a1-4e427d25ee1b",
                "metadata": {},
                "outputs": [],
                "source": ["predictor.predict_proba(score_df)"],
            },
            {
                "cell_type": "markdown",
                "id": "7ee6d313-4612-4fb9-bee2-b2dcc83772ef",
                "metadata": {},
                "source": [
                    '<a id="summary-and-next-steps"></a>\n',
                    "## Summary and next steps\n",
                    "\n",
                    "**Summary:** This notebook loaded a trained AutoGluon model from S3 and ran predictions on sample data using `predict_proba`.\n",  # noqa: E501
                    "\n",
                    "**Next steps:**\n",
                    "- Run predictions on your own data (ensure columns match the training schema).\n",
                    "- Try another model from the leaderboard by changing `model_name` and re-running the download and load cells.\n",  # noqa: E501
                    "- Optionally create the Predictor online deployment using Kserve custom runtime.",
                ],
            },
            {"cell_type": "markdown", "id": "44a650c8-e5cc-4a2e-bebd-becd73944489", "metadata": {}, "source": ["---"]},
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3.12", "language": "python", "name": "python3"},
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.12.9",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    problem_type = predictor.problem_type
    match problem_type:
        case "regression":
            notebook = REGRESSION
        case "binary" | "multiclass":
            notebook = CLASSIFICATION
        case _:
            raise ValueError(f"Invalid problem type: {problem_type}")

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
