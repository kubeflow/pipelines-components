"""Run the SDG component locally with an LLM flow and print results."""

import json
import os
import tempfile

import pandas as pd
from component import sdg

# Paths
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DATA = os.path.join(REPO_ROOT, "..", "..", "..", "test_data", "sdg_hub")
INPUT_PATH = os.path.abspath(os.path.join(TEST_DATA, "sample_input.jsonl"))
FLOW_PATH = os.path.abspath(os.path.join(TEST_DATA, "llm_test_flow.yaml"))


class Artifact:
    """Mock KFP artifact with a writable path."""

    def __init__(self, path):
        """Initialize with path."""
        self.path = path


with tempfile.TemporaryDirectory() as tmp_dir:
    output_artifact = Artifact(os.path.join(tmp_dir, "output.jsonl"))
    output_metrics = Artifact(os.path.join(tmp_dir, "metrics.json"))

    print(f"Input:   {INPUT_PATH}")
    print(f"Flow:    {FLOW_PATH}")
    print(f"Output:  {tmp_dir}")
    print()

    sdg.python_func(
        output_artifact=output_artifact,
        output_metrics=output_metrics,
        input_pvc_path=INPUT_PATH,
        flow_yaml_path=FLOW_PATH,
        model="openai/gpt-4o-mini",
        max_concurrency=1,
        temperature=0.7,
        max_tokens=2048,
        checkpoint_pvc_path="",
        save_freq=100,
        log_level="INFO",
        export_to_pvc=False,
        export_path="",
    )

    # Print results
    print("\n" + "=" * 60)
    print("GENERATED OUTPUT")
    print("=" * 60)
    df = pd.read_json(output_artifact.path, lines=True)
    pd.set_option("display.max_colwidth", 80)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))

    print("\n" + "=" * 60)
    print("METRICS")
    print("=" * 60)
    with open(output_metrics.path) as f:
        print(json.dumps(json.load(f), indent=2))
