"""Commercial growth analysis from reported quarterly figures (data/quarterly_sales.csv, official sources)."""
from __future__ import annotations

import pandas as pd

from .data_validation import ValidationReport

REQUIRED = ["quarter", "period_end", "product_net_sales_usd_m", "source_url", "source_type"]
REGION_COLS = ["us_usd_m", "japan_usd_m", "row_usd_m", "china_supply_usd_m"]


def load_sales(path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["period_end"])
    return df.sort_values("period_end").reset_index(drop=True)


def validate_sales(df: pd.DataFrame, tol: float = 3.0) -> ValidationReport:
    rep = ValidationReport()
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        rep.add("ERROR", "columns", f"missing columns {miss}")
        return rep
    if df["quarter"].duplicated().any():
        rep.add("ERROR", "dup", "duplicate quarters")
    if not df["period_end"].is_monotonic_increasing:
        rep.add("ERROR", "order", "quarters not in chronological order")
    if (df["product_net_sales_usd_m"] <= 0).any() or df["product_net_sales_usd_m"].isna().any():
        rep.add("ERROR", "values", "non-positive or missing sales")
    if df["source_url"].isna().any():
        rep.add("ERROR", "source", "every row needs a source_url")
    have = df[REGION_COLS].notna().all(axis=1)
    diff = (df.loc[have, REGION_COLS].sum(axis=1) - df.loc[have, "product_net_sales_usd_m"]).abs()
    if (diff > tol).any():
        bad = df.loc[have][diff > tol]["quarter"].tolist()
        rep.add("ERROR", "region_sum", f"regions do not sum to total (tolerance ${tol}m) in {bad}")
    gaps = df["period_end"].diff().dt.days.dropna()
    if ((gaps < 85) | (gaps > 95)).any():
        rep.add("WARN", "gap", "quarters are not consecutive")
    n_sec = int((df["source_type"] != "primary").sum())
    if n_sec:
        rep.add("WARN", "secondary", f"{n_sec} rows from non-primary sources")
    return rep


def growth_table(df: pd.DataFrame) -> pd.DataFrame:
    s = df.set_index("quarter")["product_net_sales_usd_m"]
    out = pd.DataFrame({"sales": s})
    out["qoq_pct"] = s / s.shift(1) - 1
    out["yoy_pct"] = s / s.shift(4) - 1
    out["qoq_abs"] = s - s.shift(1)
    out["yoy_abs"] = s - s.shift(4)
    out["ttm_sales"] = s.rolling(4).sum()
    out["yoy_pct_change_pts"] = out["yoy_pct"] - out["yoy_pct"].shift(1)   # acceleration (+) / deceleration (-)
    return out


def margin_table(df: pd.DataFrame) -> pd.DataFrame:
    d = df.set_index("quarter")[["product_net_sales_usd_m", "operating_profit_usd_m"]].dropna()
    d["op_margin_on_product_sales"] = d["operating_profit_usd_m"] / d["product_net_sales_usd_m"]
    return d


def regional_mix(df: pd.DataFrame) -> pd.DataFrame:
    d = df.set_index("quarter")[REGION_COLS + ["product_net_sales_usd_m"]].dropna()
    mix = d[REGION_COLS].div(d[REGION_COLS].sum(axis=1), axis=0)
    mix.columns = [c.replace("_usd_m", "_share") for c in mix.columns]
    return mix
