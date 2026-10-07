"""Run a fixture cycle through three subprocess MCP sessions, not local dispatch."""

import asyncio
from contextlib import AsyncExitStack
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def server_parameters(name: str) -> StdioServerParameters:
    env = dict(os.environ)
    src = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (src, env.get("PYTHONPATH"))))
    return StdioServerParameters(command=sys.executable, args=["-m", "floor.servers", name], env=env)


async def connect(stack: AsyncExitStack, name: str) -> ClientSession:
    read, write = await stack.enter_async_context(stdio_client(server_parameters(name)))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


def payload(result) -> dict:
    if result.isError:
        raise RuntimeError("MCP tool returned an error")
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def run_protocol_demo() -> dict:
    async with AsyncExitStack() as stack:
        sessions = {name: await connect(stack, name) for name in ("market", "risk", "oms")}
        exposed = {name: [t.name for t in (await session.list_tools()).tools] for name, session in sessions.items()}
        intent = {"book": "ercot-power", "symbol": "ERCOT.HB_HOUSTON", "notional": 25.0}
        quote = payload(await sessions["market"].call_tool("get_curve", {"symbol": intent["symbol"]}))
        risk = payload(await sessions["risk"].call_tool("check_limit", {"book": intent["book"], "notional": intent["notional"], "as_of": quote["as_of"]}))
        if not risk.get("allowed"):
            raise RuntimeError("Fixture risk check rejected the demo intent")
        fill = payload(await sessions["oms"].call_tool("submit_paper_order", intent))
        denied = await sessions["oms"].call_tool("place_venue_order", intent)
        return {"transport": "MCP stdio", "data": "synthetic fixtures", "tools": exposed, "quote": quote, "risk": risk, "fill": fill, "venue_tool_rejected": denied.isError, "street_fill": False}


def main() -> None:
    print(json.dumps(asyncio.run(run_protocol_demo()), indent=2))


if __name__ == "__main__":
    main()
