# Data

| File | Content | Source |
|---|---|---|
| `quarterly_sales.csv` | Quarterly VYVGART product net sales, regions (to Q3 2025), operating profit | argenx releases / SEC 6-K (URLs in file) |
| `pipeline.csv` | Indications, stage, results, catalysts | argenx releases; secondary rows flagged `verified=false` |
| `events.csv` | Verified announcements with exact timestamps | argenx releases (07:00 CET) |
| `raw/` | Prices (git-ignored): `ARGX.csv`, `XBI.csv` | `python -m src.data_collection` |

Manual price fallback: download Historical Data (Max, Daily) from Yahoo Finance for ARGX and XBI, save as `data/raw/ARGX.csv`, `data/raw/XBI.csv`
(columns Date, Open, High, Low, Close, Adj Close, Volume).

Add events only after checking date/time in the original release. Keep `confounders` honest (same-day earnings, other trials, market moves).
