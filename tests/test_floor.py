from floor import run_cycle
from floor.mcp import call_tool


def test_power_intent_gets_a_paper_fill_and_cannot_reach_a_venue():
    result = run_cycle({"book": "ercot-power", "symbol": "ERCOT.HB_HOUSTON", "notional": 25})
    assert result["status"] == "paper-filled"
    assert result["street_fill"] is False
    assert result["venue_attempt"]["error"] == "no-venue-path"
    assert result["fill"]["venue"] is None
    assert result["quote"]["unit"] == "USD/MWh"


def test_over_limit_gas_intent_is_rejected():
    result = run_cycle({"book": "us-gas", "symbol": "GAS.HENRY", "notional": 80})
    assert result["status"] == "rejected"
    assert result["stage"] == "risk"


def test_unknown_market_tool_is_denied():
    denied = call_tool("market", "place_venue_order", {"symbol": "NGRD"})
    assert denied["error"] == "tool-not-exposed"


def test_equity_paper_fill_stays_inside_the_oms():
    result = run_cycle({"book": "us-equities", "symbol": "NGRD", "notional": 40})
    assert result["status"] == "paper-filled"
    assert result["fill"]["book"] == "us-equities"
