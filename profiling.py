"""Automated data profiling and the Data Quality Score."""
from __future__ import annotations

import numpy as np
import pandas as pd


def semantic_type(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    if pd.api.types.is_numeric_dtype(s):
        nun = s.nunique(dropna=True)
        name = str(s.name).lower()
        looks_like_id = name == "id" or name.endswith("_id") or name.endswith("id") and len(name) <= 12
        if pd.api.types.is_integer_dtype(s) and len(s) > 20 and nun / max(s.notna().sum(), 1) > 0.95 and looks_like_id:
            return "identifier"
        return "numeric"
    nun = s.nunique(dropna=True)
    if len(s) and nun / max(len(s), 1) > 0.9 and nun > 50:
        return "text/id"
    return "categorical"


_MEASURE_HINTS = ("revenue", "sales", "amount", "profit", "total", "income", "cost", "price", "value")


def pick_measure(df: pd.DataFrame, numeric_cols: list[str]) -> str | None:
    """Choose the most 'business-meaningful' numeric column to headline analyses."""
    for hint in _MEASURE_HINTS:
        for c in numeric_cols:
            if hint in c.lower():
                return c
    return numeric_cols[0] if numeric_cols else None


def iqr_outlier_mask(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0 or np.isnan(iqr):
        return pd.Series(False, index=s.index)
    return (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)


def _is_string(s: pd.Series) -> bool:
    return pd.api.types.is_string_dtype(s) and not pd.api.types.is_numeric_dtype(s)


def profile(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape
    cols = []
    outlier_cells = 0
    numeric_cells = 0
    inconsistent_cols = 0
    for c in df.columns:
        s = df[c]
        sem = semantic_type(s)
        info = {
            "column": c, "dtype": str(s.dtype), "type": sem,
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2) if n_rows else 0.0,
            "unique": int(s.nunique(dropna=True)),
        }
        if sem == "numeric":
            info.update(mean=float(s.mean()) if s.notna().any() else None,
                        std=float(s.std()) if s.notna().sum() > 1 else None,
                        min=float(s.min()) if s.notna().any() else None,
                        max=float(s.max()) if s.notna().any() else None)
            n_out = int(iqr_outlier_mask(s).sum())
            info["outliers"] = n_out
            outlier_cells += n_out
            numeric_cells += int(s.notna().sum())
        if _is_string(s):
            vals = s.dropna().astype(str)
            if len(vals) and ((vals != vals.str.strip()).any()
                              or (vals.str.lower().nunique() < vals.nunique())):
                info["inconsistent"] = True
                inconsistent_cols += 1
        cols.append(info)

    dup_rows = int(df.duplicated().sum())
    missing_cells = int(df.isna().sum().sum())
    total_cells = max(n_rows * n_cols, 1)

    completeness = 1 - missing_cells / total_cells
    uniqueness = 1 - dup_rows / max(n_rows, 1)
    validity = 1 - (outlier_cells / numeric_cells if numeric_cells else 0)
    consistency = 1 - inconsistent_cols / max(n_cols, 1)
    score = 100 * (0.4 * completeness + 0.2 * uniqueness + 0.2 * validity + 0.2 * consistency)

    return {
        "rows": n_rows, "columns": n_cols,
        "missing_cells": missing_cells, "duplicate_rows": dup_rows,
        "outlier_cells": outlier_cells,
        "dimensions": {"completeness": round(completeness * 100, 1),
                       "uniqueness": round(uniqueness * 100, 1),
                       "validity": round(validity * 100, 1),
                       "consistency": round(consistency * 100, 1)},
        "quality_score": round(score, 1),
        "columns_info": cols,
    }
