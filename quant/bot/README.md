# Prediction Market LLM Trading Bot

A self-improving trading bot for [Polymarket](https://polymarket.com) and [Kalshi](https://kalshi.com) that uses an ensemble of LLMs to forecast binary prediction markets, applying findings from the [Lossfunk paper](../04-lossfunk-paper-analysis.md) on domain-asymmetric forecasting.

**Paper trading by default.** Set `PAPER_MODE=false` in `.env` to go live.

---

## Key Ideas

- **LLMs are domain-asymmetric**: geopolitics accuracy (84%) >> sports (44%). Domain weights adapt automatically.
- **News context helps some domains, hurts others**: disabled for entertainment and technology.
- **Three failure-mode guards** on every news fetch: recency bias, rumor anchoring, definition drift.
- **Shannon entropy as a confidence filter**: only trade when the ensemble is sufficiently certain (low entropy).
- **Four self-improvement axes**: prompt evolution, domain calibration, entropy threshold adaptation, model selection.

---

## Directory Structure

```
bot/
├── run.py                      # Entry point
├── agent.py                    # APScheduler jobs + main forecast pipeline
├── config.py                   # All settings (override via .env)
├── requirements.txt
├── .env.example
│
├── db/
│   ├── schema.sql              # SQLite schema (8 tables)
│   └── store.py                # Async DB layer (aiosqlite)
│
├── exchanges/
│   ├── base.py                 # ExchangeClient ABC
│   ├── polymarket.py           # Polymarket CLOB (py-clob-client)
│   ├── kalshi.py               # Kalshi REST API v2
│   └── scanner.py              # Cross-exchange discovery + dedup
│
├── intelligence/
│   ├── classifier.py           # Map question → domain (6 paper domains)
│   ├── news.py                 # News retrieval + 3 failure-mode guards
│   ├── forecaster.py           # Parallel multi-model LLM forecasting
│   ├── entropy.py              # Shannon entropy from logprobs
│   └── ensemble.py             # Weighted multi-model combination
│
├── trading/
│   ├── edge.py                 # Edge = ensemble_prob − market_price
│   ├── kelly.py                # 25% fractional Kelly, 5% bankroll cap
│   ├── executor.py             # Order placement (paper_mode flag)
│   └── portfolio.py            # Virtual bankroll tracker
│
└── learning/
    ├── tracker.py              # Record outcomes when markets resolve
    ├── domain_calibrator.py    # Per-domain Brier tracking + weight update
    ├── prompt_evolver.py       # A/B prompt experiments; retire losers
    ├── threshold_adapter.py    # Bayesian entropy threshold adaptation
    └── model_selector.py       # Rerank models by 30-day rolling Brier
```

---

## Setup

**1. Install dependencies**

```bash
pip install -r requirements.txt
```

**2. Configure credentials**

```bash
cp .env.example .env
# Edit .env with your API keys
```

At minimum you need one LLM key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`) and one exchange key to fetch live markets. Everything else degrades gracefully.

**3. Initialise the database**

The DB is created automatically on first run at `bot/bot.db`.

---

## Running

```bash
# From quant/ directory:

# Test exchange connections — print 5 sample markets
python3 bot/run.py --dry-run

# Run the full pipeline on 1 market, print forecast + edge
python3 bot/run.py --paper

# Run all jobs once then exit
python3 bot/run.py --once

# Start the full scheduler loop
python3 bot/run.py
```

---

## Scheduler Jobs

| Job | Frequency | What it does |
|-----|-----------|--------------|
| `scan_markets` | Every 4h | Discover markets on both exchanges, dedup cross-listed |
| `update_prices` | Every 30m | Refresh `market_price` for all active markets |
| `check_resolutions` | Every 1h | Poll for resolved markets, compute Brier scores |
| `run_forecasts` | Every 4h | Run full pipeline on unforecasted markets |
| `self_improvement` | Daily 6am | Domain calibration + model reranking + threshold adaptation |
| `prompt_tournament` | Weekly Mon | A/B prompt tournament; retire losers; evolve new variants |
| `load_state` | On start | Restore weights + thresholds from DB |

---

## Forecast Pipeline (per market)

```
1. classifier  → map question to domain
2. news        → fetch articles, apply 3 guards (or skip for entertainment/technology)
3. forecaster  → run all models in parallel (asyncio.gather)
4. entropy     → compute Shannon H per model from logprobs
5. ensemble    → weighted combination (model_weight × domain_weight)
6. edge        → ensemble_prob − market_price
7. [filter]    → edge > 5%, confidence == "high", domain_weight > 0.5, positions < 20
8. kelly       → 25% fractional Kelly, capped at 5% of bankroll
9. executor    → paper log or live order
```

---

## Trading Filters

A trade is placed only when **all** conditions are met:

| Condition | Threshold |
|-----------|-----------|
| Edge | `ensemble_prob − market_price > 0.05` |
| Confidence tier | `"high"` (entropy < per-domain τ) |
| Domain weight | `> 0.5` (not actively losing on this domain) |
| Open positions | `< 20` |
| Position size | `≤ 5% of bankroll` |

---

## Self-Improvement

### Domain Calibration (`domain_calibrator.py`)
Tracks rolling Brier score per `(domain, model)` pair. Updates `domain_weight`:

| Brier | Weight |
|-------|--------|
| < 0.15 | 1.5× (excellent) |
| 0.15–0.20 | 1.2× |
| 0.20–0.25 | 1.0× |
| 0.25–0.28 | 0.7× |
| > 0.28 | 0.3× (alert fired) |

Random baseline Brier = 0.25 (always predict 50%).

### Model Selection (`model_selector.py`)
Computes 30-day rolling Brier per model, normalises to weights summing to 1. Kill switch: Brier > 0.28 → weight = 0.

### Prompt Evolution (`prompt_evolver.py`)
Starts with two variants (`v1-baseline`, `v2-cot`). After 20+ outcomes per variant, runs a tournament. Losers (Brier gap > 0.05 vs best) are retired. An LLM generates replacement variants automatically.

### Entropy Threshold Adaptation (`threshold_adapter.py`)
Bayesian update of the per-domain entropy threshold τ (default 4.0 bits):
- If `P(correct | H < τ) − P(correct | H ≥ τ) > 0.10`: tighten τ by 0.25 bits
- If separation < 0.05: widen τ by 0.25 bits (entropy not useful for this domain)

---

## Database

SQLite at `bot/bot.db`. All access goes through `db/store.py`.

```bash
# Quick inspection:
sqlite3 bot/bot.db "SELECT domain, round(avg(brier),3) as mean_brier, count(*) as n FROM outcomes GROUP BY domain"
sqlite3 bot/bot.db "SELECT * FROM calibration_state ORDER BY brier_score"
sqlite3 bot/bot.db "SELECT * FROM model_weights"
sqlite3 bot/bot.db "SELECT * FROM trades ORDER BY placed_at DESC LIMIT 10"
```

---

## Key Configuration (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PAPER_MODE` | `true` | Paper trading; no real orders |
| `VIRTUAL_BANKROLL` | `10000` | Starting USD for paper trades |
| `MIN_EDGE` | `0.05` | Minimum edge to trade |
| `KELLY_FRACTION` | `0.25` | Fractional Kelly multiplier |
| `MAX_POSITION_PCT` | `0.05` | Max bankroll per position |
| `MAX_OPEN_POSITIONS` | `20` | Max concurrent positions |
| `MIN_VOLUME_USD` | `10000` | Market liquidity filter |
| `MIN_HOURS_TO_CLOSE` | `48` | Ignore markets closing soon |
| `ENTROPY_THRESHOLD_DEFAULT` | `4.0` | Entropy threshold in bits |
| `LEARNING_BATCH_SIZE` | `10` | Outcomes before calibration update |
| `MODEL_KILL_BRIER` | `0.28` | Brier score kill switch |

---

## Models

Default roster (updated dynamically by `model_selector.py`):

| Model | Provider | Logprobs |
|-------|----------|----------|
| `claude-sonnet-4-6` | Anthropic | via API |
| `gpt-4.1` | OpenAI | native |
| `deepseek-chat` | DeepSeek | native |

Domain classification uses `claude-haiku-4-5-20251001` (cheap, fast).

---

## Going Live

1. Set `PAPER_MODE=false` in `.env`
2. Add real exchange credentials (`POLY_PRIVATE_KEY`, `POLY_API_KEY`, `KALSHI_API_KEY`, etc.)
3. Run `--dry-run` to confirm exchange connectivity
4. Start with a small `VIRTUAL_BANKROLL` equivalent and monitor `calibration_state` for the first week
5. Review `SELECT domain, avg(brier) FROM outcomes GROUP BY domain` before trusting any domain

> **Note:** Kalshi requires a real-money funded account. Polymarket requires a Polygon wallet with USDC.
