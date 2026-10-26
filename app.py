"""HR Analytics - interactive Streamlit dashboard.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import inspect
import io
from itertools import count

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import charts as C
from utils.data_cleaning import (AGE_ORDER, SLAB_ORDER, TENURE_ORDER, clean_data, load_raw)
from utils.insights import generate_insights

# =============================================================== page setup
st.set_page_config(page_title="HR Analytics Dashboard", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1500px;}
      .hero {background: linear-gradient(120deg,#264653 0%,#2A9D8F 60%,#8AB17D 100%);
             padding: 1.6rem 2rem; border-radius: 18px; color: #fff; margin-bottom: 1.2rem;}
      .hero h1 {margin:0; font-size: 2rem; color:#fff;}
      .hero p {margin:.3rem 0 0 0; opacity:.9; font-size:1rem;}
      .kpi {background:#fff; border-radius:14px; padding:14px 18px; box-shadow:0 2px 10px rgba(0,0,0,.08);
            height:100%;}
      .kpi-label {font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; color:#6b7280;}
      .kpi-value {font-size:1.9rem; font-weight:700; color:#264653; line-height:1.2;}
      .kpi-sub {font-size:.8rem; color:#6b7280;}
      .insight {background:#fff8f3; border-left:5px solid #E76F51; border-radius:10px;
                padding:.7rem 1rem; margin-bottom:.6rem; color:#264653;}
      .section-note {color:#6b7280; font-size:.9rem; margin-bottom:.4rem;}
      div[data-baseweb="tab-list"] {gap: 6px;}
      button[data-baseweb="tab"] {border-radius: 10px 10px 0 0; padding: 8px 16px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- version-safe wrappers (Streamlit renamed use_container_width -> width="stretch")
def _has_width(fn) -> bool:
    try:
        return "width" in inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False


_PLOT_WIDTH = _has_width(st.plotly_chart)
_DF_WIDTH = _has_width(st.dataframe)
_BTN_WIDTH = _has_width(st.button)
_key = count()


def show(fig) -> None:
    kw = {"width": "stretch"} if _PLOT_WIDTH else {"use_container_width": True}
    st.plotly_chart(fig, key=f"chart_{next(_key)}", **kw)


def show_df(data, **kwargs) -> None:
    kw = {"width": "stretch"} if _DF_WIDTH else {"use_container_width": True}
    st.dataframe(data, hide_index=True, **kw, **kwargs)


def kpi(label: str, value: str, sub: str = "", color: str = C.TEAL) -> str:
    return (f'<div class="kpi" style="border-left:5px solid {color}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>')


# =============================================================== data
@st.cache_data(show_spinner="Loading & cleaning data...")
def get_data():
    raw = load_raw()
    clean, log = clean_data(raw)
    return raw, clean, log


raw_df, df_all, clean_log = get_data()
company_rate = df_all["AttritionFlag"].mean() * 100

# =============================================================== sidebar filters
st.sidebar.title("🎛️ Filters")
st.sidebar.caption("All tabs update instantly.")

MULTI = {  # key -> (label, column)
    "f_dept": ("Department", "Department"),
    "f_role": ("Job role", "JobRole"),
    "f_gender": ("Gender", "Gender"),
    "f_marital": ("Marital status", "MaritalStatus"),
    "f_ot": ("Overtime", "OverTime"),
    "f_travel": ("Business travel", "BusinessTravel"),
}
OPTIONS = {k: sorted(df_all[col].unique()) for k, (_, col) in MULTI.items()}
AGE_RNG = (int(df_all["Age"].min()), int(df_all["Age"].max()))
INC_RNG = (int(df_all["MonthlyIncome"].min()), int(df_all["MonthlyIncome"].max()))
TEN_RNG = (int(df_all["YearsAtCompany"].min()), int(df_all["YearsAtCompany"].max()))


DEFAULTS = {**{k: OPTIONS[k] for k in MULTI}, "f_age": AGE_RNG, "f_inc": INC_RNG, "f_ten": TEN_RNG}
for _k, _v in DEFAULTS.items():  # initialise once; widgets then read their value from session state
    st.session_state.setdefault(_k, _v)


def reset_filters() -> None:
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


_btn_kw = {"width": "stretch"} if _BTN_WIDTH else {"use_container_width": True}
st.sidebar.button("↺ Reset all filters", on_click=reset_filters, **_btn_kw)

selected = {}
for k, (label, _) in MULTI.items():
    selected[k] = st.sidebar.multiselect(label, OPTIONS[k], key=k)

age_sel = st.sidebar.slider("Age", AGE_RNG[0], AGE_RNG[1], key="f_age")
inc_sel = st.sidebar.slider("Monthly income", INC_RNG[0], INC_RNG[1], step=100, key="f_inc")
ten_sel = st.sidebar.slider("Years at company", TEN_RNG[0], TEN_RNG[1], key="f_ten")

mask = (
    df_all["Age"].between(*age_sel)
    & df_all["MonthlyIncome"].between(*inc_sel)
    & df_all["YearsAtCompany"].between(*ten_sel)
)
for k, (_, col) in MULTI.items():
    mask &= df_all[col].isin(selected[k])
df = df_all[mask].copy()

st.sidebar.markdown("---")
st.sidebar.metric("Employees in selection", f"{len(df):,}", f"{len(df) / len(df_all):.0%} of workforce",
                  delta_color="off")

# =============================================================== header
st.markdown(
    """
    <div class="hero">
      <h1>📊 HR Analytics Dashboard</h1>
      <p>Workforce composition, attrition drivers, compensation & engagement - cleaned, validated and interactive.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No employees match the current filters. Adjust or reset the filters in the sidebar.")
    st.stop()

# =============================================================== tabs
tab_overview, tab_attr, tab_comp, tab_eng, tab_demo, tab_drivers, tab_data = st.tabs(
    ["🏠 Overview", "🚪 Attrition deep-dive", "💰 Compensation", "😊 Engagement",
     "👥 Demographics", "🧠 Drivers & risk", "🧹 Data & quality"]
)

# ------------------------------------------------------------------ OVERVIEW
with tab_overview:
    rate = df["AttritionFlag"].mean() * 100
    diff = rate - company_rate
    cols = st.columns(6)
    cards = [
        ("Employees", f"{len(df):,}", f"{int(df['AttritionFlag'].sum())} have left", C.NAVY),
        ("Attrition rate", f"{rate:.1f}%",
         "company average" if abs(diff) < 0.05 else f"{diff:+.1f} pts vs company ({company_rate:.1f}%)", C.CORAL),
        ("Avg monthly income", f"${df['MonthlyIncome'].mean():,.0f}", f"median ${df['MonthlyIncome'].median():,.0f}", C.TEAL),
        ("Avg tenure", f"{df['YearsAtCompany'].mean():.1f} yrs", f"avg age {df['Age'].mean():.0f}", C.SAND),
        ("Overtime share", f"{(df['OverTime'] == 'Yes').mean() * 100:.0f}%", "of employees work overtime", C.ORANGE),
        ("Avg satisfaction", f"{df['AvgSatisfaction'].mean():.2f} / 4", "job, env., relations, WLB", "#8AB17D"),
    ]
    for col, card in zip(cols, cards):
        col.markdown(kpi(*card), unsafe_allow_html=True)

    st.markdown("### 💡 Key insights")
    st.markdown('<div class="section-note">Generated automatically from the current filter selection '
                f'(segments with fewer than 20 employees are ignored).</div>', unsafe_allow_html=True)
    for text in generate_insights(df):
        st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1.6])
    with c1:
        show(C.donut_attrition(df))
    with c2:
        show(C.rate_bar(df, "Department", "Attrition rate by department", height=340))

    c3, c4 = st.columns(2)
    with c3:
        show(C.treemap_attrition(df))
    with c4:
        show(C.headcount_bar(df, "JobRole", "Headcount by job role", horizontal=True, height=420))

# ------------------------------------------------------------------ ATTRITION
with tab_attr:
    st.markdown("#### Where is attrition concentrated?")
    DIMS = {
        "Department": ("Department", None), "Job role": ("JobRole", None),
        "Age group": ("AgeGroup", AGE_ORDER), "Salary slab": ("SalarySlab", SLAB_ORDER),
        "Tenure band": ("TenureBucket", TENURE_ORDER), "Overtime": ("OverTime", None),
        "Business travel": ("BusinessTravel", None), "Marital status": ("MaritalStatus", None),
        "Education field": ("EducationField", None), "Gender": ("Gender", None),
        "Job level": ("JobLevel", None), "Years since last promotion": ("YearsSinceLastPromotion", None),
        "Number of companies worked": ("NumCompaniesWorked", None), "Stock option level": ("StockOptionLevel", None),
    }
    pick = st.selectbox("Break attrition down by", list(DIMS), index=0)
    dcol, dorder = DIMS[pick]
    horizontal = pick in ("Job role", "Education field")
    a1, a2 = st.columns(2)
    with a1:
        show(C.rate_bar(df, dcol, f"Attrition rate by {pick.lower()}", dorder, horizontal=horizontal))
    with a2:
        show(C.headcount_bar(df, dcol, f"Headcount by {pick.lower()}", dorder, horizontal=horizontal))

    st.markdown("#### Hot-spot matrix")
    h1, h2 = st.columns(2)
    with h1:
        show(C.heatmap_rate(df, "JobRole", "OverTime", "Attrition % - job role × overtime", min_n=5))
    with h2:
        show(C.heatmap_rate(df, "AgeGroup", "SalarySlab", "Attrition % - age group × salary slab", min_n=5,
                            row_order=AGE_ORDER, col_order=SLAB_ORDER))

    t1, t2 = st.columns(2)
    with t1:
        show(C.hist_by_attrition(df, "YearsAtCompany", "Tenure distribution: stayers vs leavers", nbins=20))
    with t2:
        show(C.hist_by_attrition(df, "DistanceFromHome", "Commute distance: stayers vs leavers", nbins=15))

# ------------------------------------------------------------------ COMPENSATION
with tab_comp:
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(kpi("Avg income - stayed", f"${df.loc[df.Attrition == 'No', 'MonthlyIncome'].mean():,.0f}", "", C.TEAL),
                unsafe_allow_html=True)
    left_inc = df.loc[df.Attrition == "Yes", "MonthlyIncome"].mean()
    m2.markdown(kpi("Avg income - left", f"${left_inc:,.0f}" if pd.notna(left_inc) else "n/a", "", C.CORAL),
                unsafe_allow_html=True)
    f_inc = df.loc[df.Gender == "Female", "MonthlyIncome"].mean()
    m_inc = df.loc[df.Gender == "Male", "MonthlyIncome"].mean()
    m3.markdown(kpi("Avg income - female", f"${f_inc:,.0f}" if pd.notna(f_inc) else "n/a", "", "#B56576"),
                unsafe_allow_html=True)
    m4.markdown(kpi("Avg income - male", f"${m_inc:,.0f}" if pd.notna(m_inc) else "n/a", "", C.NAVY),
                unsafe_allow_html=True)
    st.write("")

    p1, p2 = st.columns(2)
    with p1:
        show(C.income_box(df, "JobRole", "Monthly income by job role"))
    with p2:
        show(C.income_scatter(df))
    p3, p4 = st.columns(2)
    with p3:
        show(C.gender_pay(df))
    with p4:
        show(C.hike_vs_performance(df))
    p5, p6 = st.columns(2)
    with p5:
        show(C.rate_bar(df, "SalarySlab", "Attrition rate by salary slab", SLAB_ORDER))
    with p6:
        show(C.income_box(df, "Department", "Monthly income by department"))

# ------------------------------------------------------------------ ENGAGEMENT
with tab_eng:
    e1, e2 = st.columns([1.2, 1])
    with e1:
        show(C.radar_satisfaction(df))
    with e2:
        show(C.pie_chart(df, "PerformanceLabel", "Performance rating mix"))
    st.markdown("#### Attrition rate by satisfaction level")
    SAT = [("JobSatisfactionLabel", "Job satisfaction"), ("EnvSatisfactionLabel", "Environment satisfaction"),
           ("RelSatisfactionLabel", "Relationship satisfaction"), ("WorkLifeBalanceLabel", "Work-life balance")]
    SAT_ORDER = ["Low", "Medium", "High", "Very High"]
    WLB_ORDER = ["Bad", "Good", "Better", "Best"]
    s_cols = st.columns(2)
    for i, (col, label) in enumerate(SAT):
        with s_cols[i % 2]:
            show(C.rate_bar(df, col, label, WLB_ORDER if col == "WorkLifeBalanceLabel" else SAT_ORDER, height=330))
    g1, g2 = st.columns(2)
    with g1:
        show(C.rate_bar(df, "TrainingTimesLastYear", "Attrition rate by trainings attended last year", height=330))
    with g2:
        show(C.rate_bar(df, "JobInvolvement", "Attrition rate by job involvement (1-4)", height=330))

# ------------------------------------------------------------------ DEMOGRAPHICS
with tab_demo:
    d1, d2, d3 = st.columns(3)
    with d1:
        show(C.pie_chart(df, "Gender", "Gender split"))
    with d2:
        show(C.pie_chart(df, "MaritalStatus", "Marital status"))
    with d3:
        show(C.pie_chart(df, "AgeGroup", "Age groups", AGE_ORDER))
    d4, d5 = st.columns(2)
    with d4:
        show(C.hist_by_attrition(df, "Age", "Age distribution", nbins=22))
    with d5:
        show(C.headcount_bar(df, "EducationLabel", "Education level",
                             ["Below College", "College", "Bachelor", "Master", "Doctor"]))
    d6, d7 = st.columns(2)
    with d6:
        show(C.headcount_bar(df, "EducationField", "Education field", horizontal=True))
    with d7:
        show(C.headcount_bar(df, "BusinessTravel", "Business travel frequency"))

# ------------------------------------------------------------------ DRIVERS & RISK
with tab_drivers:
    r1, r2 = st.columns([1, 1])
    with r1:
        show(C.corr_with_attrition(df))
    with r2:
        st.markdown("##### 🔥 Highest-risk employee segments")
        st.markdown('<div class="section-note">Department × role × overtime combinations with at least '
                    '15 employees, ranked by attrition rate.</div>', unsafe_allow_html=True)
        seg = (df.groupby(["Department", "JobRole", "OverTime"], observed=True)
                 .agg(Employees=("EmpID", "count"), Leavers=("AttritionFlag", "sum"),
                      AttritionRate=("AttritionFlag", "mean")).reset_index())
        seg = seg[seg["Employees"] >= 15].copy()
        seg["AttritionRate"] = (seg["AttritionRate"] * 100).round(1)
        seg = seg.sort_values("AttritionRate", ascending=False).head(10)
        show_df(seg, column_config={
            "AttritionRate": st.column_config.ProgressColumn("Attrition %", min_value=0, max_value=100,
                                                              format="%.1f%%")})
    with st.expander("Show full correlation matrix", expanded=False):
        show(C.corr_heatmap(df))

    st.markdown("##### 🔍 Relationship explorer")
    num_cols = ["Age", "MonthlyIncome", "TotalWorkingYears", "YearsAtCompany", "YearsInCurrentRole",
                "YearsSinceLastPromotion", "YearsWithCurrManager", "DistanceFromHome", "PercentSalaryHike",
                "HourlyRate", "DailyRate", "MonthlyRate", "NumCompaniesWorked", "AvgSatisfaction"]
    x1, x2, x3 = st.columns(3)
    xv = x1.selectbox("X axis", num_cols, index=num_cols.index("TotalWorkingYears"))
    yv = x2.selectbox("Y axis", num_cols, index=num_cols.index("MonthlyIncome"))
    cv = x3.selectbox("Colour by", ["Attrition", "Department", "Gender", "OverTime", "JobRole", "MaritalStatus"])
    fig = px.scatter(df, x=xv, y=yv, color=cv, opacity=0.7, hover_data=["EmpID", "JobRole"],
                     color_discrete_map=C.ATTR_COLORS if cv == "Attrition" else None,
                     color_discrete_sequence=C.SEQ, title=f"{yv} vs {xv}")
    fig.update_traces(marker=dict(size=7))
    show(C.style(fig, 480))

# ------------------------------------------------------------------ DATA & QUALITY
with tab_data:
    st.markdown("#### 🧹 Cleaning summary")
    q1, q2, q3, q4 = st.columns(4)
    q1.markdown(kpi("Rows (raw → clean)", f"{len(raw_df):,} → {len(df_all):,}", "duplicates removed", C.NAVY),
                unsafe_allow_html=True)
    q2.markdown(kpi("Columns (raw → clean)", f"{raw_df.shape[1]} → {df_all.shape[1]}", "constants dropped, features added", C.TEAL),
                unsafe_allow_html=True)
    q3.markdown(kpi("Missing cells (raw)", f"{int(raw_df.isna().sum().sum())}", "all in YearsWithCurrManager", C.CORAL),
                unsafe_allow_html=True)
    q4.markdown(kpi("Missing cells (clean)", f"{int(df_all.drop(columns=['IncomePerYearExp']).isna().sum().sum())}",
                    "IncomePerYearExp n/a when experience = 0", C.SAND), unsafe_allow_html=True)
    st.write("")
    show_df(pd.DataFrame(clean_log))

    st.markdown("#### 📋 Data explorer")
    default_cols = ["EmpID", "Age", "Gender", "Department", "JobRole", "MonthlyIncome", "YearsAtCompany",
                    "OverTime", "AvgSatisfaction", "Attrition"]
    chosen = st.multiselect("Columns to display", list(df.columns), default=default_cols)
    view = df[chosen] if chosen else df
    show_df(view, height=380)

    d_a, d_b, _ = st.columns([1, 1, 2])
    d_a.download_button("⬇️ Filtered data (CSV)", df.to_csv(index=False).encode("utf-8"),
                        "hr_filtered.csv", "text/csv")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df_all.to_excel(xl, index=False, sheet_name="Cleaned_Data")
    d_b.download_button("⬇️ Full cleaned data (Excel)", buf.getvalue(), "HR_Analytics_cleaned.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander("Statistical summary of the filtered data"):
        show_df(df.describe().T.round(2).reset_index().rename(columns={"index": "Feature"}))

st.caption("Built with Streamlit & Plotly · Data: HR_Analytics.xlsx · Attrition = share of employees with Attrition = Yes")
