"""Three real stdio MCP servers over bounded synthetic paper tools."""

import argparse

from mcp.server.fastmcp import FastMCP

from floor.mcp import market_call, oms_call, risk_call

market = FastMCP("paper-market-fixtures")
risk = FastMCP("paper-risk-fixtures")
oms = FastMCP("paper-oms")


@market.tool()
def get_curve(symbol: str) -> dict:
    """Return a synthetic energy curve fixture with units and scenario date."""
    return market_call("get_curve", {"symbol": symbol})


@market.tool()
def get_quote(symbol: str) -> dict:
    """Return a synthetic equity quote fixture; this is not a live feed."""
    return market_call("get_quote", {"symbol": symbol})


@risk.tool()
def check_limit(book: str, notional: float, as_of: str) -> dict:
    """Check positive finite notional, book limit, and fixed fixture date."""
    return risk_call("check_limit", {"book": book, "notional": notional, "as_of": as_of})


@oms.tool()
def submit_paper_order(book: str, symbol: str, notional: float) -> dict:
    """Recheck fixture risk and append an in-memory paper fill; no venue path."""
    return oms_call("submit_paper_order", {"book": book, "symbol": symbol, "notional": notional})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", choices=("market", "risk", "oms"))
    args = parser.parse_args()
    {"market": market, "risk": risk, "oms": oms}[args.server].run(transport="stdio")


if __name__ == "__main__":
    main()
