# Paper trading floor

Four seats, three MCP servers, one paper book. Research can request a power, gas, or equity action. Market data returns a fixture with a unit and an as-of time. Risk allows or denies. The OMS can write a paper fill. It cannot write a street fill.

## MCP servers

- `market`: `get_curve`, `get_quote`
- `risk`: `check_limit`
- `oms`: `submit_paper_order`

`place_venue_order` is denied on every server. That denial is a test, not a comment.

## What a cycle proves

An in-limit ERCOT Houston hub intent receives a paper fill and a rejected venue attempt. An over-limit Henry Hub intent stops at risk. A paper fill has `venue: null`.

## What it does not do

- No broker, no TT, no ICE, no OMS outside this process.
- Fixtures are not live ERCOT or Henry Hub prices.
- A paper fill is not a P&L claim.

## Run

```bash
python -m pytest
```

Related: [capital-markets-research-desk](https://github.com/TAM-DS/capital-markets-research-desk) produces the memo. [investment-gems](https://github.com/TAM-DS/investment-gems) produces a watchlist. Neither is an order on this floor.

## Dashboard

Open [docs/index.html](docs/index.html). It shows the same fixture decisions as the tests. It is not a live market feed.
