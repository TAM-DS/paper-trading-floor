"""Local tool-dispatch fixture; no MCP protocol server or transport."""

from __future__ import annotations

from math import isfinite

CURVES = {
    "ERCOT.HB_HOUSTON": {"as_of": "2026-10-07", "value": 46.20, "unit": "USD/MWh"},
    "GAS.HENRY": {"as_of": "2026-10-07", "value": 3.15, "unit": "USD/MMBtu"},
}
QUOTES = {
    "NGRD": {"as_of": "2026-10-07", "value": 18.40, "unit": "USD"},
}
LIMITS = {"ercot-power": 50.0, "us-gas": 20.0, "us-equities": 100.0}
SYMBOL_BOOKS = {"ERCOT.HB_HOUSTON": "ercot-power", "GAS.HENRY": "us-gas", "NGRD": "us-equities"}
PAPER: list[dict] = []


def market_call(name: str, args: dict) -> dict:
    if name == "get_curve":
        row = CURVES.get(args["symbol"])
        if not row:
            return {"ok": False, "error": "unknown-symbol"}
        return {"ok": True, "tool": name, **row, "symbol": args["symbol"]}
    if name == "get_quote":
        row = QUOTES.get(args["symbol"])
        if not row:
            return {"ok": False, "error": "unknown-symbol"}
        return {"ok": True, "tool": name, **row, "symbol": args["symbol"]}
    return {"ok": False, "error": "tool-not-exposed", "tool": name}


def risk_call(name: str, args: dict) -> dict:
    if name != "check_limit":
        return {"ok": False, "error": "tool-not-exposed", "tool": name}
    book = args.get("book")
    cap = LIMITS.get(book)
    try:
        raw = args.get("notional")
        notional = float(raw)
    except (TypeError, ValueError, OverflowError):
        return {"ok": True, "allowed": False, "reason": "invalid-notional"}
    if isinstance(raw, bool) or not isfinite(notional) or notional <= 0:
        return {"ok": True, "allowed": False, "reason": "invalid-notional"}
    if cap is None:
        return {"ok": True, "allowed": False, "reason": "unknown-book"}
    allowed = notional <= cap and args.get("as_of") == "2026-10-07"
    return {"ok": True, "allowed": allowed, "cap": cap, "reason": None if allowed else "limit-or-stale"}


def oms_call(name: str, args: dict) -> dict:
    if name == "place_venue_order":
        return {"ok": False, "error": "no-venue-path", "tool": name}
    if name != "submit_paper_order":
        return {"ok": False, "error": "tool-not-exposed", "tool": name}
    symbol = args.get("symbol")
    book = args.get("book")
    if symbol not in SYMBOL_BOOKS or SYMBOL_BOOKS[symbol] != book:
        return {"ok": False, "error": "symbol-book-mismatch"}
    quote = (QUOTES if book == "us-equities" else CURVES).get(symbol)
    if quote is None:
        return {"ok": False, "error": "unknown-symbol"}
    # Independently check the fixture quote and risk limit. Caller flags confer no authority.
    risk = risk_call("check_limit", {"book": book, "notional": args.get("notional"), "as_of": quote["as_of"]})
    if not risk.get("allowed"):
        return {"ok": False, "error": "risk-not-allowed", "risk": risk}
    fill = {
        "fill_id": f"paper-{len(PAPER) + 1}",
        "book": args["book"],
        "symbol": args["symbol"],
        "notional": args["notional"],
        "venue": None,
    }
    PAPER.append(fill)
    return {"ok": True, "fill": fill}


SERVERS = {"market": market_call, "risk": risk_call, "oms": oms_call}


def call_tool(server: str, name: str, args: dict) -> dict:
    if server not in SERVERS:
        return {"ok": False, "error": "unknown-server"}
    return SERVERS[server](name, args)
