"""Automatic chart generation with Plotly."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules.profiling import pick_measure, semantic_type


def auto_charts(df: pd.DataFrame, max_charts: int = 8) -> list[tuple[str, go.Figure]]:
    charts: list[tuple[str, go.Figure]] = []
    types = {c: semantic_type(df[c]) for c in df.columns}
    nums = [c for c, t in types.items() if t == "numeric"]
    cats = [c for c, t in types.items() if t == "categorical" and df[c].nunique() <= 20]
    dates = [c for c, t in types.items() if t == "datetime"]

    m0 = pick_measure(df, nums)
    for c in ([m0] if m0 else []) + [x for x in nums if x != m0][:2]:
        charts.append((f"Distribution of {c}", px.histogram(df, x=c, nbins=30, marginal="box")))
    for c in cats[:2]:
        vc = df[c].value_counts().head(15).reset_index()
        vc.columns = [c, "count"]
        charts.append((f"Counts by {c}", px.bar(vc, x=c, y="count")))
    m = pick_measure(df, nums)
    if cats and m:
        g = df.groupby(cats[0])[m].sum().sort_values(ascending=False).head(15).reset_index()
        charts.append((f"Total {m} by {cats[0]}", px.bar(g, x=cats[0], y=m)))
    if dates and m:
        t = df.set_index(dates[0])[m].resample("MS").sum().reset_index()
        charts.append((f"{m} over time (monthly)", px.line(t, x=dates[0], y=m, markers=True)))
    if len(nums) >= 2:
        corr = df[nums].corr(numeric_only=True)
        charts.append(("Correlation heatmap",
                       px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                                 zmin=-1, zmax=1)))
    return charts[:max_charts]


def chart_for_result(res: pd.DataFrame) -> go.Figure | None:
    """Pick a sensible chart for a query result, or None if a table is better."""
    if res is None or res.empty or len(res) > 500 or res.shape[1] < 2:
        return None
    types = {c: semantic_type(res[c]) for c in res.columns}
    nums = [c for c, t in types.items() if t == "numeric"]
    dates = [c for c, t in types.items() if t == "datetime"]
    cats = [c for c, t in types.items() if t in ("categorical", "text/id")]
    if dates and nums:
        return px.line(res.sort_values(dates[0]), x=dates[0], y=nums[0], markers=True)
    if cats and nums:
        d = res.head(25)
        return px.bar(d, x=cats[0], y=nums[0])
    if len(nums) >= 2:
        return px.scatter(res, x=nums[0], y=nums[1])
    return None
