from typing import List, NamedTuple

from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
)
def leaderboard_evaluation(
    models: List[dsl.Model],
    eval_metric: str,
    html_artifact: dsl.Output[dsl.HTML],
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
    import json
    from pathlib import Path

    import pandas as pd

    # Modified theme colors for a lighter look. Only :root CSS vars are changed.
    def _build_leaderboard_html(table_html: str, eval_metric: str, best_model_name: str, num_models: int) -> str:
        """Build a styled HTML document for the leaderboard (lighter theme)."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoML Leaderboard</title>
  <style>
    :root {{
      --bg: #f7fafc;
      --surface: #ffffff;
      --surface-hover: #f1f5f9;
      --border: #dde3eb;
      --text: #23282e;
      --text-muted: #5c6975;
      --accent: #2977ff;
      --radius: 12px;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      padding: 2rem;
      font-family: var(--font);
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      min-height: 100vh;
    }}
    .container {{
      max-width: 960px;
      margin: 0 auto;
    }}
    header {{
      margin-bottom: 2rem;
      padding-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      text-align: center;
    }}
    h1 {{
      margin: 0 0 0.25rem 0;
      font-size: 1.75rem;
      font-weight: 600;
    }}
    h2 {{
      margin: 0 0 0.5rem 0;
      font-size: 1.15rem;
      font-weight: 400;
      color: var(--text-muted);
    }}
    .table-scroll {{
      overflow-x: auto;
      overflow-y: visible;
      width: 100%;
      max-width: 100%;
      -webkit-overflow-scrolling: touch;
      margin-bottom: 2rem;
      border-radius: var(--radius);
      box-shadow: 0 4px 14px 0 #e6eaf1;
    }}
    .table-scroll::-webkit-scrollbar {{
      height: 8px;
    }}
    .table-scroll::-webkit-scrollbar-track {{
      background: var(--surface-hover);
      border-radius: 4px;
    }}
    .table-scroll::-webkit-scrollbar-thumb {{
      background: var(--border);
      border-radius: 4px;
    }}
    .table-scroll::-webkit-scrollbar-thumb:hover {{
      background: var(--text-muted);
    }}
    table {{
      width: 100%;
      min-width: max-content;
      border-collapse: collapse;
      background: var(--surface);
      overflow: hidden;
    }}
    th, td {{
      padding: 0.75rem 1rem;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      background: var(--surface-hover);
      color: var(--text-muted);
      text-transform: uppercase;
      font-size: 0.95rem;
      letter-spacing: 0.03em;
      font-weight: 600;
      border-bottom: 2px solid var(--border);
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    tr:hover {{
      background: var(--surface-hover);
      transition: background 0.08s;
    }}
    .caption {{
      color: var(--text-muted);
      font-size: 0.96em;
      margin-top: -0.8em;
      margin-bottom: 2em;
    }}
    a {{
      color: var(--accent);
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .table-wrapper {{
      display: flex;
      justify-content: center;
      width: 100%;
      max-width: 100%;
    }}
    .table-wrapper .table-scroll {{
      flex: 1 1 auto;
      min-width: 0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>AutoML Model Leaderboard</h1>
      <h2>Ranking top {num_models} models by <b>{eval_metric}</b></h2>
      <div class="caption">
        <span>Best model: <b>{best_model_name}</b></span>
      </div>
    </header>
    <div class="table-wrapper">
    <div class="table-scroll">
    {table_html}
    </div>
    </div>
  </div>
</body>
</html>
"""

    results = []
    for model in models:
        eval_results = json.load(
            (Path(model.path) / model.metadata["display_name"] / "metrics" / "metrics.json").open("r")
        )
        display_name = model.metadata["display_name"]
        model_uri = f"{model.uri.rstrip('/')}/{display_name}"
        predictor_uri = f"{model_uri}/predictor/predictor.pkl"
        notebook_uri = f"{model_uri}/notebooks/automl_predictor_notebook.ipynb"
        results.append(
            {
                "model": display_name,
                **eval_results,
                "notebook": notebook_uri,
                "predictor": predictor_uri,
            }
        )

    leaderboard_df = pd.DataFrame(results).sort_values(by=eval_metric, ascending=False)
    n = len(leaderboard_df)
    leaderboard_df.index = pd.RangeIndex(start=1, stop=n + 1, name="rank")

    html_table = leaderboard_df.to_html(classes=None, border=0, escape=True)

    best_model_name = leaderboard_df.iloc[0]["model"]
    html_content = _build_leaderboard_html(
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
