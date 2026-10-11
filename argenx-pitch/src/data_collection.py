"""Download/load market data (Yahoo Finance via yfinance). Run: python -m src.data_collection

Three fallbacks (yf.download -> Ticker.history -> Yahoo chart endpoint). Raw data saved untouched with metadata.
Yahoo data: personal/research use; check terms before redistributing.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import pandas as pd

from .config import load_config, resolve

log = logging.getLogger(__name__)


def _safe(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace("/", "_")


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index.name = "Date"
    return df


def _parse_chart_payload(payload: dict) -> pd.DataFrame:
    res = payload["chart"]["result"][0]
    tz = res["meta"].get("exchangeTimezoneName", "UTC")
    ts = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(tz).tz_localize(None).normalize()
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({"Open": q["open"], "High": q["high"], "Low": q["low"], "Close": q["close"]}, index=ts)
    adj = res["indicators"].get("adjclose")
    df["Adj Close"] = adj[0]["adjclose"] if adj else df["Close"]
    df["Volume"] = q["volume"]
    df = df[~df.index.duplicated(keep="last")].dropna(subset=["Close"])
    df.index.name = "Date"
    return df


def _chart_api(ticker: str, start: str, end: str | None) -> pd.DataFrame:
    import requests

    p1 = int(pd.Timestamp(start).timestamp())
    p2 = int((pd.Timestamp(end) if end else pd.Timestamp.now()).timestamp()) + 86400
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                     params={"period1": p1, "period2": p2, "interval": "1d", "events": "div,split"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return _parse_chart_payload(r.json())


def download_ticker(ticker: str, start: str, end: str | None = None) -> pd.DataFrame:
    import yfinance as yf

    errors = []
    try:
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, actions=True, progress=False)
        if df is not None and not df.empty:
            return _clean(df)
        errors.append("yf.download: no rows")
    except Exception as e:  # noqa: BLE001
        errors.append(f"yf.download: {e}")
    try:
        df = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=True)
        if df is not None and not df.empty:
            return _clean(df)
        errors.append("Ticker.history: no rows")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Ticker.history: {e}")
    try:
        df = _chart_api(ticker, start, end)
        if not df.empty:
            return df
        errors.append("chart API: no rows")
    except Exception as e:  # noqa: BLE001
        errors.append(f"chart API: {e}")
    raise RuntimeError(f"No data for {ticker}: {errors}. Try `pip install -U yfinance`, wait (rate limit), or save a Yahoo "
                       "Historical Data CSV to data/raw/ (see data/README.md).")


def collect_all(cfg: dict | None = None) -> list[Path]:
    import yfinance as yf

    cfg = cfg or load_config()
    raw = resolve(cfg["raw_dir"])
    raw.mkdir(parents=True, exist_ok=True)
    out, failed = [], []
    for role, ticker in cfg["tickers"].items():
        try:
            df = download_ticker(ticker, cfg["start_date"], cfg.get("end_date"))
        except RuntimeError as e:
            failed.append(ticker)
            print(f"FAILED {role} {ticker}: {e}")
            continue
        path = raw / f"{_safe(ticker)}.csv"
        df.to_csv(path)
        meta = {"ticker": ticker, "source": "Yahoo Finance", "yfinance_version": getattr(yf, "__version__", "?"),
                "collected_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "rows": len(df), "first_date": str(df.index.min().date()), "last_date": str(df.index.max().date())}
        path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2))
        out.append(path)
        print(f"{role:10s} {ticker:6s} rows={len(df):5d} {df.index.min().date()} -> {df.index.max().date()}")
    if failed:
        raise SystemExit(f"\nCould not download: {failed}. Others were saved.")
    return out


def load_prices(cfg: dict | None = None) -> dict[str, pd.DataFrame]:
    """Frames keyed 'adj', 'close', 'volume'; columns = roles from config (stock, benchmark)."""
    cfg = cfg or load_config()
    raw = resolve(cfg["raw_dir"])
    adj, close, vol = {}, {}, {}
    for role, ticker in cfg["tickers"].items():
        path = raw / f"{_safe(ticker)}.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing. Run: python -m src.data_collection")
        df = pd.read_csv(path, index_col="Date", parse_dates=True)
        adj[role] = df["Adj Close"] if "Adj Close" in df else df["Close"]
        close[role], vol[role] = df["Close"], df["Volume"]
    return {"adj": pd.DataFrame(adj), "close": pd.DataFrame(close), "volume": pd.DataFrame(vol)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collect_all()
