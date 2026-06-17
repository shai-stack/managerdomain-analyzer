# tests/test_data_store.py
import pytest
from pathlib import Path
from bot.data_store import parse_csv, save, load

SAMPLE_CSV = (
    "SSP Adapter Connection Primary Seller,Day,"
    "SSP Adapter Advertiser Type (Internal),SSP Adapter Auctions,"
    "SSP Adapter Auctions (Previous),Diff,SSP Handled Auction Rate,"
    "SSP Adapter Publisher Net Revenue,SSP Adapter Fill Rate %,"
    "SSP Adapter Publisher Share (Gross),SSP Adapter - Gross RPM\n"
    'Yahoo,2026-06-16,web_display,"81,266,000","106,053,000","-24,787,000",'
    '76.77%,$512.23,0.75%,95.00%,$0.0075\n'
    'Publift,2026-06-16,web_display,"22,278,000","19,824,000","2,454,000",'
    '89.38%,$133.67,1.19%,82.27%,$0.0080\n'
    'Yahoo,2026-06-15,web_display,"90,000,000","85,000,000","5,000,000",'
    '80.00%,$480.00,0.80%,95.00%,$0.0070\n'
)


def test_parse_csv_latest_date():
    result = parse_csv(SAMPLE_CSV)
    assert result["latest_date"] == "2026-06-16"


def test_parse_csv_latest_day_has_two_rows():
    result = parse_csv(SAMPLE_CSV)
    assert len(result["latest_day"]) == 2


def test_parse_csv_revenue_is_float():
    result = parse_csv(SAMPLE_CSV)
    yahoo = next(r for r in result["latest_day"] if r["seller"] == "Yahoo")
    assert yahoo["revenue"] == pytest.approx(512.23)


def test_parse_csv_auctions_are_int():
    result = parse_csv(SAMPLE_CSV)
    yahoo = next(r for r in result["latest_day"] if r["seller"] == "Yahoo")
    assert yahoo["auctions"] == 81266000


def test_parse_csv_thirty_day_summary_keys():
    result = parse_csv(SAMPLE_CSV)
    assert "Yahoo|web_display" in result["thirty_day_summary"]


def test_parse_csv_thirty_day_total_revenue():
    result = parse_csv(SAMPLE_CSV)
    total = result["thirty_day_summary"]["Yahoo|web_display"]["total_revenue"]
    assert total == pytest.approx(992.23)


def test_save_and_load(tmp_path, monkeypatch):
    import bot.data_store as ds
    monkeypatch.setattr(ds, "DATA_FILE", tmp_path / "report.json")
    data = {"latest_date": "2026-06-16", "latest_day": [], "thirty_day_summary": {}}
    save(data)
    loaded = load()
    assert loaded["latest_date"] == "2026-06-16"


def test_load_returns_none_when_missing(tmp_path, monkeypatch):
    import bot.data_store as ds
    monkeypatch.setattr(ds, "DATA_FILE", tmp_path / "missing.json")
    assert load() is None


def test_parse_csv_raises_on_missing_column():
    bad_csv = "Wrong Column,Day\nval,2026-06-16\n"
    with pytest.raises(ValueError, match="missing required columns"):
        parse_csv(bad_csv)


def test_parse_csv_raises_on_empty_data():
    empty_csv = (
        "SSP Adapter Connection Primary Seller,Day,"
        "SSP Adapter Advertiser Type (Internal),SSP Adapter Auctions,"
        "SSP Adapter Auctions (Previous),Diff,SSP Handled Auction Rate,"
        "SSP Adapter Publisher Net Revenue,SSP Adapter Fill Rate %,"
        "SSP Adapter Publisher Share (Gross),SSP Adapter - Gross RPM\n"
    )
    with pytest.raises(ValueError, match="no data rows"):
        parse_csv(empty_csv)
