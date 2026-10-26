"""Data loading and cleaning for the HR Analytics dataset.

Every cleaning step is recorded in a log so the dashboard can show
exactly what was changed and why (full transparency).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "HR_Analytics.xlsx"

# Ordinal label maps (standard IBM HR coding)
EDUCATION_MAP = {1: "Below College", 2: "College", 3: "Bachelor", 4: "Master", 5: "Doctor"}
SATISFACTION_MAP = {1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
WLB_MAP = {1: "Bad", 2: "Good", 3: "Better", 4: "Best"}
PERFORMANCE_MAP = {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"}

AGE_ORDER = ["18-25", "26-35", "36-45", "46-55", "55+"]
SLAB_ORDER = ["Upto 5k", "5k-10k", "10k-15k", "15k+"]
TENURE_ORDER = ["0-2 yrs", "3-5 yrs", "6-10 yrs", "11-20 yrs", "20+ yrs"]


def load_raw(path: Path | str = DATA_PATH) -> pd.DataFrame:
    return pd.read_excel(path)


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Return (clean_df, cleaning_log)."""
    df = raw.copy()
    log: list[dict] = []

    def add(step: str, issue: str, action: str, affected) -> None:
        log.append({"Step": step, "Issue found": issue, "Action taken": action, "Affected": affected})

    # 1. Standardise text columns (strip whitespace)
    for c in df.columns:
        if df[c].dtype == object or str(df[c].dtype) in ("str", "string"):
            df[c] = df[c].astype(str).str.strip()

    # 2. Fix inconsistent category spelling
    n_typo = int((df["BusinessTravel"] == "TravelRarely").sum())
    df["BusinessTravel"] = df["BusinessTravel"].replace({"TravelRarely": "Travel_Rarely"})
    add("Standardise categories", "'TravelRarely' used instead of 'Travel_Rarely' in BusinessTravel",
        "Merged into 'Travel_Rarely'", f"{n_typo} rows")

    # 3. Remove duplicates (exact duplicates, then duplicate employee IDs)
    n_exact = int(df.duplicated().sum())
    df = df.drop_duplicates()
    add("Remove duplicates", "Fully identical rows", "Dropped, kept first occurrence", f"{n_exact} rows")

    n_id = int(df["EmpID"].duplicated().sum())
    df = df.drop_duplicates(subset="EmpID", keep="first")
    add("Remove duplicates",
        "Same EmpID repeated with conflicting 'YearsWithCurrManager' values",
        "Kept first record per EmpID (EmpID must be unique)", f"{n_id} rows")

    # 4. Missing values
    n_missing = int(df["YearsWithCurrManager"].isna().sum())
    df["YearsWithCurrManager_Imputed"] = df["YearsWithCurrManager"].isna()
    grp_median = df.groupby("YearsInCurrentRole")["YearsWithCurrManager"].transform("median")
    df["YearsWithCurrManager"] = df["YearsWithCurrManager"].fillna(grp_median)
    df["YearsWithCurrManager"] = df["YearsWithCurrManager"].fillna(df["YearsWithCurrManager"].median())
    df["YearsWithCurrManager"] = df["YearsWithCurrManager"].round().astype(int)
    add("Handle missing values",
        "Missing 'YearsWithCurrManager' (correlates ~0.71 with YearsInCurrentRole)",
        "Imputed with the median of employees sharing the same YearsInCurrentRole; "
        "flagged in 'YearsWithCurrManager_Imputed'", f"{n_missing} rows")

    # 5. Drop zero-information columns
    const_cols = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
    df = df.drop(columns=const_cols)
    add("Drop constant columns", f"No variance: {', '.join(const_cols)}", "Removed", f"{len(const_cols)} cols")

    # 6. Drop redundant ID column
    df = df.drop(columns=["EmployeeNumber"])
    add("Drop redundant columns", "EmployeeNumber is a second identifier that was also duplicated; EmpID is the key",
        "Removed", "1 col")

    # 7. Feature engineering
    df["AttritionFlag"] = (df["Attrition"] == "Yes").astype(int)
    df["EducationLabel"] = df["Education"].map(EDUCATION_MAP)
    df["JobSatisfactionLabel"] = df["JobSatisfaction"].map(SATISFACTION_MAP)
    df["EnvSatisfactionLabel"] = df["EnvironmentSatisfaction"].map(SATISFACTION_MAP)
    df["RelSatisfactionLabel"] = df["RelationshipSatisfaction"].map(SATISFACTION_MAP)
    df["WorkLifeBalanceLabel"] = df["WorkLifeBalance"].map(WLB_MAP)
    df["PerformanceLabel"] = df["PerformanceRating"].map(PERFORMANCE_MAP)
    df["AvgSatisfaction"] = df[["JobSatisfaction", "EnvironmentSatisfaction",
                                "RelationshipSatisfaction", "WorkLifeBalance"]].mean(axis=1).round(2)
    df["TenureBucket"] = pd.cut(df["YearsAtCompany"], [-1, 2, 5, 10, 20, 100], labels=TENURE_ORDER).astype(str)
    df["PromotionStatus"] = np.where(df["YearsSinceLastPromotion"] >= 5,
                                     "5+ yrs since promotion", "Promoted within 5 yrs")
    df["IncomePerYearExp"] = (df["MonthlyIncome"] / df["TotalWorkingYears"].replace(0, np.nan)).round(0)
    add("Feature engineering", "Coded 1-4 / 1-5 scales are hard to read",
        "Added AttritionFlag, readable label columns, AvgSatisfaction, TenureBucket, PromotionStatus, "
        "IncomePerYearExp", "10 new cols")

    # 8. Validation checks
    assert df["EmpID"].is_unique, "EmpID must be unique"
    assert not df.drop(columns=["IncomePerYearExp"]).isna().any().any(), "Unexpected nulls"
    assert (df["YearsAtCompany"] <= df["TotalWorkingYears"]).all(), "Tenure > career length"

    return df.reset_index(drop=True), log


def get_clean_data():
    raw = load_raw()
    clean, log = clean_data(raw)
    return raw, clean, log
