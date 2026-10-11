"""Exploratory event study: market model (stock ~ benchmark), abnormal returns, volume ratio, placebo comparison.

Timing is decided by the TRADING venue's hours (default Nasdaq for the ADS). Announcements made before the
open map to that day (day 0 = full reaction); during hours = same day (reaction only partly in day 0);
after the close / non-trading day = next trading day.
Placebo: the same CAR computed on every other (non-event) window in the sample shows how unusual an event CAR
is relative to this stock's ordinary 2-day noise. This is descriptive, not causal.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MarketHours:
    tz: str
    open: time
    close: time


NASDAQ = MarketHours("America/New_York", time(9, 30), time(16, 0))
SIX = MarketHours("Europe/Zurich", time(9, 0), time(17, 30))
EURONEXT = MarketHours("Europe/Brussels", time(9, 0), time(17, 30))
MARKETS = {"nasdaq": NASDAQ, "six": SIX, "euronext": EURONEXT}


def assign_event_day(ts, trading_days: pd.DatetimeIndex, hours: MarketHours = SIX) -> tuple[pd.Timestamp, str]:
    ts = pd.Timestamp(ts)
    ts = ts.tz_localize(hours.tz) if ts.tzinfo is None else ts
    ts = ts.tz_convert(hours.tz)
    day = ts.tz_localize(None).normalize()
    t = ts.time()
    is_td = day in trading_days
    if t >= hours.close or not is_td:
        pos = trading_days.searchsorted(day, side="right")
        timing = "post_close" if is_td else "non_trading_day"
    else:
        pos = trading_days.searchsorted(day, side="left")
        timing = "pre_open" if t < hours.open else "intraday"
    if pos >= len(trading_days):
        raise ValueError(f"No trading day on/after {ts} in the price data.")
    return trading_days[pos], timing


def _fit(stock: np.ndarray, bench: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(bench, stock, 1)
    resid = stock - (intercept + slope * bench)
    return intercept, slope, float(resid.std(ddof=2))


def placebo_cars(returns: pd.DataFrame, stock: str, bench: str, est_window: tuple[int, int],
                 windows: list[tuple[int, int]], exclude_pos: list[int], excl_days: int,
                 min_obs: int) -> dict[tuple[int, int], np.ndarray]:
    """CAR for every non-event window using the same estimation-window recipe."""
    a, b = est_window
    n = len(returns)
    r, m = returns[stock].to_numpy(), returns[bench].to_numpy()
    hi_max = max(w[1] for w in windows)
    out = {w: [] for w in windows}
    for p in range(-a, n - hi_max):
        if any(abs(p - q) <= excl_days for q in exclude_pos):
            continue
        sl = slice(p + a, p + b + 1)
        rs, ms = r[sl], m[sl]
        ok = ~(np.isnan(rs) | np.isnan(ms))
        if ok.sum() < min_obs:
            continue
        alpha, beta, _ = _fit(rs[ok], ms[ok])
        for lo, hi in windows:
            seg = slice(p + lo, p + hi + 1)
            out[(lo, hi)].append(float((r[seg] - (alpha + beta * m[seg])).sum()))
    return {w: np.array(v) for w, v in out.items()}


def run_event_study(events: pd.DataFrame, returns: pd.DataFrame, stock: str = "stock", bench: str = "benchmark",
                    hours: MarketHours = NASDAQ, est_window: tuple[int, int] = (-120, -21),
                    windows: list[tuple[int, int]] | None = None, min_est_obs: int = 60,
                    volume: pd.Series | None = None, placebo_excl_days: int = 6) -> pd.DataFrame:
    windows = windows or [(0, 0), (0, 1), (-1, 1), (0, 5)]
    idx = returns.index
    ev = events[events["verified"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
    pos, timing = {}, {}
    for _, e in ev.iterrows():
        tz = e["timezone"] if isinstance(e.get("timezone"), str) and e["timezone"] else hours.tz
        ts = pd.Timestamp(e["announce_datetime"])
        ts = ts.tz_localize(tz) if ts.tzinfo is None else ts
        try:
            day, tm = assign_event_day(ts, idx, hours)
        except ValueError:
            continue
        pos[e["event_id"]], timing[e["event_id"]] = idx.get_loc(day), tm
    max_w = max(abs(w) for pair in windows for w in pair)
    placebo = placebo_cars(returns, stock, bench, est_window, windows, list(pos.values()), placebo_excl_days, min_est_obs)
    rows = []
    for _, e in ev.iterrows():
        eid = e["event_id"]
        if eid not in pos:
            continue
        p = pos[eid]
        row = {"event_id": eid, "category": e["category"], "direction": e["direction"],
               "event_day": idx[p].date(), "timing": timing[eid],
               "same_day_events": sum(1 for q in pos.values() if q == p) - 1,
               "overlap_flag": any(q != p and abs(q - p) <= max_w + 1 for q in pos.values()) or
                               sum(1 for q in pos.values() if q == p) > 1}
        a, b = est_window
        if p + a < 0:
            rows.append({**row, "status": "insufficient_data"})
            continue
        est = returns.iloc[p + a:p + b + 1][[stock, bench]].dropna()
        if len(est) < min_est_obs:
            rows.append({**row, "status": "insufficient_estimation_obs"})
            continue
        alpha, beta, sigma = _fit(est[stock].to_numpy(), est[bench].to_numpy())
        row.update({"status": "ok", "alpha": alpha, "beta": beta, "n_est": len(est), "resid_sd": sigma,
                    "raw_return_day0": float(returns[stock].iloc[p])})
        unavailable = []
        for lo, hi in windows:
            if p + hi >= len(idx) or p + lo < 0:      # window runs past the data: report NaN, never drop the event
                unavailable.append(f"[{lo},{hi}]")
                for k in ("CAR", "t", "placebo_pctile_abs"):
                    row[f"{k}[{lo},{hi}]"] = np.nan
                continue
            w = returns.iloc[p + lo:p + hi + 1]
            car = float((w[stock] - (alpha + beta * w[bench])).sum())
            row[f"CAR[{lo},{hi}]"] = car
            row[f"t[{lo},{hi}]"] = car / (sigma * np.sqrt(len(w))) if sigma > 0 else np.nan
            pl = placebo[(lo, hi)]
            row[f"placebo_pctile_abs[{lo},{hi}]"] = float((np.abs(pl) <= abs(car)).mean()) if len(pl) else np.nan
        row["windows_unavailable"] = ",".join(unavailable)
        if volume is not None:
            vmed = float(volume.iloc[p + a:p + b + 1].median())
            row["volume_ratio_day0"] = float(volume.iloc[p] / vmed) if vmed > 0 else np.nan
            row["volume_ratio_day1"] = float(volume.iloc[p + 1] / vmed) if (vmed > 0 and p + 1 < len(idx)) else np.nan
        rows.append(row)
    res = pd.DataFrame(rows)
    res.attrs["n_placebo"] = {f"{w}": int(len(v)) for w, v in placebo.items()}
    return res
