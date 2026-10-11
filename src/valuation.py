"""argenx scenario valuation and reverse valuation.

Revenue path : FY2026E = H1 actual + Q3E + Q4E (Q3E = Q2 actual x (1+g_qoq), Q4E = Q3E x (1+g_qoq));
               FY2027E, FY2028E = prior year x (1 + growth).
Earnings     : net income = (operating margin x product net sales + net financial income) x (1 - tax rate).
EPS          : diluted, using the latest reported weighted diluted share count (held constant: a simplification).
12m value    : exit P/E x FY2027E diluted EPS (exit P/E applied to the then-current-year EPS at ~Oct 2027).
All scenario inputs are ANALYST ASSUMPTIONS (config/valuation_inputs.yaml); facts are separated and sourced.
"""
from __future__ import annotations

import pandas as pd
import yaml


def load(path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def project(inp: dict, s: dict) -> dict:
    f, h1 = inp["facts"], inp["facts"]["h1_2026"]
    shares = f["diluted_shares_m"]
    fin = s["net_financial_income_usd_m"]
    q3 = f["q2_2026_sales"] * (1 + s["qoq_h2_2026"])
    q4 = q3 * (1 + s["qoq_h2_2026"])
    rev26 = h1["product_net_sales"] + q3 + q4
    ni_h2 = (s["op_margin_2026_h2"] * (q3 + q4) + fin / 2) * (1 - s["tax_rate"])
    eps26 = h1["eps_diluted"] + ni_h2 / shares
    rev27 = rev26 * (1 + s["growth_2027"])
    eps27 = (s["op_margin_2027"] * rev27 + fin) * (1 - s["tax_rate"]) / shares
    rev28 = rev27 * (1 + s["growth_2028"])
    eps28 = (s["op_margin_2028"] * rev28 + fin) * (1 - s["tax_rate"]) / shares
    return {"rev_2026e": rev26, "rev_2027e": rev27, "rev_2028e": rev28,
            "eps_2026e": eps26, "eps_2027e": eps27, "eps_2028e": eps28}


def scenario_table(inp: dict) -> pd.DataFrame:
    price = inp["facts"]["price_usd"]
    rows = []
    for name, s in inp["scenarios"].items():
        p = project(inp, s)
        value = p["eps_2027e"] * s["exit_pe"]
        rows.append({"scenario": name, **p, "exit_pe": s["exit_pe"],
                     "pe_2026e_today": price / p["eps_2026e"], "pe_2027e_today": price / p["eps_2027e"],
                     "value_12m": value, "return_12m": value / price - 1})
    return pd.DataFrame(rows).set_index("scenario")


def trailing_metrics(inp: dict) -> dict:
    f = inp["facts"]
    ttm_eps = f["eps_diluted_fy2025"] - f["h1_2025"]["eps_diluted"] + f["h1_2026"]["eps_diluted"]
    mcap_diluted = f["price_usd"] * f["diluted_shares_m"]
    net_cash = f["cash_and_current_financial_assets_usd_m"]
    pro_forma = net_cash - f["forte_incremental_cash_consideration_est_usd_m"]
    return {"ttm_eps_diluted": ttm_eps, "pe_ttm": f["price_usd"] / ttm_eps,
            "market_cap_diluted_usd_m": mcap_diluted, "cash_30jun26_usd_m": net_cash,
            "cash_pro_forma_after_forte_usd_m_est": pro_forma,
            "ev_diluted_usd_m_pro_forma": mcap_diluted - pro_forma,
            "ev_to_ttm_sales": (mcap_diluted - pro_forma) / (f["fy2025_sales"] - f["h1_2025"]["product_net_sales"] + f["h1_2026"]["product_net_sales"])}


def reverse_valuation(inp: dict) -> pd.DataFrame:
    """FY2030E product sales needed for a required annual return to Oct 2030, given an exit P/E.
    Uses base-case margin, tax and financial income. Returns revenue (usd m) and implied CAGR from base FY2026E."""
    rv, f = inp["reverse_valuation"], inp["facts"]
    b = inp["scenarios"]["base"]
    rev26 = project(inp, b)["rev_2026e"]
    n = rv["years"]
    rows = []
    for r in rv["required_annual_returns"]:
        for pe in rv["exit_pes"]:
            eps = f["price_usd"] * (1 + r) ** n / pe
            ni = eps * f["diluted_shares_m"]
            op = ni / (1 - b["tax_rate"]) - b["net_financial_income_usd_m"]
            rev = op / rv["op_margin_2030"]
            rows.append({"required_return": r, "exit_pe": pe, "eps_2030_needed": eps, "rev_2030_needed_usd_m": rev,
                         "implied_rev_cagr_from_2026e": (rev / rev26) ** (1 / (n)) - 1})
    return pd.DataFrame(rows)


def sensitivity(inp: dict) -> pd.DataFrame:
    """12m return vs FY2027E growth and exit P/E, holding base-case 2026 path and margins."""
    price = inp["facts"]["price_usd"]
    b = dict(inp["scenarios"]["base"])
    s = inp["sensitivity"]
    grid = pd.DataFrame(index=pd.Index(s["growth_2027"], name="growth_2027"),
                        columns=pd.Index(s["exit_pe"], name="exit_pe"), dtype=float)
    for g in grid.index:
        for pe in grid.columns:
            p = project(inp, {**b, "growth_2027": g})
            grid.loc[g, pe] = p["eps_2027e"] * pe / price - 1
    return grid
