# Paper Trading Floor · v2

A persistent, long-only historical paper simulator with explicit local human confirmation and independent cash, position, evidence, and replay checks.

## Run in PyCharm or a terminal

Clone this repository, open its folder in PyCharm, and select a Python 3.11–3.13 virtual environment. From the project terminal:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,ai]"
python -m pytest
python -m streamlit run app.py
```

Set `MASSIVE_API_KEY` and, for optional model review, `OPENAI_API_KEY` in your local run configuration environment variables. `CREWAI_MODEL` defaults to `openai/gpt-4.1-mini`; override with an available CrewAI-compatible model. Keys never belong in GitHub or chat. `.env.example` documents variable names; the app automatically loads `.env` from the project folder at startup. File values take precedence over shell values.

## Three explicit data modes

- **demo**: generated synthetic daily bars; needs no keys and proves workflow mechanics only.
- **massive**: retrieves actual split-adjusted daily OHLCV through Massive's REST API. Free Basic is end-of-day, five requests/minute, two years of history. Requests are paced at 12.5 seconds per session; multiple simultaneous processes share the account limit and may receive HTTP 429.
- **cache**: reads a previously fetched response for the exact ticker/date range. No silent fallback or claim that cached data is current.

Choose 1–5 US equity/ETF tickers and at least 60 trading sessions. Energy equities/ETFs such as XLE, XOM, and LNG are proxies, not ERCOT power or Henry Hub spot data. Data is checked for finite prices, OHLC consistency, ordered timestamps, date bounds, and sufficient history. Each evidence package carries its source, as-of date, provider request ID when available, and SHA-256 digest.

## Actual CrewAI execution

The optional review creates a sequential Crew with three Agents and three Tasks, then calls `kickoff()`: market researcher → skeptical risk reviewer → evidence editor. The final output uses a Pydantic schema. Structured metric values and highest/lowest rankings are checked against Python evidence. Unknown IDs, incorrect values/rankings, numeric narrative and unsupported total-return wording flag the draft as `CORRECTION_REQUIRED`. Flagged drafts are withheld from the readable brief and retained in an audit expander. Agents receive precomputed metrics, have no external tools, and cannot submit orders. Identifier validation does not prove semantic accuracy; all model text requires human review. Model use incurs provider charges. A failed call accepts no new review.

## Financial interpretation

Returns, 20-session momentum, annualized daily-return volatility, maximum price drawdown, and average daily dollar volume are calculated in Python, never by a model. Historical SMA20 evaluation uses a fixed rule, the final 30% of observations as a chronological holdout, prior-close signals, next-open execution, open-to-open returns, and configurable one-way costs. No optimization is performed. Prices are split-adjusted, not total returns; dividends, financing, market impact, and point-in-time universe selection are not modeled. A positive result is not a forecast or a profitability claim.

## Review boundary and limitations

This is a local portfolio research/simulation application, not customer production. No broker, exchange connection, or real-money execution exists. Reviewer names in the paper app are local audit labels, not authenticated identities. Synthetic demos and static legacy dashboards remain clearly labeled. Live Massive and model calls must be verified with locally configured credentials; offline tests do not establish provider connectivity. Check provider licensing before redistributing downloaded data.

## Existing evidence

[Legacy fixture scope](docs/legacy-fixture-scope.md) preserves the previous deterministic/protocol implementation and its limitations. Existing tests remain alongside the new market-data tests. The interactive app is `app.py`; `docs/index.html` remains the older static fixture view.

[Massive aggregate API](https://massive.com/docs/rest/stocks/aggregates/custom-bars) · [CrewAI documentation](https://docs.crewai.com/)

## Local launch after configuring .env

```bash
python -m streamlit run app.py
```

The review shows qualitative thesis, challenge, checked observations and uncertainties. Passing structured checks does not establish semantic correctness or authorize a trade.

A failed review receives at most one additional editor correction call with exact validation feedback and Python-calculated signed rankings. Both attempts remain in the audit record. Correction adds model usage; if it fails, the draft remains flagged.

Review correction uses an independent editor and names each offending narrative field and token. Comparative prose (including higher/lower and outperform) remains blocked; market comparisons belong in validated structured claims. A successful check validates structured facts, not investment suitability or the meaning of every sentence.
