"""Reusable Plotly chart builders for the HR Analytics dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------ palette
TEAL = "#2A9D8F"
CORAL = "#E76F51"
NAVY = "#264653"
SAND = "#E9C46A"
ORANGE = "#F4A261"
ATTR_COLORS = {"No": TEAL, "Yes": CORAL}
SEQ = [NAVY, TEAL, SAND, ORANGE, CORAL, "#8AB17D", "#6D597A", "#B56576", "#355070"]
RATE_SCALE = ["#FDE8DF", "#F4A261", "#E76F51", "#B23A48"]


def style(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    """Apply the dashboard look to any figure."""
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(size=16)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=""),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False)
    return fig


# ------------------------------------------------------------------ helpers
def rate_by(df: pd.DataFrame, col: str, order: list | None = None) -> pd.DataFrame:
    """Headcount, leavers and attrition rate (%) per category of `col`."""
    g = (df.groupby(col, observed=True)
           .agg(Employees=("EmpID", "count"), Leavers=("AttritionFlag", "sum"),
                AttritionRate=("AttritionFlag", "mean"))
           .reset_index())
    g["AttritionRate"] = (g["AttritionRate"] * 100).round(1)
    if order:
        g[col] = pd.Categorical(g[col], categories=order, ordered=True)
        g = g.sort_values(col)
    return g


# ------------------------------------------------------------------ attrition
def donut_attrition(df: pd.DataFrame) -> go.Figure:
    counts = df["Attrition"].value_counts().reindex(["No", "Yes"]).fillna(0)
    fig = go.Figure(go.Pie(
        labels=["Stayed", "Left"], values=counts.values, hole=0.62,
        marker=dict(colors=[TEAL, CORAL]), textinfo="percent", sort=False))
    rate = df["AttritionFlag"].mean() * 100
    fig.add_annotation(text=f"<b>{rate:.1f}%</b><br>attrition", showarrow=False, font=dict(size=18))
    fig.update_layout(title="Workforce retention")
    return style(fig, 340)


def rate_bar(df: pd.DataFrame, col: str, title: str, order: list | None = None,
             horizontal: bool = False, height: int = 380) -> go.Figure:
    g = rate_by(df, col, order)
    overall = df["AttritionFlag"].mean() * 100
    if horizontal and not order:
        g = g.sort_values("AttritionRate", ascending=True)
    common = dict(color="AttritionRate", color_continuous_scale=RATE_SCALE,
                  text="AttritionRate", hover_data={"Employees": True, "Leavers": True})
    if horizontal:
        fig = px.bar(g, y=col, x="AttritionRate", orientation="h", **common)
        fig.add_vline(x=overall, line_dash="dash", line_color=NAVY,
                      annotation_text=f"Avg {overall:.1f}%", annotation_position="top")
    else:
        fig = px.bar(g, x=col, y="AttritionRate", **common)
        if pd.api.types.is_numeric_dtype(g[col]):
            fig.update_xaxes(type="category")
        fig.add_hline(y=overall, line_dash="dash", line_color=NAVY,
                      annotation_text=f"Avg {overall:.1f}%", annotation_position="top left")
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(title=title)
    if horizontal:
        fig.update_xaxes(title="Attrition rate (%)")
        fig.update_yaxes(title="")
    else:
        fig.update_yaxes(title="Attrition rate (%)")
        fig.update_xaxes(title="")
    return style(fig, height, legend=False)


def headcount_bar(df: pd.DataFrame, col: str, title: str, order: list | None = None,
                  horizontal: bool = False, height: int = 380) -> go.Figure:
    g = df.groupby([col, "Attrition"], observed=True).size().reset_index(name="Employees")
    cat_orders = {"Attrition": ["No", "Yes"]}
    if order:
        cat_orders[col] = order
    if horizontal:
        totals = df[col].value_counts().sort_values(ascending=True).index.tolist()
        cat_orders[col] = totals
        fig = px.bar(g, y=col, x="Employees", color="Attrition", orientation="h",
                     color_discrete_map=ATTR_COLORS, category_orders=cat_orders)
    else:
        fig = px.bar(g, x=col, y="Employees", color="Attrition",
                     color_discrete_map=ATTR_COLORS, category_orders=cat_orders)
    fig.update_layout(title=title, barmode="stack")
    fig.update_xaxes(title="" if not horizontal else "Employees")
    fig.update_yaxes(title="" if horizontal else "Employees")
    return style(fig, height)


def heatmap_rate(df: pd.DataFrame, row: str, col: str, title: str, min_n: int = 5,
                 height: int = 420, row_order: list | None = None, col_order: list | None = None) -> go.Figure:
    rate = df.pivot_table(index=row, columns=col, values="AttritionFlag", aggfunc="mean", observed=True) * 100
    cnt = df.pivot_table(index=row, columns=col, values="AttritionFlag", aggfunc="count", observed=True)
    rate = rate.where(cnt >= min_n)
    if row_order:
        rate = rate.reindex([r for r in row_order if r in rate.index])
    if col_order:
        rate = rate[[c for c in col_order if c in rate.columns]]
    fig = px.imshow(rate.round(1), text_auto=".1f", aspect="auto",
                    color_continuous_scale=RATE_SCALE, labels=dict(color="Attrition %"))
    fig.update_layout(title=title, coloraxis_colorbar=dict(title="%"))
    fig.update_xaxes(title="")
    fig.update_yaxes(title="")
    return style(fig, height, legend=False)


def treemap_attrition(df: pd.DataFrame) -> go.Figure:
    fig = px.treemap(df, path=[px.Constant("Company"), "Department", "JobRole"],
                     color="AttritionFlag", color_continuous_scale=["#2A9D8F", "#E9C46A", "#E76F51"],
                     title="Headcount by Department → Role (colour = attrition rate)")
    fig.update_coloraxes(colorbar=dict(title="Attrition", tickformat=".0%"))
    fig.update_traces(hovertemplate="<b>%{label}</b><br>Employees: %{value}<br>Attrition: %{color:.1%}<extra></extra>")
    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), height=420, paper_bgcolor="rgba(0,0,0,0)")
    return fig


def radar_satisfaction(df: pd.DataFrame) -> go.Figure:
    metrics = {"JobSatisfaction": "Job satisfaction", "EnvironmentSatisfaction": "Environment",
               "RelationshipSatisfaction": "Relationships", "WorkLifeBalance": "Work-life balance",
               "JobInvolvement": "Job involvement"}
    fig = go.Figure()
    for label, color, name in [("No", TEAL, "Stayed"), ("Yes", CORAL, "Left")]:
        sub = df[df["Attrition"] == label]
        if sub.empty:
            continue
        vals = [sub[c].mean() for c in metrics]
        fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=list(metrics.values()) + [list(metrics.values())[0]],
                                      fill="toself", name=name, line=dict(color=color), opacity=0.65))
    fig.update_layout(title="Engagement profile: stayers vs leavers (avg score, 1-4)",
                      polar=dict(radialaxis=dict(visible=True, range=[2, 3.2])))
    return style(fig, 400)


# ------------------------------------------------------------------ compensation
def income_box(df: pd.DataFrame, x: str, title: str, order: list | None = None, height: int = 400) -> go.Figure:
    cat = {x: order} if order else None
    fig = px.box(df, x=x, y="MonthlyIncome", color="Attrition", color_discrete_map=ATTR_COLORS,
                 category_orders=cat, points=False)
    fig.update_layout(title=title, boxmode="group")
    fig.update_xaxes(title="", tickangle=-25)
    fig.update_yaxes(title="Monthly income")
    return style(fig, height)


def income_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(df, x="TotalWorkingYears", y="MonthlyIncome", color="Attrition",
                     color_discrete_map=ATTR_COLORS, opacity=0.65,
                     hover_data=["EmpID", "JobRole", "JobLevel", "Age"])
    fig.update_traces(marker=dict(size=7))
    fig.update_layout(title="Income vs. career experience")
    fig.update_xaxes(title="Total working years")
    fig.update_yaxes(title="Monthly income")
    return style(fig, 400)


def gender_pay(df: pd.DataFrame) -> go.Figure:
    g = df.groupby(["JobLevel", "Gender"], observed=True)["MonthlyIncome"].mean().reset_index()
    fig = px.bar(g, x="JobLevel", y="MonthlyIncome", color="Gender", barmode="group",
                 color_discrete_map={"Female": "#B56576", "Male": NAVY})
    fig.update_layout(title="Average monthly income by job level & gender")
    fig.update_xaxes(title="Job level", dtick=1)
    fig.update_yaxes(title="Avg monthly income")
    return style(fig, 400)


def hike_vs_performance(df: pd.DataFrame) -> go.Figure:
    order = ["Excellent", "Outstanding"]
    fig = px.violin(df, x="PerformanceLabel", y="PercentSalaryHike", color="PerformanceLabel", box=True,
                    category_orders={"PerformanceLabel": order},
                    color_discrete_map={"Excellent": TEAL, "Outstanding": SAND})
    fig.update_layout(title="Salary hike % by performance rating")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Salary hike (%)")
    return style(fig, 400, legend=False)


# ------------------------------------------------------------------ distributions
def hist_by_attrition(df: pd.DataFrame, col: str, title: str, nbins: int = 25, height: int = 360) -> go.Figure:
    fig = px.histogram(df, x=col, color="Attrition", nbins=nbins, barmode="overlay", opacity=0.7,
                       color_discrete_map=ATTR_COLORS)
    fig.update_layout(title=title)
    fig.update_yaxes(title="Employees")
    return style(fig, height)


def pie_chart(df: pd.DataFrame, col: str, title: str, order: list | None = None) -> go.Figure:
    counts = df[col].value_counts()
    if order:
        counts = counts.reindex([o for o in order if o in counts.index])
    fig = go.Figure(go.Pie(labels=counts.index.astype(str), values=counts.values, hole=0.5,
                           marker=dict(colors=SEQ), sort=False, textinfo="label+percent"))
    fig.update_layout(title=title)
    return style(fig, 340, legend=False)


# ------------------------------------------------------------------ correlations
def corr_heatmap(df: pd.DataFrame) -> go.Figure:
    num = df.select_dtypes(include="number").drop(columns=["YearsWithCurrManager_Imputed"], errors="ignore")
    corr = num.corr().round(2)
    fig = px.imshow(corr, text_auto=".1f", aspect="auto", zmin=-1, zmax=1,
                    color_continuous_scale="RdBu_r")
    fig.update_traces(textfont_size=8)
    fig.update_layout(title="Correlation matrix (numeric features)")
    return style(fig, 720, legend=False)


def corr_with_attrition(df: pd.DataFrame, top: int = 12) -> go.Figure:
    num = df.select_dtypes(include="number").drop(columns=["YearsWithCurrManager_Imputed"], errors="ignore")
    c = num.corr()["AttritionFlag"].drop("AttritionFlag").dropna()
    c = c.reindex(c.abs().sort_values(ascending=False).index).head(top).sort_values()
    colors = [CORAL if v > 0 else TEAL for v in c.values]
    fig = go.Figure(go.Bar(x=c.values, y=c.index, orientation="h", marker_color=colors,
                           text=[f"{v:+.2f}" for v in c.values], textposition="outside", cliponaxis=False))
    fig.update_layout(title="Strongest correlations with attrition  (red ↑ more likely to leave, green ↓ less likely)")
    fig.update_xaxes(title="Pearson correlation with attrition", zeroline=True)
    return style(fig, 460, legend=False)
