# argenx (ARGX) investment research pitch

A reproducible, public-data investment research project prepared as an interview case study. It combines commercial trend analysis, a small event study, pipeline tracking, scenario valuation, and reverse valuation.

**As of:** 9 October 2026  
**Reference price:** $825.03 (Yahoo Finance, secondary market data)  
**Investment conclusion:** **LONG ARGX at $825.03 with a 12-month base target of $1,006 (+22%).** The thesis is that the October pipeline reset lowered expectations while the VYVGART commercial engine remains intact. The next major checkpoint is Q3 2026 results on 22 October.

## What changed after the 8 October clinical updates

- argenx discontinued the Phase 3 UNITY Sjogren's study after an independent monitoring committee concluded the primary endpoint could not be met.
- On the same morning, FB102 met the primary endpoint in Phase 2 celiac disease and argenx said it plans to advance the program into Phase 3.
- Sjogren's contributes **zero explicit revenue** in the revised model.
- Forte is treated as a cash acquisition. The repo distinguishes the ~$2.2bn headline equity value from an estimated incremental cash consideration because argenx already held a stake in Forte.

## Core valuation output

| Scenario | FY2027E sales | FY2027E EPS | Exit P/E | 12m value | Return vs $825.03 |
|---|---:|---:|---:|---:|---:|
| Bear | ~$6.65bn | ~$26.62 | 18x | ~$479 | -41.9% |
| Base | ~$7.77bn | ~$40.23 | 25x | ~$1,006 | +21.9% |
| Bull | ~$8.66bn | ~$48.04 | 30x | ~$1,441 | +74.7% |

The base case assumes **25% FY2027 sales growth, a 38% operating margin, and a 25x exit P/E**. It assigns zero explicit revenue to Sjogren's and no discrete value to FB102 or empasiprubart. The target is therefore a commercial-execution call rather than a pipeline-optionality valuation.

## Repository map

```text
config/        sourced facts + explicit analyst assumptions
data/          compact input datasets and event/pipeline definitions
src/           growth, valuation, event-study and validation code
tests/         unit tests using synthetic data
outputs/       generated tables and figures
analysis/      updated Excel valuation workbook
presentation/  interview pitch deck (.pptx + .pdf)
memo/          investment memo (.docx + .md + .pdf)
docs/          source register and modeling limitations
```

## Reproduce the analysis

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
python run_growth.py
python run_valuation.py
```

The event study can be rerun after collecting prices:

```bash
python -m src.data_collection
python run_events.py
```

## Evidence discipline

Company operating and clinical facts use primary company/SEC sources where available. Market price is a secondary quote and clearly labeled. Facts and analyst assumptions are separated in `config/valuation_inputs.yaml`. See `docs/source_register.csv` and `docs/limitations.md` before using any output.

## Disclaimer

Educational interview project only. This is not investment advice, a solicitation, or a recommendation to transact in any security.
