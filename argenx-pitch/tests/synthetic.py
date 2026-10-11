"""SYNTHETIC data for unit tests ONLY. Random numbers with no relation to argenx, XBI, or any real price."""
import numpy as np
import pandas as pd


def make_returns(n: int = 700, seed: int = 0, beta: float = 1.1, start: str = "2023-01-02") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n)
    bench = rng.normal(0.0004, 0.012, n)
    stock = 0.0002 + beta * bench + rng.normal(0, 0.015, n)
    return pd.DataFrame({"stock": stock, "benchmark": bench}, index=idx)
