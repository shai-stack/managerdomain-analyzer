# bot/data_store.py
import io
import json
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_FILE = Path("latest_report.json")

_COL_MAP = {
    "SSP Adapter Connection Primary Seller": "seller",
    "Day": "date",
    "SSP Adapter Advertiser Type (Internal)": "ad_type",
    "SSP Adapter Auctions": "auctions",
    "SSP Adapter Auctions (Previous)": "auctions_prev",
    "Diff": "auctions_diff",
    "SSP Handled Auction Rate": "auction_rate",
    "SSP Adapter Publisher Net Revenue": "revenue",
    "SSP Adapter Fill Rate %": "fill_rate",
    "SSP Adapter Publisher Share (Gross)": "pub_share",
    "SSP Adapter - Gross RPM": "rpm",
}


def parse_csv(csv_content: str) -> dict:
    df = pd.read_csv(io.StringIO(csv_content))
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in _COL_MAP.items() if k in df.columns})

    required = {"seller", "ad_type", "date", "revenue"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    if df.empty:
        raise ValueError("CSV contains no data rows")

    for col in ("revenue", "fill_rate", "pub_share", "rpm", "auction_rate"):
        if col in df.columns:
            df[col] = (
                df[col].astype(str).str.replace(r"[$%,]", "", regex=True)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ("auctions", "auctions_prev", "auctions_diff"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "")
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].copy()

    summary: dict = {}
    for (seller, ad_type), group in df.groupby(["seller", "ad_type"]):
        key = f"{seller}|{ad_type}"
        revenue_by_date = group.set_index("date")["revenue"].to_dict()
        summary[key] = {
            "seller": seller,
            "ad_type": ad_type,
            "total_revenue": round(float(group["revenue"].sum()), 2),
            "avg_fill_rate": round(float(group["fill_rate"].mean()), 4),
            "avg_rpm": round(float(group["rpm"].mean()), 4),
            "revenue_by_date": {str(k): round(float(v), 2) for k, v in revenue_by_date.items()},
        }

    return {
        "latest_date": latest_date,
        "latest_day": latest.to_dict(orient="records"),
        "thirty_day_summary": summary,
    }


def save(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, default=str))


def load() -> Optional[dict]:
    if not DATA_FILE.exists():
        return None
    return json.loads(DATA_FILE.read_text())
