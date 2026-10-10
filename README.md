# Paper Trading Floor

A persistent historical paper simulator that separates AI research from human confirmation and checks the account before recording a simulated fill.

**Historical evidence · Bounded AI research · Human authority**

## The decision this supports

Can a proposed historical paper transaction be recorded only after explicit local confirmation and independent account checks?

The floor provides a concrete authority boundary: agents receive research metrics and have no order tool. A person prepares a ticket, supplies a reviewer label, and explicitly confirms the historical simulation. The ledger then checks evidence, cash, positions, and ticket uniqueness before recording a fill.

The business purpose is to demonstrate how research capability can coexist with a constrained transaction workflow and an inspectable record.

## Paper-account rules

| Control | Behavior |
|---|---|
| Starting cash | $100,000 in simulated funds |
| Position model | Long-only; selling more than held is rejected |
| Symbol limit | $20,000 at the selected historical mark for a proposed buy |
| Fill price | Selected dataset’s last historical close |
| Fee | 10 basis points of transaction notional |
| Confirmation | Nonempty local reviewer label and explicit approval |
| Evidence | OHLCV validation, recomputed digest, and ticket-to-evidence match |
| Replay protection | Unique ticket ID; duplicate submission rejected |
| Persistence | SQLite fill ledger; cash and positions reconstructed from records |
| Transaction handling | Account checks and insertion inside an immediate database transaction |

The reviewer label is **not an authenticated identity**. This is a local demonstration, not a production approval service. The database is not an immutable or cryptographically signed audit store. Historical fills do not model current liquidity, bid/ask spread, order queues, or market impact.

## Demonstration evidence

A local Massive run loaded **167 XLE daily bars** through **October 9, 2026**. The optional CrewAI review reached `HUMAN_REVIEW_REQUIRED`. A recorded historical paper buy on **October 10** showed:

| Observation | Recorded result |
|---|---:|
| Quantity | 10 XLE shares |
| Historical price | $65.08 |
| Simulated fee | $0.6508 |
| Remaining cash | $99,348.55, rounded for display |
| Position | 10 XLE shares |

The fill row included a ticket ID, evidence digest, reviewer label, and timestamp. A browser refresh preserved the same fill, position, and cash. This establishes the demonstrated local recording and persistence flow; automated tests separately exercise rejected submissions.

## Try the paper workflow

1. Load evidence and inspect the historical source/date.
2. Choose a side and quantity, then **Prepare paper ticket**.
3. Supply a local reviewer label and explicitly approve the historical simulation.
4. Select **Record historical paper fill**.
5. Inspect the ledger, cash, and position; refresh to check persistence.

Preparing a ticket does not record a fill. The paper workflow is independent of the optional AI review: a passing AI brief never supplies transaction authorization.

## Architecture and evidence boundary

| Layer | Responsibility | Evidence to inspect |
|---|---|---|
| Streamlit | User-selected symbols, dates, and workflow controls | [Application](app.py) |
| Market data | Provider response validation, explicit cache, and Python analytics | [Market module](src/floor/market.py) |
| CrewAI | Bounded research and skeptical interpretation | [Crew and validator](src/floor/crew.py) |
| Review surface | Accepted structured observations or a withheld draft with issues | [Review UI](src/floor/review_ui.py) |
| Paper ledger | Independent account checks and durable simulated fills | [Paper book](src/floor/book.py) |
| Verification | Offline numerical, boundary, and dashboard checks | [Tests](tests/) |

**Capability is not authority.** Model output never grants permission to trade. There is no broker connection, exchange integration, or real-money execution path.

## CrewAI: execution, checks, and correction

The optional review constructs three actual agents and tasks, then calls `Crew.kickoff()` in sequence: **market researcher → skeptical risk reviewer → evidence editor**. Agents receive calculated evidence, have no external tools, and cannot delegate or submit orders.

The final Pydantic output contains a thesis, counterargument, evidence citations, uncertainties, and structured metric claims. Python checks citation membership, numeric values, and highest/lowest rankings against the loaded evidence. Drawdown is signed: the most negative value is the deepest loss. Rankings are only relative to the selected universe; they have little meaning for a single security.

| Review status | Meaning |
|---|---|
| `CORRECTION_REQUIRED` | Draft failed checks; the readable accepted brief is withheld |
| `HUMAN_REVIEW_REQUIRED` | Structured checks passed; interpretation still needs human judgment |
| Call/schema failure | No new review is accepted |

A failed draft gets at most one additional correction kickoff with an independent editor and field-specific feedback. Both attempts remain in the displayed audit. CrewAI may make multiple model requests within each kickoff; the correction therefore adds API usage. The audit reports usage per attempt.

Narrative wording checks reject numeric/comparative prose and unsupported total-return wording, with narrowly approved missing-data disclosures. **These are limited rules, not a semantic proof.** Qualitative claims such as “elevated volatility” can still lack a reference baseline. A valid schema, matching digest, or passed metric check does not establish that every sentence is accurate or useful. Human review remains required.

## Data modes and financial meaning

| Mode | Source | What it establishes |
|---|---|---|
| `demo` | Generated synthetic daily bars | Workflow mechanics without credentials |
| `massive` | Massive split-adjusted historical daily OHLCV | Provider-backed end-of-day evidence |
| `cache` | Saved response for the exact ticker/date range | Explicit reuse of previously loaded evidence |

The application uses an end-of-day research feed. It checks finite prices, OHLC consistency, timestamp order, date bounds, and sufficient history. Each exported dataset includes provenance, an as-of date, a provider request ID when available, and a SHA-256 digest. A digest helps identify/check the supplied rows; it does not authenticate the provider or prove their economic correctness.

Price returns exclude dividends. Momentum uses twenty trading sessions; annualized volatility uses sample daily-return standard deviation and a trading-year convention. Dollar volume is a historical close-times-volume estimate. XLE, XOM, and LNG are equity/ETF energy proxies—not ERCOT power prices, Henry Hub spot prices, or direct Texas-market evidence. No filings, news, valuation, or fundamental data are supplied to the crew.

Requests are paced at 12.5 seconds per session for the configured Basic-tier assumptions. Other running applications share the account’s provider limits. Errors are displayed; the app does not silently substitute demo data for a failed provider request. Consult provider terms before redistributing downloaded data.

## Run locally in PyCharm or a terminal

Use a project virtual environment; avoid installing into Homebrew’s system Python. Python 3.11–3.13 is the project setup range. From the repository folder on macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,ai]"
python -m pytest -q
python -m streamlit run app.py --server.port 8503
```

Open **http://localhost:8503**. In PyCharm, select this project’s `.venv` interpreter. The `ai` extra installs CrewAI; use `.[dev]` if you only need deterministic research and the dashboard.

Copy [.env.example](.env.example) to a local `.env` and enter your credentials there:

```dotenv
MASSIVE_API_KEY=your_local_massive_key
OPENAI_API_KEY=your_local_openai_key
CREWAI_MODEL=openai/gpt-4.1-mini
```

Massive needs its key for provider data; OpenAI is only needed for the optional model review. The app loads the project-root `.env` automatically at startup, with file values taking precedence over shell values. Restart after changing credentials. Keep `.env` local; never commit or include keys in screenshots.

Select one to five tickers and a range with at least sixty trading sessions. Load evidence, inspect the source and dates, then optionally run CrewAI once. Switching/reloading evidence clears the prior AI brief. Model access and API charges depend on the configured provider account.

## Verification and scope

**Latest local verification: 51 tests passed on October 10, 2026.** Tests cover market validation and analytics, structured claim checks, bounded correction, dashboard rendering, and retained fixture behavior. AI orchestration tests construct CrewAI objects with model calls mocked; they do not contact providers. The demonstration observations above come from separate locally credentialed runs inspected through the application screenshots.

The interactive application is [app.py](app.py). The older [static dashboard](docs/index.html) is a fixture view, and [legacy fixture scope](docs/legacy-fixture-scope.md) preserves its original implementation and limitations. This project is portfolio evidence of a local research/simulation system; it is not customer production or proof of profitable execution.

## Related projects

| Project | Distinct purpose |
|---|---|
| [Investment Gems](https://github.com/TAM-DS/investment-gems) | Transparent shortlist screening |
| [Capital Markets Research Desk](https://github.com/TAM-DS/capital-markets-research-desk) | Research challenge and historical strategy evaluation |
| [Paper Trading Floor](https://github.com/TAM-DS/paper-trading-floor) | Explicit local confirmation and persistent simulated fills |

[Massive aggregate API](https://massive.com/docs/rest/stocks/aggregates/custom-bars) · [CrewAI documentation](https://docs.crewai.com/)
