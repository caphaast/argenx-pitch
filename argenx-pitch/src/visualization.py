"""Charts: titled, labeled axes, source note, observed vs modeled labelled."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SRC_CO = "Source: argenx quarterly releases (SEC 6-K filings); own calculations."


def _finish(fig, ax, title, xl, yl, note, path):
    ax.set_title(title, fontsize=11, fontweight="bold", loc="left")
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    ax.grid(alpha=0.3)
    fig.text(0.01, 0.005, note, fontsize=6.5, color="#555", wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_sales_growth(g: pd.DataFrame, path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(g.index, g["sales"], color="#1f4e79")
    ax.set_ylim(0, g["sales"].max() * 1.25)
    ax2 = ax.twinx()
    ax2.plot(g.index, g["yoy_pct"] * 100, color="crimson", marker="o", label="YoY growth (%)")
    ax2.set_ylabel("YoY growth (%)")
    ax2.legend(loc="upper right", fontsize=8)
    for i, v in enumerate(g["sales"]):
        ax.text(i, v + 20, f"{v:,.0f}", ha="center", fontsize=7)
    plt.setp(ax.get_xticklabels(), rotation=45)
    return _finish(fig, ax, "VYVGART product net sales by quarter and YoY growth (reported)", "Quarter",
                   "Product net sales (USD m)", SRC_CO + " 100% of product net sales are VYVGART franchise.", path)


def plot_qoq(g: pd.DataFrame, path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    q = g["qoq_pct"].dropna() * 100
    ax.bar(q.index, q.values, color=["#c62828" if i.endswith("Q1") else "#1f4e79" for i in q.index])
    for i, v in enumerate(q.values):
        ax.text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=7)
    plt.setp(ax.get_xticklabels(), rotation=45)
    return _finish(fig, ax, "Quarter-on-quarter growth (red = Q1, seasonally weak)", "Quarter", "QoQ growth (%)",
                   SRC_CO + " Q1 pattern may reflect gross-to-net/inventory effects (hypothesis, not verified).", path)


def plot_regional(mix: pd.DataFrame, path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bottom = np.zeros(len(mix))
    for c in mix.columns:
        ax.bar(mix.index, mix[c] * 100, bottom=bottom, label=c.replace("_share", ""))
        bottom += mix[c].to_numpy() * 100
    ax.legend(fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45)
    return _finish(fig, ax, "Sales by region, share of total (reported; through Q3 2025 only)", "Quarter", "Share of product net sales (%)",
                   SRC_CO + " Regional split for later quarters not collected.", path)


def plot_margin(m: pd.DataFrame, path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(m.index, m["op_margin_on_product_sales"] * 100, marker="o")
    plt.setp(ax.get_xticklabels(), rotation=45)
    return _finish(fig, ax, "Operating profit / product net sales (calculated)", "Quarter", "Margin (%)",
                   SRC_CO + " 2025Q3 operating profit derived (FY minus H1 minus Q4).", path)


def plot_scenarios(scen: pd.DataFrame, price: float, path) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.4))
    cols = {"bear": "#c62828", "base": "#757575", "bull": "#2e7d32"}
    for i, (n, r) in enumerate(scen.iterrows()):
        ax.bar(i, r["value_12m"], color=cols[n])
        ax.text(i, r["value_12m"] + 20, f"${r['value_12m']:,.0f}\n({r['return_12m']:+.0%})", ha="center", fontsize=9)
    ax.axhline(price, color="black", ls="--", label=f"Price ${price:,.2f} (2026-10-09, secondary source)")
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels(scen.index)
    ax.set_ylim(0, scen["value_12m"].max() * 1.25)
    ax.legend(fontsize=8, loc="upper left")
    return _finish(fig, ax, "argenx: 12-month scenario values vs current price (modeled, analyst assumptions)", "Scenario",
                   "Value per share (USD)", "Value = FY2027E diluted EPS x exit P/E. Not a forecast; see config/valuation_inputs.yaml.", path)


def plot_heatmap(grid: pd.DataFrame, title, xl, yl, path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 4.4))
    im = ax.imshow(grid.values.astype(float) * 100, cmap="RdYlGn", aspect="auto", vmin=-60, vmax=100)
    ax.set_xticks(range(grid.shape[1]))
    ax.set_xticklabels([f"{c:.0f}x" for c in grid.columns])
    ax.set_yticks(range(grid.shape[0]))
    ax.set_yticklabels([f"{i:.0%}" for i in grid.index])
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, f"{grid.values[i, j] * 100:.0f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="12m return (%)")
    return _finish(fig, ax, title, xl, yl, "Modeled grid using base-case 2026 path and margins; analyst assumptions.", path)


def plot_car(res: pd.DataFrame, car_col: str, path) -> Path | None:
    ok = res[res["status"] == "ok"]
    if ok.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.4))
    colors = {"positive": "#2e7d32", "negative": "#c62828", "mixed": "#f9a825", "neutral": "#757575"}
    ax.bar(range(len(ok)), ok[car_col] * 100, color=[colors.get(d, "#757575") for d in ok["direction"]])
    ax.set_xticks(range(len(ok)))
    ax.set_xticklabels([f"{r.event_id}\n{r.event_day}" for r in ok.itertuples()], fontsize=7)
    for i, r in enumerate(ok.itertuples()):
        if getattr(r, "overlap_flag", False):
            ax.text(i, 0, "*", ha="center", va="bottom", fontsize=14)
    ax.axhline(0, color="k", lw=0.8)
    return _finish(fig, ax, f"Abnormal returns around verified events, {car_col} (model-based, exploratory)", "Event",
                   "Cumulative abnormal return (%)", "Market model vs XBI. * = overlapping/confounded news. Color = expected direction. No causal claim.", path)
