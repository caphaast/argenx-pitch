"""Structured clinical pipeline table (data/pipeline.csv) with validation."""
from __future__ import annotations

import pandas as pd

from .data_validation import ValidationReport

COLUMNS = ["asset", "indication", "stage_or_status", "trial", "result_or_status", "result_date", "next_catalyst",
           "expected_timing", "nct_id", "source_url", "source_type", "verified", "notes"]


def load_pipeline(path) -> pd.DataFrame:
    return pd.read_csv(path)


def validate_pipeline(df: pd.DataFrame) -> ValidationReport:
    rep = ValidationReport()
    miss = [c for c in COLUMNS if c not in df.columns]
    if miss:
        rep.add("ERROR", "columns", f"missing columns {miss}")
        return rep
    if df["source_url"].isna().any():
        rep.add("ERROR", "source", "every row needs a source_url")
    if not set(df["source_type"].dropna()) <= {"primary", "secondary"}:
        rep.add("ERROR", "source_type", "source_type must be primary or secondary")
    bad = df[(df["verified"].astype(str).str.lower() == "true") & (df["source_type"] != "primary")]
    if len(bad):
        rep.add("ERROR", "verified_needs_primary", f"verified=true requires a primary source: {bad['asset'].tolist()}")
    n_unv = int((df["verified"].astype(str).str.lower() != "true").sum())
    if n_unv:
        rep.add("WARN", "unverified", f"{n_unv} rows are not verified against primary sources")
    d = pd.to_datetime(df["result_date"], errors="coerce", format="mixed")
    if (d.notna() & (d > pd.Timestamp("2026-10-11"))).any():
        rep.add("ERROR", "future_date", "result_date is after the research cutoff")
    return rep


def upcoming_catalysts(df: pd.DataFrame) -> pd.DataFrame:
    c = df[df["next_catalyst"].notna() & df["expected_timing"].notna()]
    return c[["asset", "indication", "next_catalyst", "expected_timing", "source_type", "verified"]].reset_index(drop=True)
