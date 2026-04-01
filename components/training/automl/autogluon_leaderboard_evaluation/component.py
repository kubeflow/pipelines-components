from pathlib import Path
from typing import List, NamedTuple

from kfp import dsl

_COMPONENT_DIR = Path(__file__).parent


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
    embedded_artifact_path=str(_COMPONENT_DIR),
)
def leaderboard_evaluation(
    models: List[dsl.Model],
    eval_metric: str,
    html_artifact: dsl.Output[dsl.HTML],
    embedded_artifact: dsl.EmbeddedInput[dsl.Artifact],
) -> NamedTuple("outputs", best_model=str):
    """Evaluate multiple AutoGluon models and generate a leaderboard.

    This component aggregates evaluation results from a list of Model artifacts
    (reading pre-computed metrics from JSON) and generates an HTML-formatted
    leaderboard ranking the models by their performance metrics. Each model
    artifact is expected to contain metrics at
    model.path / model.metadata["display_name"] / metrics / metrics.json.

    Args:
        models: List of Model artifacts with "display_name" in metadata and metrics at model.path/model_name/metrics/metrics.json.
        eval_metric: Metric name for ranking (e.g. "accuracy", "root_mean_squared_error"); leaderboard sorted by it descending.
        html_artifact: Output artifact for the HTML-formatted leaderboard (model names and metrics).
        embedded_artifact: Embedded component files (injected by runtime from embedded_artifact_path); provides leaderboard_html_template.html.

    Raises:
        FileNotFoundError: If any model metrics path cannot be found.
        KeyError: If metadata lacks "display_name" or metrics JSON lacks the eval_metric key.

    Example:
        from kfp import dsl
        from components.training.automl.autogluon_leaderboard_evaluation import (
            leaderboard_evaluation
        )

        @dsl.pipeline(name="model-evaluation-pipeline")
        def evaluation_pipeline(trained_models):
            leaderboard = leaderboard_evaluation(
                models=trained_models,
                eval_metric="root_mean_squared_error",
            )
            return leaderboard
    """  # noqa: E501
    import html as html_module
    import json
    from pathlib import Path

    import pandas as pd

    # Input validation
    if not isinstance(eval_metric, str) or not eval_metric.strip():
        raise TypeError("eval_metric must be a non-empty string.")
    if not isinstance(models, list) or len(models) == 0:
        raise TypeError("models must be a non-empty list.")

    def _build_leaderboard_table(df: pd.DataFrame) -> str:
        """Build table HTML with Notebook and Predictor as separate columns (raw URI as link text)."""
        display_cols = [c for c in df.columns if c not in ("notebook", "predictor")]
        rows = []
        rows.append(
            "<thead><tr>"
            + "".join(f"<th>{html_module.escape(str(c))}</th>" for c in [df.index.name or "rank"] + display_cols)
            + "<th>Notebook</th><th>Predictor</th></tr></thead><tbody>"
        )
        for idx, row in df.iterrows():
            cells = [f"<td>{html_module.escape(str(idx))}</td>"]
            for col in display_cols:
                val = row[col]
                cells.append(f"<td>{html_module.escape(str(val))}</td>")
            notebook_uri = html_module.escape(str(row["notebook"]))
            predictor_uri = html_module.escape(str(row["predictor"]))
            cells.append(
                f'<td class="uri-cell">'
                f'<a href="{notebook_uri}" class="uri-link" data-uri="{notebook_uri}" target="_blank" rel="noopener">URI</a>'  # noqa: E501
                f'<div class="uri-popover" role="dialog" aria-label="URI" hidden>'
                f'<pre class="uri-popover-text"></pre>'
                f'<button type="button" class="uri-popover-close" aria-label="Close">×</button>'
                f"</div></td>"
            )
            cells.append(
                f'<td class="uri-cell">'
                f'<a href="{predictor_uri}" class="uri-link" data-uri="{predictor_uri}" target="_blank" rel="noopener">URI</a>'  # noqa: E501
                f'<div class="uri-popover" role="dialog" aria-label="URI" hidden>'
                f'<pre class="uri-popover-text"></pre>'
                f'<button type="button" class="uri-popover-close" aria-label="Close">×</button>'
                f"</div></td>"
            )
            rows.append("<tr>" + "".join(cells) + "</tr>")
        return "<table>" + "".join(rows) + "</tbody></table>"

    def _build_leaderboard_html(
        template_path: Path,
        table_html: str,
        eval_metric: str,
        best_model_name: str,
        num_models: int,
    ) -> str:
        """Build leaderboard HTML from embedded template."""
        with Path(template_path).open("r", encoding="utf-8") as f:
            template = f.read()
        return (
            template.replace("__TABLE_HTML__", table_html)
            .replace("__NUM_MODELS__", str(num_models))
            .replace("__EVAL_METRIC__", eval_metric)
            .replace("__BEST_MODEL_NAME__", best_model_name)
        )

    def _round_metrics(metrics: dict, decimals: int = 4) -> dict:
        """Round numeric values in a metrics dict to the given number of decimals."""
        return {k: round(v, decimals) if isinstance(v, (int, float)) else v for k, v in metrics.items()}

    if not models:
        raise ValueError("At least one model is required")

    results = []
    for model in models:
        metrics_path = Path(model.path) / model.metadata["display_name"] / "metrics" / "metrics.json"
        with metrics_path.open("r") as f:
            eval_results = json.load(f)
        display_name = model.metadata["display_name"]
        model_uri = f"{model.uri.rstrip('/')}/{display_name}"
        predictor_uri = f"{model_uri}/predictor/predictor.pkl"
        notebook_uri = f"{model_uri}/notebooks/automl_predictor_notebook.ipynb"
        results.append(
            {
                "model": display_name,
                **_round_metrics(eval_results),
                "notebook": notebook_uri,
                "predictor": predictor_uri,
            }
        )

    # Notice: AutoGluon follows the "higher is better" strategy for all metrics.
    # This means that some metrics—like log_loss and root_mean_squared_error—will have their signs FLIPPED and are shown as negative. # noqa: E501
    # This is to ensure that a higher value always means a better model, so users do not need to know about the metric's normal directionality when interpreting the leaderboard. # noqa: E501
    leaderboard_df = pd.DataFrame(results).sort_values(by=eval_metric, ascending=False)
    n = len(leaderboard_df)
    leaderboard_df.index = pd.RangeIndex(start=1, stop=n + 1, name="rank")

    html_table = _build_leaderboard_table(leaderboard_df)

    best_model_name = leaderboard_df.iloc[0]["model"]
    template_path = Path(embedded_artifact.path) / "leaderboard_html_template.html"
    html_content = _build_leaderboard_html(
        template_path=template_path,
        table_html=html_table,
        eval_metric=eval_metric,
        best_model_name=best_model_name,
        num_models=len(leaderboard_df),
    )
    with open(html_artifact.path, "w", encoding="utf-8") as f:
        f.write(html_content)

    html_artifact.metadata["data"] = leaderboard_df.to_dict()
    html_artifact.metadata["display_name"] = "automl_leaderboard"
    return NamedTuple("outputs", best_model=str)(best_model=best_model_name)


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        leaderboard_evaluation,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
