import numpy as np
import pandas as pd
import pytest

from src.event_study import NASDAQ, SIX, assign_event_day, placebo_cars, run_event_study
from tests.synthetic import make_returns


def test_nasdaq_event_day_for_7am_cet_announcement():
    days = pd.bdate_range("2026-10-01", "2026-10-30")
    d, t = assign_event_day(pd.Timestamp("2026-10-08 07:00", tz="Europe/Amsterdam"), days, NASDAQ)
    assert (str(d.date()), t) == ("2026-10-08", "pre_open")      # 01:00 New York time, before the open


def test_after_close_and_weekend_roll_forward():
    days = pd.bdate_range("2026-10-01", "2026-10-30")
    d, t = assign_event_day(pd.Timestamp("2026-10-08 17:00", tz="America/New_York"), days, NASDAQ)
    assert (str(d.date()), t) == ("2026-10-09", "post_close")
    d, t = assign_event_day(pd.Timestamp("2026-10-10 12:00", tz="America/New_York"), days, NASDAQ)   # Saturday
    assert (str(d.date()), t) == ("2026-10-12", "non_trading_day")
    d, t = assign_event_day(pd.Timestamp("2026-10-08 12:00", tz="America/New_York"), days, NASDAQ)
    assert t == "intraday"


def test_six_hours_still_work_for_naive_timestamps():
    days = pd.bdate_range("2024-03-01", "2024-03-29")
    d, t = assign_event_day(pd.Timestamp("2024-03-05 18:30"), days, SIX)
    assert (str(d.date()), t) == ("2024-03-06", "post_close")


def _ev(eid, ts, direction="negative", verified=True):
    return {"event_id": eid, "company": "argenx", "product": "p", "category": "clinical", "announce_datetime": ts,
            "timezone": "Europe/Amsterdam", "source_url": "http://x", "description": "d", "direction": direction,
            "rationale": "r", "verified": verified, "confounders": ""}


def test_injected_jump_recovered_and_placebo_percentile_is_extreme():
    r = make_returns(700, seed=3)
    r["stock"] = 0.0002 + 1.1 * r["benchmark"] + np.random.default_rng(9).normal(0, 0.01, len(r))
    day = r.index[450]
    r.loc[day, "stock"] -= 0.12
    ev = pd.DataFrame([_ev("e1", f"{day.date()} 07:00")])
    vol = pd.Series(1_000_000.0, index=r.index)
    vol.loc[day] = 5_000_000.0
    res = run_event_study(ev, r, volume=vol)
    row = res.iloc[0]
    assert row["status"] == "ok" and row["timing"] == "pre_open"
    assert row["CAR[0,0]"] == pytest.approx(-0.12, abs=0.03)
    assert row["placebo_pctile_abs[0,0]"] > 0.99
    assert row["volume_ratio_day0"] == pytest.approx(5.0)
    assert res.attrs["n_placebo"]["(0, 0)"] > 300


def test_ordinary_day_is_not_extreme_vs_placebo():
    r = make_returns(700, seed=5)
    day = r.index[450]
    res = run_event_study(pd.DataFrame([_ev("e1", f"{day.date()} 07:00")]), r)
    assert res.iloc[0]["placebo_pctile_abs[0,0]"] < 0.99


def test_unverified_excluded_and_same_day_overlap_flagged():
    r = make_returns(700, seed=4)
    d = r.index[450]
    ev = pd.DataFrame([_ev("a", f"{d.date()} 07:00"), _ev("b", f"{d.date()} 07:00", "positive"),
                       _ev("c", f"{r.index[300].date()} 07:00", verified=False)])
    res = run_event_study(ev, r)
    assert set(res["event_id"]) == {"a", "b"}
    assert res["overlap_flag"].all() and (res["same_day_events"] == 1).all()


def test_placebo_excludes_event_neighbourhood():
    r = make_returns(400, seed=1)
    allp = placebo_cars(r, "stock", "benchmark", (-120, -21), [(0, 0)], [], 6, 60)[(0, 0)]
    some = placebo_cars(r, "stock", "benchmark", (-120, -21), [(0, 0)], [300], 6, 60)[(0, 0)]
    assert len(allp) - len(some) == 13       # positions 294..306 removed


def test_event_near_end_of_data_keeps_available_windows():
    r = make_returns(700, seed=6)
    day = r.index[-2]                     # only day 0 and day +1 exist
    res = run_event_study(pd.DataFrame([_ev("e1", f"{day.date()} 07:00")]), r)
    row = res.iloc[0]
    assert row["status"] == "ok"
    assert not np.isnan(row["CAR[0,1]"]) and np.isnan(row["CAR[0,5]"])
    assert row["windows_unavailable"] == "[0,5]"
