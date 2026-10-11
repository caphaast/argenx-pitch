import pytest

from src import valuation as v

INP = {  # ILLUSTRATIVE test inputs only - not argenx data
    "facts": {"price_usd": 100.0, "diluted_shares_m": 10.0, "cash_and_current_financial_assets_usd_m": 500,
              "forte_incremental_cash_consideration_est_usd_m": 100, "q2_2026_sales": 100.0, "fy2025_sales": 300.0,
              "eps_diluted_fy2025": 5.0, "h1_2025": {"product_net_sales": 120, "eps_diluted": 2.0},
              "h1_2026": {"product_net_sales": 200.0, "operating_profit": 50, "eps_diluted": 3.0}},
    "scenarios": {"base": {"qoq_h2_2026": 0.10, "op_margin_2026_h2": 0.30, "growth_2027": 0.20, "op_margin_2027": 0.35,
                           "growth_2028": 0.10, "op_margin_2028": 0.40, "tax_rate": 0.20,
                           "net_financial_income_usd_m": 10, "exit_pe": 20}},
    "reverse_valuation": {"years": 2, "required_annual_returns": [0.10], "exit_pes": [20], "op_margin_2030": 0.40},
    "sensitivity": {"growth_2027": [0.20], "exit_pe": [20]},
}


def test_projection_hand_calculation():
    p = v.project(INP, INP["scenarios"]["base"])
    q3, q4 = 110.0, 121.0
    rev26 = 200 + q3 + q4                                   # 431
    assert p["rev_2026e"] == pytest.approx(rev26)
    eps26 = 3.0 + ((0.30 * (q3 + q4) + 5) * 0.8) / 10
    assert p["eps_2026e"] == pytest.approx(eps26)
    rev27 = rev26 * 1.2
    assert p["eps_2027e"] == pytest.approx((0.35 * rev27 + 10) * 0.8 / 10)


def test_scenario_value_and_return():
    t = v.scenario_table(INP).loc["base"]
    assert t["value_12m"] == pytest.approx(t["eps_2027e"] * 20)
    assert t["return_12m"] == pytest.approx(t["value_12m"] / 100 - 1)


def test_trailing_metrics():
    m = v.trailing_metrics(INP)
    assert m["ttm_eps_diluted"] == pytest.approx(5.0 - 2.0 + 3.0)
    assert m["ev_diluted_usd_m_pro_forma"] == pytest.approx(1000 - 400)


def test_reverse_valuation_consistency():
    r = v.reverse_valuation(INP).iloc[0]
    # plug the needed revenue back in: EPS must equal price*(1+r)^n/PE
    b = INP["scenarios"]["base"]
    eps = (r["rev_2030_needed_usd_m"] * 0.40 + b["net_financial_income_usd_m"]) * (1 - b["tax_rate"]) / 10
    assert eps == pytest.approx(100 * 1.1 ** 2 / 20)


def test_sensitivity_matches_scenario_at_same_inputs():
    s = v.sensitivity(INP).loc[0.20, 20]
    assert s == pytest.approx(v.scenario_table(INP).loc["base", "return_12m"])
