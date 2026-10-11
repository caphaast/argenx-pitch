"""Data quality checks. Checks FLAG problems; they never silently fix or drop data.

Severity: ERROR = stop, WARN = review and document, INFO = good to know.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Issue:
    severity: str
    check: str
    message: str


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: str, check: str, message: str) -> None:
        self.issues.append(Issue(severity, check, message))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "ERROR"]

    def has_errors(self) -> bool:
        return bool(self.errors)

    def raise_if_errors(self) -> None:
        if self.has_errors():
            raise ValueError("Data validation failed:\n" + "\n".join(
                f"  [{i.check}] {i.message}" for i in self.errors))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([i.__dict__ for i in self.issues],
                            columns=["severity", "check", "message"])

    def summary(self) -> str:
        if not self.issues:
            return "No issues found."
        return "\n".join(f"[{i.severity}] {i.check}: {i.message}" for i in self.issues)


def validate_prices(prices: pd.DataFrame, max_abs_return: float = 0.12,
                    max_gap_days: int = 7, stale_run_length: int = 5) -> ValidationReport:
    """Validate a DataFrame of prices (index = dates, columns = series)."""
    rep = ValidationReport()
    if not isinstance(prices.index, pd.DatetimeIndex):
        rep.add("ERROR", "index_type", "Index is not a DatetimeIndex.")
        return rep
    if not prices.index.is_monotonic_increasing:
        rep.add("ERROR", "sorted", "Dates are not sorted ascending.")
    dups = prices.index[prices.index.duplicated()]
    if len(dups):
        rep.add("ERROR", "duplicates", f"{len(dups)} duplicate dates, e.g. {dups[0].date()}.")
    if prices.index.tz is not None:
        rep.add("WARN", "timezone", "Index is tz-aware; daily data should be tz-naive dates.")
    for col in prices.columns:
        s = prices[col]
        if not pd.api.types.is_numeric_dtype(s):
            rep.add("ERROR", "dtype", f"{col}: non-numeric dtype {s.dtype}.")
            continue
        n_nan = int(s.isna().sum())
        if n_nan:
            rep.add("WARN", "missing", f"{col}: {n_nan} missing values (first: {s[s.isna()].index[0].date()}).")
        n_bad = int((s <= 0).sum())
        if n_bad:
            rep.add("ERROR", "nonpositive", f"{col}: {n_bad} non-positive prices.")
        r = s.dropna().pipe(lambda x: x / x.shift(1) - 1).dropna()
        big = r[r.abs() > max_abs_return]
        if len(big):
            dates = ", ".join(str(d.date()) for d in big.index[:5])
            rep.add("WARN", "price_jump", f"{col}: {len(big)} daily moves > {max_abs_return:.0%} (e.g. {dates}). "
                    "Check for splits/data errors vs genuine events; NOT removed.")
        gaps = s.dropna().index.to_series().diff().dt.days
        long_gaps = gaps[gaps > max_gap_days]
        if len(long_gaps):
            rep.add("WARN", "gap", f"{col}: {len(long_gaps)} gaps > {max_gap_days} calendar days "
                    f"(first ends {long_gaps.index[0].date()}).")
        if stale_run_length > 1:
            same = s.dropna().diff().eq(0)
            run = same.groupby((~same).cumsum()).cumsum()
            if (run >= stale_run_length - 1).any():
                rep.add("WARN", "stale", f"{col}: price unchanged for >= {stale_run_length} consecutive days.")
    if prices.shape[1] > 1:
        na_any = prices.isna().any(axis=1)
        if na_any.any():
            rep.add("WARN", "calendar_mismatch",
                    f"{int(na_any.sum())} dates where at least one series is missing "
                    "(different trading calendars or gaps).")
    return rep


def align_common_dates(prices: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """Keep only dates where ALL series have a price. Reports exactly how many rows were dropped."""
    rep = ValidationReport()
    aligned = prices.dropna(how="any")
    dropped = len(prices) - len(aligned)
    rep.add("INFO", "alignment", f"Aligned on common dates: kept {len(aligned)} of {len(prices)} rows "
            f"({dropped} dropped because at least one series was missing).")
    return aligned, rep


def assert_no_leakage(train_index: pd.Index, test_index: pd.Index) -> None:
    """Raise if any training date is on/after the first test date (train/test must be chronological and disjoint)."""
    if len(train_index) == 0 or len(test_index) == 0:
        raise ValueError("Train or test index is empty.")
    if train_index.max() >= test_index.min():
        raise ValueError(f"Leakage: last train date {train_index.max().date()} >= first test date "
                         f"{test_index.min().date()}.")


EVENT_COLUMNS = ["event_id", "company", "product", "category", "announce_datetime", "timezone",
                 "source_url", "description", "direction", "rationale", "verified", "confounders"]


def validate_events(events: pd.DataFrame, allowed_companies: tuple = ("argenx",)) -> ValidationReport:
    rep = ValidationReport()
    missing = [c for c in EVENT_COLUMNS if c not in events.columns]
    if missing:
        rep.add("ERROR", "columns", f"events file missing columns: {missing}")
        return rep
    if events.empty:
        rep.add("ERROR", "empty", "events file has no rows.")
        return rep
    ts = pd.to_datetime(events["announce_datetime"], errors="coerce")
    if ts.isna().any():
        rep.add("ERROR", "datetime", f"{int(ts.isna().sum())} unparseable announce_datetime values.")
    if events["event_id"].duplicated().any():
        rep.add("ERROR", "dup_id", "duplicate event_id values.")
    key = events.assign(_d=ts.dt.date)[["company", "_d", "category", "product"]]
    if key.duplicated().any():
        rep.add("WARN", "dup_event", f"{int(key.duplicated().sum())} rows share company/date/category/product - possible duplicates.")
    if events["source_url"].isna().any() or (events["source_url"].astype(str).str.strip() == "").any():
        rep.add("ERROR", "source", "every event needs a source_url.")
    if not set(events["direction"].dropna().str.lower()) <= {"positive", "negative", "mixed", "neutral"}:
        rep.add("ERROR", "direction", "direction must be positive / negative / mixed / neutral.")
    if not events["company"].isin(allowed_companies).all():
        rep.add("ERROR", "company", f"company must be one of {sorted(allowed_companies)}.")
    unverified = int((~events["verified"].astype(str).str.lower().isin(["true", "1", "yes"])).sum())
    if unverified:
        rep.add("WARN", "unverified", f"{unverified} events not marked verified=true; they will be excluded from the study.")
    return rep
