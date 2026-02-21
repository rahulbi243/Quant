-- Markets discovered across exchanges
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,              -- "{exchange}:{market_id}"
    exchange TEXT NOT NULL,           -- "polymarket" | "kalshi"
    question TEXT NOT NULL,
    domain TEXT,                      -- classifier output
    url TEXT,
    market_price REAL,                -- current YES price (0-1)
    volume_usd REAL DEFAULT 0,
    close_time DATETIME,
    resolved INTEGER DEFAULT 0,
    outcome INTEGER,                  -- 1=YES, 0=NO, NULL=unresolved
    dedup_group TEXT,                 -- set to matching market ID when cross-listed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- LLM forecasts for each market
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,     -- for A/B tracking
    raw_probability REAL,
    entropy REAL,
    ensemble_probability REAL,        -- weighted across models
    confidence_tier TEXT,             -- "high" | "medium" | "low"
    reasoning_excerpt TEXT,
    news_used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id)
);

-- Trades (paper or live)
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    forecast_id INTEGER,
    exchange TEXT NOT NULL,
    side TEXT NOT NULL,               -- "YES" | "NO"
    size_units REAL,                  -- contracts or USDC
    price REAL,                       -- fill price
    kelly_fraction REAL,
    edge REAL,
    is_paper INTEGER DEFAULT 1,
    placed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (forecast_id) REFERENCES forecasts(id)
);

-- Outcomes for calibration (populated when market resolves)
CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT NOT NULL,
    forecast_id INTEGER,
    domain TEXT,
    model TEXT,
    prompt_version TEXT,
    predicted_prob REAL,
    actual_outcome INTEGER,
    brier REAL,                       -- (pred - outcome)^2
    resolved_at DATETIME,
    FOREIGN KEY (market_id) REFERENCES markets(id),
    FOREIGN KEY (forecast_id) REFERENCES forecasts(id)
);

-- Self-improvement state: per (domain, model) calibration
CREATE TABLE IF NOT EXISTS calibration_state (
    domain TEXT NOT NULL,
    model TEXT NOT NULL,
    brier_score REAL,
    n_resolved INTEGER DEFAULT 0,
    domain_weight REAL DEFAULT 1.0,   -- multiplier on model weight for this domain
    entropy_threshold REAL,           -- per-domain adaptive threshold (NULL = default)
    updated_at DATETIME,
    PRIMARY KEY (domain, model)
);

-- A/B prompt experiment tracking
CREATE TABLE IF NOT EXISTS prompt_experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_version TEXT NOT NULL UNIQUE,
    domain TEXT,                      -- NULL = applies to all domains
    prompt_template TEXT,             -- full prompt template text
    n_trials INTEGER DEFAULT 0,
    n_wins INTEGER DEFAULT 0,
    mean_brier REAL,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Per-model aggregate weights (updated by model_selector)
CREATE TABLE IF NOT EXISTS model_weights (
    model TEXT PRIMARY KEY,
    weight REAL DEFAULT 1.0,
    rolling_brier REAL,
    n_resolved INTEGER DEFAULT 0,
    updated_at DATETIME
);

-- Virtual portfolio / bankroll state
CREATE TABLE IF NOT EXISTS portfolio_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- singleton row
    cash REAL NOT NULL,
    total_value REAL NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Cost tracking for LLM spend
CREATE TABLE IF NOT EXISTS llm_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    call_type TEXT,                   -- "forecast" | "classify" | "evolve"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_forecasts_market ON forecasts(market_id);
CREATE INDEX IF NOT EXISTS idx_forecasts_created ON forecasts(created_at);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_domain ON outcomes(domain);
CREATE INDEX IF NOT EXISTS idx_outcomes_model ON outcomes(model);
CREATE INDEX IF NOT EXISTS idx_markets_resolved ON markets(resolved);
CREATE INDEX IF NOT EXISTS idx_markets_exchange ON markets(exchange);
