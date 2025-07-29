from __future__ import annotations

import pathlib

import pytest
from langsmith import Client

from riskbot.agent import classify
from utils.config import load_required_env_vars

load_required_env_vars()

ROOT = pathlib.Path(__file__).resolve().parents[1]
LS = Client(hide_inputs=False, hide_outputs=False)
DATASET_NAME = "Intent/CLS/Gold"
MIN_ACC = 0.90
TOP_K = 40  # Number of examples to evaluate


# ---------------- Target function (traceable) ----------------
def target(inputs: dict) -> dict:
    """Wrap the real classifier so LangSmith can trace each call."""
    return {"label": classify(inputs["question"])}


# ---------------- Row‑level evaluator ----------------
def accuracy(outputs: dict, reference_outputs: dict) -> dict:
    """Exact-match accuracy for a single example."""
    return {"score": outputs["label"].lower() == reference_outputs["label"].lower()}


# ---------------- Summary‑level evaluator ----------------
def aggregate_accuracy(outputs: list[dict], reference_outputs: list[dict]) -> float:
    correct = sum(
        o["label"].lower() == r["label"].lower()
        for o, r in zip(outputs, reference_outputs, strict=False)
    )
    return correct / len(outputs)


# ---------------- Main test ----------------
@pytest.mark.langsmith
def test_classification_accuracy() -> None:
    # 1) Pull the first TOP_K rows as Example objects
    examples = list(LS.list_examples(dataset_name=DATASET_NAME, limit=TOP_K))

    # 2) Run the evaluation
    results = LS.evaluate(
        target,
        data=examples,
        evaluators=[accuracy],
        summary_evaluators=[aggregate_accuracy],
        experiment_prefix="cls-v1-top5",
        max_concurrency=5,
        description=f"Accuracy on the first {TOP_K} rows",
    )

    # 3) Grab the summary metric and assert the threshold
    summary_results = results._summary_results["results"]
    agg_acc = next(r.score for r in summary_results if r.key == "aggregate_accuracy")
    assert agg_acc >= MIN_ACC, f"aggregate accuracy {agg_acc:.3%} < {MIN_ACC:.0%}"
