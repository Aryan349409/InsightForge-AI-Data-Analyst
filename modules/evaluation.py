"""Benchmark harness: measures NL->SQL execution accuracy, validity rate and latency.

Usage:
    python -m modules.evaluation --data sample_data/sales.csv \
        --questions evaluation/questions_sales.json --provider anthropic
Compare providers/models by running it several times and keeping the CSV outputs.
"""
from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from modules.cleaning import clean
from modules.ingestion import load_file, safe_table_name
from modules.nl2sql import ask, execute_sql


def _normalise(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(tuple(round(float(v), 2) if isinstance(v, (int, float)) and not isinstance(v, bool)
                          else str(v) for v in r))
    return sorted(rows)


def results_match(pred: pd.DataFrame, gold: pd.DataFrame) -> bool:
    """Order-insensitive comparison of result values (column names ignored)."""
    if pred is None or pred.shape != gold.shape:
        return False
    return _normalise(pred) == _normalise(gold)


def run_benchmark(llm, df: pd.DataFrame, table: str, questions: list[dict]) -> pd.DataFrame:
    rows = []
    for q in questions:
        gold = execute_sql(df, table, q["gold_sql"])
        t0 = time.perf_counter()
        r = ask(llm, q["question"], df, table)
        rows.append({"id": q.get("id"), "difficulty": q.get("difficulty", ""),
                     "question": q["question"], "valid_sql": r.ok,
                     "correct": bool(r.ok and results_match(r.df, gold)),
                     "attempts": r.attempts, "latency_s": round(time.perf_counter() - t0, 2),
                     "generated_sql": r.sql, "error": r.error or ""})
    return pd.DataFrame(rows)


def summarise(res: pd.DataFrame) -> dict:
    return {"questions": len(res), "valid_sql_rate": round(res["valid_sql"].mean() * 100, 1),
            "execution_accuracy": round(res["correct"].mean() * 100, 1),
            "avg_latency_s": round(res["latency_s"].mean(), 2),
            "by_difficulty": res.groupby("difficulty")["correct"].mean().mul(100).round(1).to_dict()}


if __name__ == "__main__":
    from modules.llm import LLMClient
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="evaluation/results.csv")
    a = ap.parse_args()
    data, _ = clean(load_file(a.data))
    qs = json.load(open(a.questions))
    out = run_benchmark(LLMClient(provider=a.provider, model=a.model), data, safe_table_name(a.data), qs)
    out.to_csv(a.out, index=False)
    print(json.dumps(summarise(out), indent=2))
