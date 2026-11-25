"""Automated, explainable data cleaning. Every change is written to a log."""
from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd

from modules.profiling import iqr_outlier_mask, semantic_type

_NUM_JUNK = re.compile(r"[,$€£₹%\s]")


def _snake(name: str) -> str:
    name = re.sub(r"[^\w]+", "_", str(name).strip()).strip("_").lower()
    return name or "col"


def clean(df: pd.DataFrame, *, impute: str = "auto", outliers: str = "none",
          drop_duplicates: bool = True, parse_dates: bool = True) -> tuple[pd.DataFrame, list[str]]:
    """Return (clean_df, log).

    impute:   'auto' (median/mode) | 'drop' (drop rows with any NaN) | 'none'
    outliers: 'none' | 'cap' (winsorize at IQR fences) | 'remove'
    """
    log: list[str] = []
    out = df.copy()

    # 1. column names
    new_cols, seen = [], {}
    for c in out.columns:
        n = _snake(c)
        seen[n] = seen.get(n, 0) + 1
        new_cols.append(n if seen[n] == 1 else f"{n}_{seen[n]}")
    if new_cols != list(out.columns):
        log.append("Standardised column names to snake_case.")
    out.columns = new_cols

    # 2. whitespace / empty strings
    for c in out.columns:
        if pd.api.types.is_string_dtype(out[c]) and not pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype("object")
            mask = out[c].notna()
            out.loc[mask, c] = out.loc[mask, c].astype(str).str.strip()
            blanks = out[c].isin(["", "nan", "NaN", "NULL", "null", "None", "N/A", "n/a", "-"])
            if blanks.any():
                out.loc[blanks, c] = np.nan
                log.append(f"'{c}': converted {int(blanks.sum())} blank/placeholder values to missing.")

    # 3. numbers stored as text, dates stored as text
    for c in out.columns:
        if not pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_datetime64_any_dtype(out[c]):
            non_null = out[c].dropna().astype(str)
            if non_null.empty:
                continue
            stripped = non_null.str.replace(_NUM_JUNK, "", regex=True)
            nums = pd.to_numeric(stripped, errors="coerce")
            if nums.notna().mean() >= 0.9:
                out[c] = pd.to_numeric(out[c].astype(str).str.replace(_NUM_JUNK, "", regex=True),
                                       errors="coerce")
                log.append(f"'{c}': converted text to numeric.")
                continue
            if parse_dates and non_null.str.contains(r"\d").mean() > 0.9:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        dt = pd.to_datetime(non_null, errors="coerce", format="mixed")
                    except (ValueError, TypeError):
                        continue
                if dt.notna().mean() >= 0.9:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        out[c] = pd.to_datetime(out[c], errors="coerce", format="mixed")
                    log.append(f"'{c}': parsed as datetime.")

    # 4. category casing (e.g. 'north' / 'North')
    for c in out.columns:
        if not pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_datetime64_any_dtype(out[c]):
            vals = out[c].dropna().astype(str)
            if vals.nunique() and vals.str.lower().nunique() < vals.nunique() and vals.nunique() < 100:
                canon = vals.groupby(vals.str.lower()).agg(lambda x: x.value_counts().idxmax())
                out[c] = out[c].map(lambda v: canon[str(v).lower()] if pd.notna(v) else v)
                log.append(f"'{c}': unified inconsistent capitalisation.")

    # 5. duplicates
    if drop_duplicates:
        before = len(out)
        out = out.drop_duplicates().reset_index(drop=True)
        if len(out) < before:
            log.append(f"Removed {before - len(out)} duplicate rows.")

    # 6. missing values
    if impute == "drop":
        before = len(out)
        out = out.dropna().reset_index(drop=True)
        log.append(f"Dropped {before - len(out)} rows containing missing values.")
    elif impute == "auto":
        for c in out.columns:
            n_missing = int(out[c].isna().sum())
            if n_missing == 0:
                continue
            if n_missing / max(len(out), 1) > 0.6:
                log.append(f"'{c}': {n_missing} missing (>60%) - left untouched, consider dropping the column.")
                continue
            if pd.api.types.is_numeric_dtype(out[c]):
                out[c] = out[c].fillna(out[c].median())
                log.append(f"'{c}': filled {n_missing} missing values with the median.")
            elif pd.api.types.is_datetime64_any_dtype(out[c]):
                continue
            else:
                mode = out[c].mode(dropna=True)
                if len(mode):
                    out[c] = out[c].fillna(mode.iloc[0])
                    log.append(f"'{c}': filled {n_missing} missing values with the mode ('{mode.iloc[0]}').")

    # 7. outliers
    if outliers in {"cap", "remove"}:
        if outliers == "remove":
            keep = pd.Series(True, index=out.index)
        for c in out.columns:
            if semantic_type(out[c]) != "numeric" or out[c].nunique() < 10:
                continue
            mask = iqr_outlier_mask(out[c])
            if not mask.any():
                continue
            if outliers == "cap":
                q1, q3 = out[c].quantile([0.25, 0.75])
                iqr = q3 - q1
                out[c] = out[c].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
                log.append(f"'{c}': capped {int(mask.sum())} outliers at the IQR fences.")
            else:
                keep &= ~mask
        if outliers == "remove":
            removed = int((~keep).sum())
            out = out[keep].reset_index(drop=True)
            log.append(f"Removed {removed} rows containing outliers.")

    if not log:
        log.append("No issues found - dataset was already clean.")
    return out, log
