# 📊 HR Analytics Dashboard (Streamlit)

An interactive, cleaned and validated HR analytics report built from `HR_Analytics.xlsx`
(1,480 raw rows → **1,470 unique employees**, 46 analysis-ready columns).

## Quick start

```bash
# macOS / Linux                      # Windows
./run.sh                             run.bat
```

or manually:

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. Python 3.9+ required.

## Project structure

```
hr_analytics_dashboard/
├── app.py                  # Streamlit app (layout, filters, tabs)
├── clean_and_export.py     # Optional: export cleaned CSV + cleaning log
├── requirements.txt
├── run.sh / run.bat        # One-command launchers
├── .streamlit/config.toml  # Theme
├── data/
│   ├── HR_Analytics.xlsx           # Original dataset
│   ├── HR_Analytics_cleaned.csv    # Cleaned output
│   └── cleaning_log.csv            # Every cleaning step, documented
└── utils/
    ├── data_cleaning.py    # Cleaning + feature engineering (with log & validation asserts)
    ├── charts.py           # Plotly chart builders (consistent styling)
    └── insights.py         # Auto-generated, data-driven insights
```

## Data cleaning performed

| Issue | Action | Affected |
|---|---|---|
| `TravelRarely` vs `Travel_Rarely` | Standardised spelling | 8 rows |
| Exact duplicate rows | Removed | 7 rows |
| Repeated `EmpID` with conflicting `YearsWithCurrManager` | Kept first record per ID | 3 rows |
| Missing `YearsWithCurrManager` | Imputed with median of same `YearsInCurrentRole` (flag column kept) | 57 rows |
| Constant columns (`EmployeeCount`, `Over18`, `StandardHours`) | Dropped | 3 cols |
| Redundant `EmployeeNumber` | Dropped | 1 col |

**Engineered features:** `AttritionFlag`, readable labels for coded scales (education, satisfaction,
work-life balance, performance), `AvgSatisfaction`, `TenureBucket`, `PromotionStatus`, `IncomePerYearExp`.
Validation asserts (unique IDs, no nulls, tenure ≤ career length) run on every load.

## Dashboard tabs

1. **Overview** - 6 KPI cards, auto-generated insights, retention donut, department attrition, treemap
2. **Attrition deep-dive** - break attrition down by 14 dimensions, hot-spot heatmaps, tenure/commute distributions
3. **Compensation** - income by role/department, income vs experience, gender pay by level, hike vs performance
4. **Engagement** - radar of stayers vs leavers, attrition by every satisfaction scale
5. **Demographics** - gender, marital, age, education, travel
6. **Drivers & risk** - correlations with attrition, highest-risk segments, free-form scatter explorer
7. **Data & quality** - cleaning log, before/after metrics, data explorer, CSV / Excel download

**Sidebar filters** (department, role, gender, marital status, overtime, travel, age, income, tenure) apply to every tab.

## Headline findings (full workforce)

- Overall attrition: **16.1%**
- Overtime: **30.5%** attrition vs ~10% without
- Sales Representatives: **~40%**; employees aged 18-25: **~36%**; first 2 years of tenure: **~30%**
- Income under 5k/month: **~22%** vs **~4%** above 15k

> Correlations and segment rates are descriptive, not causal.
"# HRanalytic2" 
