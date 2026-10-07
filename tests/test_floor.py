from floor import run_cycle
from floor.mcp import call_tool
import pytest


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


def test_forged_risk_flag_cannot_bypass_the_oms_limit():
    denied = call_tool("oms", "submit_paper_order", {"book": "us-gas", "symbol": "GAS.HENRY", "notional": 80, "risk_allowed": True})
    assert denied["error"] == "risk-not-allowed"


@pytest.mark.parametrize("notional", [-1, 0, float("nan"), float("inf"), "invalid", True])
def test_invalid_notional_cannot_receive_a_fill(notional):
    denied = call_tool("oms", "submit_paper_order", {"book": "us-gas", "symbol": "GAS.HENRY", "notional": notional, "risk_allowed": True})
    assert denied["error"] == "risk-not-allowed"


def test_symbol_cannot_use_another_books_limit():
    denied = call_tool("oms", "submit_paper_order", {"book": "us-equities", "symbol": "GAS.HENRY", "notional": 40})
    assert denied["error"] == "symbol-book-mismatch"


def test_oms_rechecks_the_authoritative_fixture_date(monkeypatch):
    from floor.mcp import CURVES
    monkeypatch.setitem(CURVES, "GAS.HENRY", {"as_of": "2026-07-01", "value": 3.15, "unit": "USD/MMBtu"})
    denied = call_tool("oms", "submit_paper_order", {"book": "us-gas", "symbol": "GAS.HENRY", "notional": 10, "risk_allowed": True, "as_of": "2026-10-07"})
    assert denied["error"] == "risk-not-allowed"
