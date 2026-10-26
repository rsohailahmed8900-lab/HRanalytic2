"""Standalone cleaning script: writes the cleaned dataset + cleaning log to ./data

Usage:  python clean_and_export.py
"""
from pathlib import Path

import pandas as pd

from utils.data_cleaning import clean_data, load_raw

OUT = Path(__file__).parent / "data"

raw = load_raw()
clean, log = clean_data(raw)
clean.to_csv(OUT / "HR_Analytics_cleaned.csv", index=False)
pd.DataFrame(log).to_csv(OUT / "cleaning_log.csv", index=False)
print(f"Raw {raw.shape} -> Clean {clean.shape}")
for entry in log:
    print(f" - {entry['Step']}: {entry['Issue found']} ({entry['Affected']})")
print(f"Saved to {OUT}")
