"""Exercise MCP initialization, discovery, schemas, and calls over actual stdio."""

import asyncio
from contextlib import AsyncExitStack

from floor.client import connect, payload, run_protocol_demo


def test_three_real_mcp_servers_expose_only_their_bounded_tools():
    async def verify():
        async with AsyncExitStack() as stack:
            expected = {"market": {"get_curve", "get_quote"}, "risk": {"check_limit"}, "oms": {"submit_paper_order"}}
            for name, names in expected.items():
                session = await connect(stack, name)
                listing = await session.list_tools()
                assert {tool.name for tool in listing.tools} == names
                assert all(tool.inputSchema["type"] == "object" for tool in listing.tools)
                denied = await session.call_tool("place_venue_order", {})
                assert denied.isError
                if name == "oms":
                    rejected = payload(await session.call_tool("submit_paper_order", {"book": "us-gas", "symbol": "GAS.HENRY", "notional": 80}))
                    assert rejected["error"] == "risk-not-allowed"
    asyncio.run(asyncio.wait_for(verify(), timeout=30))


def test_protocol_cycle_produces_only_a_fixture_paper_fill():
    result = asyncio.run(asyncio.wait_for(run_protocol_demo(), timeout=30))
    assert result["transport"] == "MCP stdio"
    assert result["fill"]["ok"] is True
    assert result["fill"]["fill"]["venue"] is None
    assert result["venue_tool_rejected"] is True
    assert result["street_fill"] is False
