"""Commercial growth analysis -> outputs/tables/growth_*.csv and figures. Runs offline from data/quarterly_sales.csv."""
from src import growth as g
from src import pipeline_data as pdta
from src import visualization as viz
from src.config import load_config, resolve

cfg = load_config()
tabs, figs = resolve("outputs/tables"), resolve("outputs/figures")
df = g.load_sales(resolve(cfg["files"]["sales"]))
rep = g.validate_sales(df)
print("== Sales data validation ==\n" + rep.summary())
rep.raise_if_errors()
t, m, mix = g.growth_table(df), g.margin_table(df), g.regional_mix(df)
t.to_csv(tabs / "growth_table.csv"); m.to_csv(tabs / "margin_table.csv"); mix.to_csv(tabs / "regional_mix.csv")
print("\n== Growth ==\n" + t.round(3).to_string())
print("\n== Operating margin on product sales ==\n" + m.round(3).to_string())
print("\n== Regional mix ==\n" + mix.round(3).to_string())
viz.plot_sales_growth(t, figs / "01_sales_growth.png")
viz.plot_qoq(t, figs / "02_qoq_growth.png")
viz.plot_regional(mix, figs / "03_regional_mix.png")
viz.plot_margin(m, figs / "04_op_margin.png")
pl = pdta.load_pipeline(resolve(cfg["files"]["pipeline"]))
prep = pdta.validate_pipeline(pl)
print("\n== Pipeline table validation ==\n" + prep.summary())
prep.raise_if_errors()
pdta.upcoming_catalysts(pl).to_csv(tabs / "upcoming_catalysts.csv", index=False)
print("\n== Upcoming catalysts ==\n" + pdta.upcoming_catalysts(pl).to_string())
