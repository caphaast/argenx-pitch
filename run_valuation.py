"""Scenario + reverse valuation -> outputs/tables/valuation_*.csv and figures. Runs offline."""
import pandas as pd

from src import valuation as v
from src import visualization as viz
from src.config import load_config, resolve

cfg = load_config()
tabs, figs = resolve("outputs/tables"), resolve("outputs/figures")
inp = v.load(resolve(cfg["files"]["valuation_inputs"]))
scen, rev, sens, tm = v.scenario_table(inp), v.reverse_valuation(inp), v.sensitivity(inp), v.trailing_metrics(inp)
scen.to_csv(tabs / "valuation_scenarios.csv"); rev.to_csv(tabs / "valuation_reverse.csv", index=False)
sens.to_csv(tabs / "valuation_sensitivity.csv"); pd.Series(tm).to_csv(tabs / "valuation_market_metrics.csv", header=["value"])
pd.set_option("display.width", 200)
print("== Market-implied (as of", inp["facts"]["as_of"], ") ==\n", pd.Series(tm).round(2).to_string())
print("\n== Scenarios ==\n", scen.round(2).to_string())
print("\n== Reverse valuation (FY2030E sales needed) ==\n", rev.round(3).to_string(index=False))
print("\n== Sensitivity: 12m return (%) ==\n", (sens * 100).round(0).to_string())
viz.plot_scenarios(scen, inp["facts"]["price_usd"], figs / "05_scenarios.png")
viz.plot_heatmap(sens, "argenx: 12m return vs FY2027E sales growth and exit P/E (modeled)", "Exit P/E (analyst assumption)",
                 "FY2027E sales growth (analyst assumption)", figs / "06_sensitivity.png")
