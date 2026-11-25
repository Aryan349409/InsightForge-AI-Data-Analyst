"""Insight generation: deterministic statistical facts + optional LLM narrative."""
from __future__ import annotations

import numpy as np
import pandas as pd

from modules.profiling import pick_measure, semantic_type


def statistical_facts(df: pd.DataFrame, profile: dict) -> list[str]:
    facts = [f"The dataset has {profile['rows']:,} rows and {profile['columns']} columns; "
             f"data quality score is {profile['quality_score']}/100."]
    nums = [c for c in df.columns if semantic_type(df[c]) == "numeric"]
    cats = [c for c in df.columns if semantic_type(df[c]) == "categorical" and df[c].nunique() <= 30]
    dates = [c for c in df.columns if semantic_type(df[c]) == "datetime"]

    worst = max(profile["columns_info"], key=lambda c: c["missing_pct"])
    if worst["missing_pct"] > 0:
        facts.append(f"'{worst['column']}' has the most missing data ({worst['missing_pct']}%).")

    if len(nums) >= 2:
        corr = df[nums].corr(numeric_only=True).abs().to_numpy().copy()
        np.fill_diagonal(corr, 0)
        a, b = np.unravel_index(np.nanargmax(corr), corr.shape)
        r = df[nums[a]].corr(df[nums[b]])
        if abs(r) >= 0.5:
            facts.append(f"'{nums[a]}' and '{nums[b]}' are strongly {'positively' if r > 0 else 'negatively'} "
                         f"correlated (r = {r:.2f}).")

    for c in nums[:4]:
        sk = df[c].skew()
        if abs(sk) > 1:
            facts.append(f"'{c}' is {'right' if sk > 0 else 'left'}-skewed (skew {sk:.2f}); "
                         f"median {df[c].median():,.2f} vs mean {df[c].mean():,.2f}.")

    measure = pick_measure(df, nums)
    if cats and measure:
        g = df.groupby(cats[0])[measure].sum().sort_values(ascending=False)
        if len(g) > 1 and g.sum() != 0:
            facts.append(f"'{g.index[0]}' leads '{cats[0]}' on total {measure} with "
                         f"{g.iloc[0] / g.sum() * 100:.1f}% of the overall total.")

    if dates and measure:
        s = df.set_index(dates[0])[measure].resample("MS").sum()
        if len(s) >= 4:
            half = len(s) // 2
            first, second = s.iloc[:half].mean(), s.iloc[half:].mean()
            if first:
                ch = (second - first) / abs(first) * 100
                facts.append(f"Monthly {measure} in the second half of the period is "
                             f"{abs(ch):.1f}% {'higher' if ch > 0 else 'lower'} than in the first half.")
            facts.append(f"Peak month for {measure}: {s.idxmax():%b %Y}; lowest: {s.idxmin():%b %Y}.")
    if profile["outlier_cells"]:
        facts.append(f"{profile['outlier_cells']} numeric values are statistical outliers (IQR rule).")
    return facts


NARRATIVE_SYSTEM = ("You are a senior data analyst writing for a business reader. Using ONLY the facts "
                    "provided, write a concise executive summary: 3-5 bullet insights then 2 recommended "
                    "actions. Do not invent numbers.")


def narrative(llm, facts: list[str], extra: str = "") -> str:
    return llm.complete(NARRATIVE_SYSTEM, "Facts:\n- " + "\n- ".join(facts) + (f"\n\n{extra}" if extra else ""),
                        max_tokens=700, temperature=0.2)
