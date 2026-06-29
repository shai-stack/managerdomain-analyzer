from bot.context import build_daily_context

SAMPLE_DATA = {
    "latest_date": "2026-06-16",
    "latest_day": [
        {
            "seller": "Yahoo", "ad_type": "web_display", "revenue": 512.23,
            "fill_rate": 0.0075, "rpm": 0.0075, "auction_rate": 0.7677,
            "auctions": 81266000, "auctions_prev": 106053000, "auctions_diff": -24787000,
        },
        {
            "seller": "Publift", "ad_type": "web_display", "revenue": 133.67,
            "fill_rate": 0.0119, "rpm": 0.0080, "auction_rate": 0.8938,
            "auctions": 22278000, "auctions_prev": 19824000, "auctions_diff": 2454000,
        },
    ],
    "thirty_day_summary": {
        "Yahoo|web_display": {
            "seller": "Yahoo", "ad_type": "web_display",
            "total_revenue": 14500.23, "avg_fill_rate": 0.0075, "avg_rpm": 0.0075,
            "revenue_by_date": {"2026-06-16": 512.23, "2026-06-15": 480.00},
        },
    },
}


def test_contains_latest_date():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "2026-06-16" in ctx


def test_contains_seller_name():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "Yahoo" in ctx


def test_contains_revenue():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "512.23" in ctx


def test_yahoo_before_publift_in_today_section():
    ctx = build_daily_context(SAMPLE_DATA)
    today_section = ctx.split("30-Day Summary")[0]
    assert today_section.index("Yahoo") < today_section.index("Publift")


def test_contains_thirty_day_total():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "14500.23" in ctx


def test_contains_daily_revenue_trend():
    ctx = build_daily_context(SAMPLE_DATA)
    assert "2026-06-15" in ctx
