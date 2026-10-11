import pandas as pd

from src.clinicaltrials import parse_studies
from src.data_collection import _parse_chart_payload


def test_parse_chart_payload():     # SYNTHETIC payload shaped like Yahoo's response
    t0 = int(pd.Timestamp("2026-10-07 14:30", tz="UTC").timestamp())
    p = {"chart": {"result": [{"meta": {"exchangeTimezoneName": "America/New_York"}, "timestamp": [t0, t0 + 86400, t0 + 172800],
                               "indicators": {"quote": [{"open": [1, 2, 3], "high": [1, 2, 3], "low": [1, 2, 3],
                                                         "close": [10.0, 11.0, None], "volume": [5, 6, 7]}],
                                              "adjclose": [{"adjclose": [10.0, 11.0, None]}]}}]}}
    df = _parse_chart_payload(p)
    assert list(df.index.strftime("%Y-%m-%d")) == ["2026-10-07", "2026-10-08"]
    assert {"Close", "Adj Close", "Volume"} <= set(df.columns)


def test_parse_clinicaltrials_payload():     # SYNTHETIC payload shaped like the v2 API
    payload = {"studies": [{"protocolSection": {
        "identificationModule": {"nctId": "NCT00000000", "briefTitle": "Test study"},
        "statusModule": {"overallStatus": "TERMINATED", "startDateStruct": {"date": "2025-01"}},
        "designModule": {"phases": ["PHASE3"]}, "conditionsModule": {"conditions": ["A", "B"]},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "argenx"}}}}]}
    df = parse_studies(payload)
    assert df.loc[0, "nct_id"] == "NCT00000000" and df.loc[0, "phases"] == "PHASE3" and df.loc[0, "conditions"] == "A|B"
