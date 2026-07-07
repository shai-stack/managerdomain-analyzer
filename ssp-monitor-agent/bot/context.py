def build_daily_context(data: dict) -> str:
    latest_date = data["latest_date"]
    latest_day = sorted(data["latest_day"], key=lambda r: r.get("revenue", 0), reverse=True)
    summary = data["thirty_day_summary"]

    lines = [f"# SSP Performance Data — Latest: {latest_date}\n"]

    lines.append("## Today's Performance (ranked by revenue)")
    lines.append("")  # blank line for spacing
    lines.append(
        "Seller | Ad Type | Revenue | Fill Rate | RPM | Auction Rate | "
        "Auctions | Auctions Prev | Diff"
    )
    for r in latest_day:
        lines.append(
            f"{r.get('seller', '')} | {r.get('ad_type', '')} | "
            f"${r.get('revenue', 0):.2f} | {r.get('fill_rate', 0):.4f} | "
            f"${r.get('rpm', 0):.4f} | {r.get('auction_rate', 0):.4f} | "
            f"{r.get('auctions', 0):,} | {r.get('auctions_prev', 0):,} | "
            f"{r.get('auctions_diff', 0):,}"
        )

    lines.append("\n## 30-Day Summary (per seller)")
    lines.append("Seller | Ad Type | 30d Total Revenue | Avg Fill Rate | Avg RPM")
    for key, s in sorted(summary.items(), key=lambda x: x[1]["total_revenue"], reverse=True):
        lines.append(
            f"{s['seller']} | {s.get('ad_type', '-')} | ${s['total_revenue']:.2f} | "
            f"{s.get('avg_fill_rate', 0):.4f} | ${s.get('avg_rpm', 0):.4f}"
        )

    lines.append("\n## Daily Revenue Trends (top 30 sellers, last 30 days)")
    top30 = sorted(summary.items(), key=lambda x: x[1]["total_revenue"], reverse=True)[:30]
    for _, s in top30:
        dates = ", ".join(
            f"{d}: ${v}" for d, v in sorted(s["revenue_by_date"].items())
        )
        lines.append(f"{s['seller']} ({s.get('ad_type', '-')}): {dates}")

    return "\n".join(lines)
