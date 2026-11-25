import numpy as np
import pandas as pd
from modules import ml
from modules.nl2sql import ask, extract_sql
from modules.evaluation import results_match

class FakeLLM:
    """Returns scripted answers, one per call - lets us test retry logic offline."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0
    def complete(self, system, user, **kw):
        a = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        return f"```sql\n{a}\n```"

DF = pd.DataFrame({"product": list("aabbc"), "revenue": [10, 20, 30, 40, 50]})

def test_extract_sql():
    assert extract_sql("here:\n```sql\nSELECT 1;\n```") == "SELECT 1"

def test_successful_query():
    r = ask(FakeLLM("SELECT product, SUM(revenue) AS r FROM data GROUP BY product ORDER BY r DESC LIMIT 1"), "top", DF)
    assert r.ok and r.df.iloc[0]["product"] == "b" and r.attempts == 1

def test_self_repair_after_execution_error():
    llm = FakeLLM("SELECT nonexistent FROM data", "SELECT COUNT(*) AS n FROM data")
    r = ask(llm, "count", DF)
    assert r.ok and r.attempts == 2 and int(r.df.iloc[0, 0]) == 5

def test_destructive_sql_never_executes():
    r = ask(FakeLLM("DROP TABLE data"), "bad", DF, max_retries=1)
    assert not r.ok and "Blocked" in r.error

def test_results_match_ignores_order_and_names():
    a = pd.DataFrame({"x": ["a", "b"], "y": [1.001, 2.0]})
    b = pd.DataFrame({"p": ["b", "a"], "q": [2.0, 1.0]})
    assert results_match(a, b)

def test_regression_beats_baseline():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 3))
    df = pd.DataFrame(X, columns=["a", "b", "c"])
    df["y"] = 3 * df["a"] + rng.normal(scale=0.1, size=300)
    out = ml.train(df, "y")
    assert out["task"] == "regression"
    assert out["comparison"]["r2"].max() > 0.9
    assert out["importance"].iloc[0]["feature"] == "a"

def test_classification_detected():
    df = pd.DataFrame({"x": np.random.rand(200), "label": np.random.choice(["a", "b"], 200)})
    assert ml.train(df, "label")["task"] == "classification"

def test_forecast_horizon():
    idx = pd.date_range("2022-01-01", periods=400, freq="D")
    df = pd.DataFrame({"d": idx, "v": np.arange(400) + 10.0})
    f = ml.forecast(df, "d", "v", periods=3)
    assert len(f["forecast"]) == 3
