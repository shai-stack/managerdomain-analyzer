# bot/data_store.py
import io
import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_FILE = Path("latest_report.json")


def _normalize_col(col):
    c = col.strip().lower()
    c = re.sub(r"\s*\((last hour|previous hour)\)\s*$", "", c)
    return c


_COL_MAP = {
    "ssp adapter connection primary seller": "seller",
    "day": "date",
    "ssp adapter advertiser type (internal)": "ad_type",
    "ssp adapter auctions": "auctions",
    "ssp adapter auctions (previous)": "auctions_prev",
    "diff": "auctions_diff",
    "ssp handled auction rate": "auction_rate",
    "ssp adapter publisher net revenue": "revenue",
    "ssp adapter fill rate %": "fill_rate",
    "ssp adapter publisher share (gross)": "pub_share",
    "ssp adapter - gross rpm": "rpm",
    "ssp adapter net cpm": "net_cpm",
    "ssp adapter net income (by auctions fee)": "net_income_auctions",
    "ssp adapter net income (by revshare fee)": "net_income_revshare",
}


def parse_csv(csv_content: str) -> dict:
    df = pd.read_csv(io.StringIO(csv_content), sep=None, engine="python")
    df.columns = [_normalize_col(c) for c in df.columns]
    df = df.rename(columns={k: v for k, v in _COL_MAP.items() if k in df.columns})

    required = {"seller", "date", "revenue"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    # Drop summary/aggregate rows (Average, Filter Total, Total, empty dates)
    df = df[df["date"].notna() & ~df["date"].astype(str).str.strip().isin(["", "Average", "Filter Total", "Total"])]
    # Also drop rows where seller is blank
    df = df[df["seller"].notna() & (df["seller"].astype(str).str.strip() != "")]

    if df.empty:
        raise ValueError("CSV contains no data rows")

    for col in ("revenue", "fill_rate", "pub_share", "rpm", "auction_rate", "net_cpm", "net_income_auctions", "net_income_revshare"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"[$%,]", "", regex=True)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ("auctions", "auctions_prev", "auctions_diff"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "")
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].copy()

    # Group by seller (and ad_type if present)
    group_cols = ["seller", "ad_type"] if "ad_type" in df.columns else ["seller"]
    summary: dict = {}
    for keys, group in df.groupby(group_cols):
        if isinstance(keys, str):
            keys = (keys,)
        seller = keys[0]
        ad_type = keys[1] if len(keys) > 1 else None
        key = f"{seller}|{ad_type}" if ad_type else seller
        revenue_by_date = group.set_index("date")["revenue"].to_dict()
        entry = {
            "seller": seller,
            "total_revenue": round(float(group["revenue"].sum()), 2),
            "revenue_by_date": {str(k): round(float(v), 2) for k, v in revenue_by_date.items()},
        }
        if ad_type:
            entry["ad_type"] = ad_type
        if "fill_rate" in df.columns:
            entry["avg_fill_rate"] = round(float(group["fill_rate"].mean()), 4)
        if "rpm" in df.columns:
            entry["avg_rpm"] = round(float(group["rpm"].mean()), 4)
        summary[key] = entry

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
