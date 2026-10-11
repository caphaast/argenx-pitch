"""Fetch argenx-sponsored studies from ClinicalTrials.gov API v2 -> data/raw/clinicaltrials_argenx.csv.
Run:  python -m src.clinicaltrials    (needs internet; public API, no key). Raw JSON is kept alongside."""
from __future__ import annotations

import json

import pandas as pd

from .config import resolve

URL = "https://clinicaltrials.gov/api/v2/studies"


def parse_studies(payload: dict) -> pd.DataFrame:
    rows = []
    for st in payload.get("studies", []):
        p = st.get("protocolSection", {})
        idm, sm, dm, cm = (p.get(k, {}) for k in ("identificationModule", "statusModule", "designModule", "conditionsModule"))
        rows.append({
            "nct_id": idm.get("nctId"), "title": idm.get("briefTitle"),
            "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "status": sm.get("overallStatus"), "start_date": sm.get("startDateStruct", {}).get("date"),
            "primary_completion_date": sm.get("primaryCompletionDateStruct", {}).get("date"),
            "last_update": sm.get("lastUpdatePostDateStruct", {}).get("date"),
            "phases": "|".join(dm.get("phases", [])), "conditions": "|".join(cm.get("conditions", []))})
    return pd.DataFrame(rows)


def fetch(sponsor: str = "argenx", page_size: int = 100) -> tuple[pd.DataFrame, list]:
    import requests

    payloads, token = [], None
    while True:
        params = {"query.spons": sponsor, "pageSize": page_size, "format": "json"}
        if token:
            params["pageToken"] = token
        r = requests.get(URL, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        payloads.append(j)
        token = j.get("nextPageToken")
        if not token:
            break
    df = pd.concat([parse_studies(j) for j in payloads], ignore_index=True)
    return df, payloads


if __name__ == "__main__":
    df, raw = fetch()
    out = resolve("data/raw")
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "clinicaltrials_argenx.csv", index=False)
    (out / "clinicaltrials_argenx.json").write_text(json.dumps(raw))
    print(f"{len(df)} studies saved. Cross-check NCT ids against data/pipeline.csv.")
