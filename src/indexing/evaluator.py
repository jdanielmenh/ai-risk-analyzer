"""Automated evaluation harness for finance Q&A with rate-shock scenarios.

Computes metrics for RQ1 (efficiency/effectiveness), RQ2 (explainability proxies),
RQ3 (latency) without human subjects.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from riskbot.agent import router_graph
from riskbot.utils.states import ConversationState


NUM_RE = re.compile(r"([-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+\.\d+|[-+]?\d+)")
PCT_RE = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*%")


@dataclass
class EvalConfig:
    dataset_path: str = "eval/questions.jsonl"
    concurrent: int = 2
    max_tasks: int | None = None
    seed: int = 0


def _parse_first_number(text: str) -> float | None:
    # Look for percentage first
    m = PCT_RE.search(text)
    if m:
        try:
            return float(m.group(1)) / 100.0
        except Exception:
            pass
    m2 = NUM_RE.search(text)
    if m2:
        try:
            return float(m2.group(1).replace(",", ""))
        except Exception:
            return None
    return None


def _extract_metrics(answer: str) -> dict[str, float]:
    # Heuristic extraction; projects should add structured output later
    vals: dict[str, float] = {}
    # Try to capture multiple numbers; map by keywords if present
    lowered = answer.lower()
    numbers = [m.group(0) for m in NUM_RE.finditer(answer)]
    # Assign heuristically
    if "coverage" in lowered and numbers:
        vals.setdefault("coverage_post", _parse_first_number(answer) or math.nan)
    if "%" in answer and numbers:
        vals.setdefault(
            "debt_service_pct_post", _parse_first_number(answer) or math.nan
        )
    # Fallback single primary number
    if not vals and numbers:
        vals["primary"] = _parse_first_number(answer) or math.nan
    return vals


def _within_tol(
    pred: float, gold: float, abs_tol: float | None, pct_tol: float | None
) -> bool:
    if math.isnan(pred) or math.isnan(gold):
        return False
    if abs_tol is not None and abs(pred - gold) <= abs_tol:
        return True
    if pct_tol is not None and gold != 0:
        return abs(pred - gold) / abs(gold) <= pct_tol
    return False


async def _run_one(graph, q: dict[str, Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    state: ConversationState = ConversationState(question=q["question"])  # type: ignore[arg-type]
    # Use invoke for sync graph; if graph is async-stream based, adapt here
    result_state = await graph.ainvoke(state)  # type: ignore[attr-defined]
    t1 = time.perf_counter()
    ans = result_state.answer or ""
    metrics = _extract_metrics(ans)
    return {
        "id": q["id"],
        "ticker": q.get("ticker"),
        "bps": q.get("bps"),
        "answer": ans,
        "metrics": metrics,
        "latency_s": t1 - t0,
        "api_results": result_state.api_results or {},
    }


async def evaluate(cfg: EvalConfig | None = None) -> dict[str, Any]:
    if cfg is None:
        cfg = EvalConfig()
    ds_path = Path(cfg.dataset_path)
    rows = []
    with ds_path.open() as f:
        for i, line in enumerate(f):
            if cfg.max_tasks and i >= cfg.max_tasks:
                break
            rows.append(json.loads(line))

    out: list[dict[str, Any]] = []

    async def sem_task(q):
        return await _run_one(router_graph, q)

    for q in rows:
        out.append(await sem_task(q))

    # Scoring (no gold numeric values here; uses presence + heuristic correctness where possible)
    # Projects extending this should plug in a calculator and compare against gold numbers.

    # Simple aggregates
    latencies = [r["latency_s"] for r in out]
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
    summary = {
        "count": len(out),
        "latency_avg_s": sum(latencies) / len(latencies) if latencies else 0.0,
        "latency_p50_s": p50,
    }
    return {"summary": summary, "results": out}


if __name__ == "__main__":
    res = asyncio.run(evaluate())
    print(json.dumps(res["summary"], indent=2))
