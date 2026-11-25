import numpy as np
import pandas as pd
from modules.cleaning import clean
from modules.profiling import profile, semantic_type

def messy():
    return pd.DataFrame({
        "Order ID": range(1, 41),
        "Region ": ["north", "North", "South", " South"] * 10,
        "Amount": ["$1,200", "300", "450", "1,000"] * 10,
        "Date": ["01-02-2024", "15-03-2024", "20-04-2024", "05-05-2024"] * 10,
        "Age": [25, np.nan, 31, 40] * 10,
    })

def test_cleaning_standardises_and_converts():
    out, log = clean(messy())
    assert "order_id" in out.columns and "region" in out.columns
    assert pd.api.types.is_numeric_dtype(out["amount"])
    assert pd.api.types.is_datetime64_any_dtype(out["date"])
    assert out["region"].nunique() == 2
    assert out["age"].isna().sum() == 0
    assert log

def test_duplicates_removed():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    out, _ = clean(df)
    assert len(out) == 2

def test_quality_score_improves_after_cleaning():
    raw = messy()
    cleaned, _ = clean(raw)
    assert profile(cleaned)["quality_score"] >= profile(raw)["quality_score"]

def test_identifier_detection():
    s = pd.Series(range(100), name="customer_id")
    assert semantic_type(s) == "identifier"
    assert semantic_type(pd.Series(np.random.rand(100), name="price")) == "numeric"
