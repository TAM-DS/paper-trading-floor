"""Paper floor. Agents may act only through MCP tools that exist."""

from __future__ import annotations

from floor.mcp import call_tool


def run_cycle(intent: dict) -> dict:
    quote = call_tool(
        "market",
        "get_curve" if intent["book"] != "us-equities" else "get_quote",
        {"symbol": intent["symbol"]},
    )
    if not quote.get("ok"):
        return {"status": "rejected", "stage": "market", "detail": quote}
    risk = call_tool(
        "risk",
        "check_limit",
        {"book": intent["book"], "notional": intent["notional"], "as_of": quote["as_of"]},
    )
    if not risk.get("allowed"):
        return {"status": "rejected", "stage": "risk", "detail": risk, "quote": quote}
    venue = call_tool("oms", "place_venue_order", intent)
    fill = call_tool(
        "oms",
        "submit_paper_order",
        {**intent, "risk_allowed": True},
    )
    return {
        "status": "paper-filled" if fill.get("ok") else "rejected",
        "quote": quote,
        "risk": risk,
        "venue_attempt": venue,
        "fill": fill.get("fill"),
        "street_fill": False,
    }
