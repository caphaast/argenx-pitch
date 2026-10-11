import pandas as pd
import pytest

from src import growth as g
from src import pipeline_data as pdta
from src.config import resolve


def _sales():
    return g.load_sales(resolve("data/quarterly_sales.csv"))


def test_official_sales_validate_clean():
    rep = g.validate_sales(_sales())
    assert not rep.has_errors()


def test_growth_arithmetic_matches_hand_calculation():
    t = g.growth_table(_sales())
    assert t.loc["2026Q2", "yoy_pct"] == pytest.approx(1516 / 949 - 1)
    assert t.loc["2026Q2", "qoq_pct"] == pytest.approx(1516 / 1298 - 1)
    assert t.loc["2026Q1", "qoq_pct"] == pytest.approx(1298 / 1285.711 - 1)
    assert t.loc["2025Q4", "ttm_sales"] == pytest.approx(398 * 0 + 790 + 949 + 1126.961 + 1285.711)


def test_fy2025_sum_matches_reported_total():
    s = _sales().set_index("quarter")["product_net_sales_usd_m"]
    fy25 = s[["2025Q1", "2025Q2", "2025Q3", "2025Q4"]].sum()
    assert fy25 == pytest.approx(4151.316, abs=1.0)        # FY2025 reported in the Feb 2026 release


def test_region_sum_check_catches_errors():
    df = _sales().copy()
    df.loc[df["quarter"] == "2025Q2", "us_usd_m"] += 50
    assert any(i.check == "region_sum" for i in g.validate_sales(df).errors)


def test_margin_table():
    m = g.margin_table(_sales())
    assert m.loc["2026Q2", "op_margin_on_product_sales"] == pytest.approx(494 / 1516)


def test_pipeline_table_valid_and_verified_rows_need_primary_source():
    df = pdta.load_pipeline(resolve("data/pipeline.csv"))
    assert not pdta.validate_pipeline(df).has_errors()
    bad = df.copy()
    bad.loc[0, "source_type"] = "secondary"
    assert any(i.check == "verified_needs_primary" for i in pdta.validate_pipeline(bad).errors)


def test_upcoming_catalysts_includes_mmn_q4_2026():
    c = pdta.upcoming_catalysts(pdta.load_pipeline(resolve("data/pipeline.csv")))
    assert ((c["next_catalyst"].str.contains("EMPASSION")) & (c["expected_timing"] == "Q4 2026")).any()
