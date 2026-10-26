"""Auto-generated, data-driven insights for the currently filtered workforce."""
from __future__ import annotations

import pandas as pd

from utils.charts import rate_by

MIN_GROUP = 20  # ignore tiny segments so insights are not driven by noise

DIMENSIONS = [
    ("OverTime", "overtime status"),
    ("Department", "department"),
    ("JobRole", "job role"),
    ("MaritalStatus", "marital status"),
    ("BusinessTravel", "travel frequency"),
    ("SalarySlab", "salary band"),
    ("TenureBucket", "tenure band"),
    ("AgeGroup", "age group"),
    ("PromotionStatus", "promotion status"),
]


def generate_insights(df: pd.DataFrame, top_n: int = 4) -> list[str]:
    overall = df["AttritionFlag"].mean() * 100
    if len(df) < 2 * MIN_GROUP or overall == 0:
        return ["Not enough data in the current selection to generate insights."]

    candidates: list[tuple[float, str]] = []
    for col, label in DIMENSIONS:
        g = rate_by(df, col)
        g = g[g["Employees"] >= MIN_GROUP]
        if len(g) < 2:
            continue
        hi = g.sort_values("AttritionRate", ascending=False).iloc[0]
        lo = g.sort_values("AttritionRate", ascending=True).iloc[0]
        lift = hi["AttritionRate"] - overall
        if lift > 0:
            ratio = hi["AttritionRate"] / lo["AttritionRate"] if lo["AttritionRate"] > 0 else float("inf")
            ratio_txt = f", {ratio:.1f}x the lowest group ({lo[col]})" if ratio != float("inf") else ""
            candidates.append((
                lift,
                f"Highest-attrition {label}: **{hi[col]}** at **{hi['AttritionRate']:.1f}%** "
                f"({int(hi['Employees'])} employees, {lift:+.1f} pts vs average{ratio_txt}).",
            ))

    candidates.sort(key=lambda t: t[0], reverse=True)
    return [text for _, text in candidates[:top_n]] or ["No segment stands out against the average."]
