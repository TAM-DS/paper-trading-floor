# Paper trading floor

A deterministic cycle, three stdio MCP servers, one in-memory paper book. Research can request a power, gas, or equity action. The quote handler returns a synthetic fixture with a unit and an as-of time. Risk allows or denies. The OMS can write a paper fill. It cannot write a street fill.

## MCP servers and tools

- `market`: `get_curve`, `get_quote`
- `risk`: `check_limit`
- `oms`: `submit_paper_order`

`place_venue_order` is not exposed by any MCP server. Protocol tests call it and verify an MCP error on all three servers. The local fixture handlers also deny it.

## What a cycle proves

An in-limit ERCOT Houston hub intent receives a paper fill and a rejected venue attempt. An over-limit Henry Hub intent stops at risk. A paper fill has `venue: null`.

[servers.py](src/floor/servers.py) wraps the local fixture handlers with the official Python MCP SDK (pinned to 1.30.0). Each server runs in a separate stdio subprocess with MCP initialization, tool discovery, input schemas, and tool calls. [client.py](src/floor/client.py) runs a fixture cycle through all three actual MCP sessions. The original `run_cycle()` remains a local deterministic unit-test path; no live model orchestration is claimed. The OMS independently rechecks the symbol/book pairing, positive finite notional, fixture as-of date, and limit; a caller-supplied risk flag is not authority.

## What it does not do

- No broker, no TT, no ICE, no OMS outside this process.
- Fixtures are not live ERCOT or Henry Hub prices.
- A paper fill is not a P&L claim.
- No human approval workflow, authenticated identity, durable book, replay protection, or production risk control.
- The date and limits belong to a fixed scenario, not current market conditions.

## Run

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m floor.client
```

Related: [capital-markets-research-desk](https://github.com/TAM-DS/capital-markets-research-desk) produces the memo. [investment-gems](https://github.com/TAM-DS/investment-gems) produces a watchlist. Neither is an order on this floor.

## Dashboard

Open [docs/index.html](docs/index.html). It shows the same fixture decisions as the tests. It is not a live market feed.

## Start a server from an MCP host

After installation, each MCP host launches one of these stdio commands:

```bash
python -m floor.servers market
python -m floor.servers risk
python -m floor.servers oms
```

These wait for an MCP client on stdin; they are not interactive terminals or HTTP feeds.

## Verified scope

On October 7, 2026, 15 tests passed, including two protocol integration tests. Three separate processes completed MCP initialization and tool discovery. The client called the fixture curve, risk check, and paper submission over stdio, and verified venue-tool rejection. The OMS independently rejected an over-limit protocol submission.

- [Captured MCP fixture result](docs/mcp-proof.json)
- [Protocol tests](tests/test_protocol.py)
- [Dashboard file](docs/index.html) — static fixture view, not live market data or a running frontend.

The paper book is process-local and resets when the OMS process exits. A protocol transport does not establish customer-production readiness, authenticated human approval, or a live trading system.
