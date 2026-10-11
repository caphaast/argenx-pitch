"""Event study on REAL prices. Prereq: python -m src.data_collection ; data/events.csv (verified events only)."""
import sys

import pandas as pd

from src import visualization as viz
from src.config import load_config, resolve
from src.data_collection import load_prices
from src.data_validation import align_common_dates, validate_events, validate_prices
from src.event_study import MARKETS, run_event_study

cfg = load_config()
tabs, figs = resolve("outputs/tables"), resolve("outputs/figures")
try:
    px = load_prices(cfg)
except FileNotFoundError as e:
    sys.exit(str(e))
v = cfg["validation"]
rep = validate_prices(px["adj"], v["max_abs_daily_return"], v["max_gap_days"], v["stale_run_length"])
adj, rep2 = align_common_dates(px["adj"])
rep.issues += rep2.issues
print("== Price validation ==\n" + rep.summary())
rep.to_frame().to_csv(tabs / "price_validation_report.csv", index=False)
rep.raise_if_errors()
rets = adj / adj.shift(1) - 1
rets = rets.iloc[1:]
vol = px["volume"]["stock"].reindex(rets.index)
ev = pd.read_csv(resolve(cfg["event_study"]["events_file"]))
erep = validate_events(ev)
print("\n== Events validation ==\n" + erep.summary())
erep.raise_if_errors()
es = cfg["event_study"]
res = run_event_study(ev, rets, "stock", "benchmark", MARKETS[cfg["market"]], tuple(es["estimation_window"]),
                      [tuple(w) for w in es["windows"]], es["min_estimation_obs"], vol, es["placebo_exclusion_days"])
res.to_csv(tabs / "event_study_results.csv", index=False)
pd.set_option("display.width", 220)
cols = [c for c in res.columns if c.startswith(("event_id", "event_day", "timing", "direction", "CAR", "placebo", "volume", "overlap", "status"))]
print("\n== Event study (exploratory) ==\n" + res[cols].round(3).to_string(index=False))
print("\nPlacebo windows per event window:", res.attrs.get("n_placebo"))
viz.plot_car(res, "CAR[0,1]", figs / "07_event_car.png")
