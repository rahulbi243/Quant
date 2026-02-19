# EXECUTION PLAN: Entropy-Guided Time-Series Momentum Forecasting

> **Project Title:** "Think Before You Trade: Sequence-Level Entropy as a
> Confidence Filter for LLM Momentum Forecasting"
>
> **Duration:** 10 days (Feb 20 - Mar 1, 2026)
> **Extends:** Lossfunk's "Think Just Enough" (NeurIPS 2025) +
>              "Future Is Unevenly Distributed" (AAAI 2026)

---

## THE RESEARCH QUESTION

> When LLMs forecast the direction of financial momentum signals, does the
> sequence-level entropy of their reasoning trace predict forecast reliability?
> Can we use entropy as a confidence filter to build a BETTER momentum strategy
> than classical TSMOM?

---

## TECHNICAL CONSTRAINTS (Discovered During Research)

These constraints SHAPE the methodology — they're not problems, they're design inputs:

```
┌─────────────────────────────────────────────────────────────────────┐
│ LOGPROBS AVAILABILITY BY MODEL                                      │
│                                                                     │
│ Model              Logprobs?   Reasoning Trace?   Use In Study      │
│ ─────────────      ─────────   ────────────────   ──────────────    │
│ GPT-4.1            YES ✓       No                 Standard baseline │
│ o3                 YES ✓*      Summary only       Reasoning model   │
│ o4-mini            YES ✓*      Summary only       Reasoning (cheap) │
│ Claude 3.7 Sonnet  YES ✓       No                 Standard baseline │
│ Claude 3.7 Think   YES ✓       Yes (thinking)     Reasoning model   │
│ DeepSeek-V3        YES ✓       No                 Standard baseline │
│ DeepSeek-R1        NO ✗        Yes (<think> tags)  Reasoning model   │
│ Gemini 2.5 Pro     YES ✓       Yes (thinking)     Reasoning model   │
│                                                                     │
│ * o3/o4-mini: logprobs on OUTPUT only, reasoning tokens encrypted   │
│                                                                     │
│ IMPLICATION: For DeepSeek-R1, we use PROXY entropy measures:        │
│ • Linguistic hedging frequency ("maybe", "however", "uncertain")    │
│ • Reasoning chain length (tokens in <think> block)                  │
│ • Self-contradiction count                                          │
│ • This itself becomes a research contribution — do proxy measures   │
│   correlate with true logprob entropy?                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## DATA SOURCES

```
┌─────────────────────────────────────────────────────────────────────┐
│ SOURCE 1: AQR TSMOM Factor Data (PRIMARY)                           │
│                                                                     │
│ URL:  aqr.com/Insights/Datasets/Time-Series-Momentum-Factors-Monthly│
│ Format: Excel (.xlsx)                                               │
│ Range: Jan 1985 — Jan 2025 (updated monthly)                        │
│ Contents: Monthly excess returns for TSMOM factors across:          │
│   • 24 commodity futures                                            │
│   • 12 currency cross-pairs                                         │
│   • 9 equity index futures                                          │
│   • 13 government bond futures                                      │
│ Signal: Long if 12-month excess return > 0, Short otherwise         │
│ Cost: FREE                                                          │
│                                                                     │
│ SOURCE 2: Yahoo Finance / yfinance (SUPPLEMENTARY)                  │
│                                                                     │
│ Use for: Raw price data for individual instruments to construct     │
│          the actual return series LLMs will see as input            │
│ Instruments: ETFs tracking the 4 asset classes                      │
│   • SPY, EWJ, EWG, EFA (equity indices)                            │
│   • GLD, USO, DBA (commodities)                                    │
│   • TLT, IEF, SHY (bonds)                                          │
│   • FXE, FXY, FXB (currencies)                                     │
│ Range: 2010-2025 (sufficient for 12-month lookback + test period)   │
│ Cost: FREE                                                          │
│                                                                     │
│ SOURCE 3: GitHub TSMOM Replication (REFERENCE)                      │
│                                                                     │
│ URL: github.com/rkohli3/TSMOM                                      │
│ Use for: Validated baseline code to compare against                 │
│ Contains: tsmom.py, TSMOM_replicateETF.ipynb                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## EXPERIMENT DESIGN

### Phase 1: Classical TSMOM Baseline

Replicate the standard strategy as ground truth:

```
For each instrument i, each month t:
  signal_i,t = sign(cumulative_return_i,t-12 to t-1)
  position_i,t = signal_i,t / volatility_i,t    (inverse-vol weighting)

Portfolio return = (1/N) × Σ position_i,t × return_i,t+1
```

### Phase 2: LLM Momentum Forecasting

Feed each model a structured prompt with raw data:

```
PROMPT TEMPLATE:
─────────────────────────────────────────────────────
You are a quantitative analyst. Given the following monthly returns
for [INSTRUMENT] over the past 12 months:

Month 1: +2.3%
Month 2: -1.1%
Month 3: +0.8%
...
Month 12: +1.5%

Cumulative 12-month return: +14.2%
Recent 3-month return: +4.1%
Annualized volatility: 18.3%

Task: Predict the DIRECTION of next month's return.
Provide:
1. Your probability estimate (0-100%) that next month is POSITIVE
2. Your reasoning

Respond with ONLY a JSON object:
{"probability": <0-100>, "direction": "long" or "short"}
─────────────────────────────────────────────────────
```

### Phase 3: Entropy Extraction

For each model response, compute:

```
ENTROPY COMPUTATION (matching Lossfunk's "Think Just Enough"):
──────────────────────────────────────────────────────────────

Step 1: Extract top-20 logprobs per output token
        → API param: logprobs=true, top_logprobs=20

Step 2: Convert to probabilities
        p_i = exp(logprob_i) / Σ exp(logprob_j)  for j in top-20

Step 3: Compute per-token Shannon entropy
        H_t = -Σ p_i × log₂(p_i)  for i in 1..20

Step 4: Compute sequence-level mean entropy
        H_mean = (1/T) × Σ H_t  for t in 1..T

Step 5: For DeepSeek-R1 (no logprobs), compute proxy entropy:
        • hedging_score = count("maybe","however","uncertain",...) / total_words
        • chain_length = token_count(<think> block)
        • contradiction_score = count(self-corrections) / total_sentences
        • proxy_H = weighted_average(hedging, chain_length, contradiction)
```

### Phase 4: Entropy-Filtered Strategy

```
ENTROPY FILTER ALGORITHM:
────────────────────────────────────────

For each instrument i, month t:
  1. Get LLM forecast: prob_i,t, H_i,t (entropy)
  2. Compute entropy threshold τ from training window

  IF H_i,t ≤ τ:     (model is confident)
    position_i,t = LLM_signal × inverse_vol_weight
  ELSE:              (model is uncertain)
    position_i,t = classical_TSMOM_signal × inverse_vol_weight
    (or: position_i,t = 0  ← sit out)

Threshold methods (from Lossfunk's paper):
  τ_1 = mean(H | correct predictions in training window)
  τ_2 = μ_c + σ_c × ln(1 + |d|)   (information-theoretic)
  τ_3 = Bayesian optimal boundary
  τ_4 = Scale-invariant universal
```

### Phase 5: Evaluation

```
METRICS:
────────

Strategy Performance:
  • Annualized return
  • Sharpe ratio
  • Maximum drawdown
  • Calmar ratio (return / max drawdown)
  • Hit rate (% of months with correct direction)

Calibration:
  • Brier score (LLM probability vs actual outcome)
  • ECE (expected calibration error)
  • Calibration curve

Entropy Analysis:
  • Correlation(H_mean, forecast_error)   ← KEY METRIC
  • Entropy discrimination: Cohen's d between correct & incorrect
  • ROC-AUC of entropy as binary classifier for "forecast correct?"

Cost:
  • API cost per forecast
  • Cost-adjusted Sharpe ratio
```

---

## MODEL MATRIX

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EXPERIMENT MATRIX                                  │
│                                                                      │
│  Standard Models (control group — no reasoning):                     │
│  ┌─────────────────────┬─────────────┬──────────┬────────────────┐   │
│  │ Model               │ Logprobs    │ Est.Cost │ Purpose        │   │
│  │                     │             │ /query   │                │   │
│  ├─────────────────────┼─────────────┼──────────┼────────────────┤   │
│  │ GPT-4.1             │ ✓ top-20    │ ~$0.02   │ OpenAI base    │   │
│  │ Claude 3.7 Sonnet   │ ✓ top-20    │ ~$0.02   │ Anthropic base │   │
│  │ DeepSeek-V3         │ ✓ top-20    │ ~$0.005  │ Open-src base  │   │
│  └─────────────────────┴─────────────┴──────────┴────────────────┘   │
│                                                                      │
│  Reasoning Models (experimental group):                              │
│  ┌─────────────────────┬─────────────┬──────────┬────────────────┐   │
│  │ Model               │ Logprobs    │ Est.Cost │ Purpose        │   │
│  │                     │             │ /query   │                │   │
│  ├─────────────────────┼─────────────┼──────────┼────────────────┤   │
│  │ o3                  │ ✓ output    │ ~$0.12   │ OAI reasoning  │   │
│  │ o4-mini             │ ✓ output    │ ~$0.02   │ OAI cheap reas │   │
│  │ Claude 3.7 Think    │ ✓ top-20    │ ~$0.06   │ Anthr reasoning│   │
│  │ DeepSeek-R1         │ ✗ NONE      │ ~$0.01   │ Proxy entropy  │   │
│  │ Gemini 2.5 Pro      │ ✓ top-20    │ ~$0.04   │ Google reason  │   │
│  └─────────────────────┴─────────────┴──────────┴────────────────┘   │
│                                                                      │
│  KEY COMPARISONS:                                                    │
│  GPT-4.1     vs  o3           ← Same family, reasoning effect       │
│  Claude std  vs  Claude think ← Same family, reasoning effect       │
│  DeepSeek-V3 vs  DeepSeek-R1  ← Same family, reasoning effect      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## SCALE

```
Instruments: 15 ETFs across 4 asset classes
Months: 120 test months (2015-2025)
Models: 8
────────────────────────────────
Total forecasts: 15 × 120 × 8 = 14,400

With logprobs extraction → ~14,400 API calls
Average tokens per call: ~300 input + ~200 output = ~500 tokens

Estimated total cost:
  Standard models:  15 × 120 × 3 × $0.015  = ~$81
  Reasoning models: 15 × 120 × 5 × $0.05   = ~$450

  TOTAL: ~$530

  ⚠️  COST REDUCTION OPTIONS:
  • Drop to 8 instruments (2 per asset class): ÷1.9  → ~$280
  • Use 60 test months instead of 120:         ÷2    → ~$265
  • Drop Gemini 2.5 Pro:                       -$72  → ~$193
  • Minimal viable: 8 instruments, 60 months, 6 models → ~$150
```

---

## DAY-BY-DAY PLAN

### ═══════════════════════════════════════════════
### DAY 1 (Feb 20) — READ + SETUP
### ═══════════════════════════════════════════════

**Goal:** Deeply understand both Lossfunk papers. Set up project infra.

```
MORNING (4 hours):
├── Read "Think Just Enough" (arxiv.org/abs/2510.08146)
│   └── Take notes on: entropy formula, threshold methods,
│       calibration finding, which models showed emergent property
├── Read "Future Is Unevenly Distributed" (arxiv.org/abs/2511.18394)
│   └── Take notes on: failure modes, dataset construction, metrics
└── Read companion blog: letters.lossfunk.com/p/your-llm-is-a-confused-oracle

AFTERNOON (4 hours):
├── Initialize GitHub repo (PUBLIC)
│   ├── README.md (project title + one-paragraph description)
│   ├── LICENSE (MIT)
│   ├── .gitignore (Python, .env, data/)
│   ├── requirements.txt (see dependencies below)
│   └── Directory structure (see architecture below)
├── Set up Python environment
│   └── python -m venv venv && pip install -r requirements.txt
├── Get API keys
│   ├── OpenAI (gpt-4.1, o3, o4-mini)
│   ├── Anthropic (claude-3.7-sonnet)
│   ├── DeepSeek (deepseek-chat, deepseek-reasoner)
│   └── Google (gemini-2.5-pro)
└── Create .env.example (template without real keys)

EVENING (2 hours):
├── Read TSMOM reference implementation: github.com/rkohli3/TSMOM
└── Skim AQR dataset to understand format
```

**Deliverables:**
- [ ] Paper notes in `notes/paper_notes.md`
- [ ] Repo initialized with structure
- [ ] API keys working (test each with a hello-world call)

---

### ═══════════════════════════════════════════════
### DAY 2 (Feb 21) — DATA PIPELINE
### ═══════════════════════════════════════════════

**Goal:** Get clean TSMOM data and build classical baseline.

```
MORNING (4 hours):
├── Download AQR TSMOM factor data
│   └── Parse Excel → pandas DataFrame
│   └── Validate: check date range, asset classes, monthly returns
├── Download ETF price data via yfinance
│   ├── Equity:  SPY, EWJ, EWG, EWU, EFA, VGK, EWA, EWH
│   ├── Commodity: GLD, USO, DBA, SLV, DBC
│   ├── Bond: TLT, IEF, SHY, BWX, EMB
│   └── Currency: FXE, FXY, FXB, UUP, FXA
│   (Pick 2-3 most liquid per class → 8-12 final instruments)
├── Compute monthly returns from adjusted close prices
└── Save: data/raw/ and data/processed/

AFTERNOON (4 hours):
├── Implement classical TSMOM strategy
│   ├── 12-month lookback signal
│   ├── Inverse-volatility position sizing (60-day rolling vol)
│   ├── Monthly rebalancing
│   └── src/strategies/classical_tsmom.py
├── Backtest classical TSMOM on ETF data (2015-2025)
│   ├── Compute: annual return, Sharpe, max DD, hit rate
│   └── Compare to AQR factor returns (sanity check)
└── Save baseline results: results/baseline/

EVENING (2 hours):
├── Build data formatting module
│   └── src/data/formatter.py
│   └── Function: format_for_llm(instrument, month)
│       → Returns the 12-month return series + stats as prompt text
└── Verify on 5 example months: does the formatted prompt look right?
```

**Deliverables:**
- [ ] `data/processed/etf_returns.parquet` — clean monthly returns
- [ ] `src/strategies/classical_tsmom.py` — working baseline
- [ ] `results/baseline/classical_tsmom_results.json` — Sharpe, returns, etc.
- [ ] `src/data/formatter.py` — LLM prompt data formatter

---

### ═══════════════════════════════════════════════
### DAY 3 (Feb 22) — EVALUATION HARNESS + ENTROPY
### ═══════════════════════════════════════════════

**Goal:** Build the core evaluation engine with entropy extraction.

```
MORNING (4 hours):
├── Build unified model interface
│   └── src/models/base.py
│       class ModelInterface:
│         def predict(question, logprobs=True) → {
│           prediction: float,    # 0-1 probability
│           direction: str,       # "long" / "short"
│           reasoning: str,       # full reasoning trace
│           logprobs: List[TokenLogprob],  # per-token logprobs
│           tokens_used: int,
│           cost_usd: float,
│           latency_ms: int
│         }
│   └── src/models/openai_models.py    (GPT-4.1, o3, o4-mini)
│   └── src/models/anthropic_models.py (Claude std, Claude thinking)
│   └── src/models/deepseek_models.py  (V3, R1)
│   └── src/models/google_models.py    (Gemini 2.5 Pro)
├── Implement logprobs extraction for each API
│   ├── OpenAI: response.choices[0].logprobs.content[i].top_logprobs
│   ├── Anthropic: logprobs parameter in API call
│   ├── DeepSeek-V3: standard logprobs
│   └── DeepSeek-R1: extract <think> block text (no logprobs)
└── Test each model with 1 sample prediction (verify API works)

AFTERNOON (4 hours):
├── Implement entropy computation
│   └── src/entropy/calculator.py
│       ├── compute_token_entropy(top_logprobs) → float
│       │   H_t = -Σ p_i × log₂(p_i)
│       │   where p_i = softmax(logprob_i) over top-20
│       ├── compute_sequence_entropy(all_token_logprobs) → float
│       │   H_mean = mean(H_t for t in all tokens)
│       ├── compute_proxy_entropy(reasoning_text) → float
│       │   (For DeepSeek-R1: hedging + length + contradictions)
│       └── Tests: verify on known distributions
│           (uniform top-20 → H ≈ 4.32 bits, peaked → H ≈ 0)
├── Implement proxy entropy for DeepSeek-R1
│   └── src/entropy/proxy.py
│       ├── HEDGING_WORDS = ["maybe", "perhaps", "however",
│       │    "uncertain", "not sure", "on the other hand",
│       │    "alternatively", "it's possible", "hard to say"]
│       ├── hedging_score(text) → float (count / total_words)
│       ├── chain_length_score(text) → float (normalized token count)
│       ├── contradiction_score(text) → float
│       │   (detect "but wait", "actually", "I was wrong", etc.)
│       └── proxy_entropy(text) → float (weighted combination)
└── Build prompt templates
    └── src/prompts/momentum_prompts.py
        ├── bare_prompt(instrument_data) → str
        └── analyst_prompt(instrument_data) → str
            (structured: "identify trend, check volatility regime,
             consider macro, estimate probability, give direction")

EVENING (2 hours):
├── Build evaluation orchestrator
│   └── src/evaluate.py
│       def run_experiment(models, instruments, months, prompts):
│         for month in months:
│           for instrument in instruments:
│             for model in models:
│               result = model.predict(format_data(instrument, month))
│               entropy = compute_entropy(result.logprobs)
│               store(result, entropy)
└── Test full pipeline: 1 model × 1 instrument × 2 months
    → Verify: prediction stored, entropy computed, cost logged
```

**Deliverables:**
- [ ] `src/models/` — all model interfaces working
- [ ] `src/entropy/calculator.py` — entropy computation verified
- [ ] `src/entropy/proxy.py` — proxy entropy for R1
- [ ] `src/evaluate.py` — orchestrator working end-to-end
- [ ] Pipeline test passing on 2 sample months

---

### ═══════════════════════════════════════════════
### DAY 4 (Feb 23) — RUN: STANDARD MODELS
### ═══════════════════════════════════════════════

**Goal:** Complete all standard model experiments.

```
FULL DAY:
├── Run GPT-4.1 × all instruments × all months
│   └── ~8-12 instruments × 120 months = 960-1440 calls
│   └── With logprobs, bare prompt
│   └── Estimated time: 2-3 hours (rate limited)
│   └── Estimated cost: ~$20-30
│
├── Run Claude 3.7 Sonnet × all instruments × all months
│   └── Same scale, with logprobs
│   └── Estimated cost: ~$20-30
│
├── Run DeepSeek-V3 × all instruments × all months
│   └── Same scale, with logprobs
│   └── Estimated cost: ~$5-10
│
├── PARALLEL: While API calls run, build analysis scaffolding
│   └── src/analysis/metrics.py
│       ├── compute_sharpe(returns) → float
│       ├── compute_max_drawdown(returns) → float
│       ├── compute_hit_rate(predictions, actuals) → float
│       ├── compute_brier(probabilities, outcomes) → float
│       ├── compute_ece(probabilities, outcomes, n_bins=10) → float
│       └── compute_calibration_curve(probs, outcomes) → (x, y)
│
└── Spot-check: randomly sample 20 predictions
    → Do they look reasonable? Any API errors? Any parsing failures?
```

**Deliverables:**
- [ ] `results/raw/gpt41/` — all predictions + logprobs
- [ ] `results/raw/claude37/` — all predictions + logprobs
- [ ] `results/raw/deepseekv3/` — all predictions + logprobs
- [ ] `src/analysis/metrics.py` — all metrics implemented
- [ ] Cost log updated

---

### ═══════════════════════════════════════════════
### DAY 5 (Feb 24) — RUN: REASONING MODELS
### ═══════════════════════════════════════════════

**Goal:** Complete all reasoning model experiments.

```
FULL DAY (longer — reasoning models are slower + more expensive):

├── Run o3 × all instruments × all months
│   └── With logprobs on output, reasoning_effort="medium"
│   └── Estimated cost: ~$100-150  ← MOST EXPENSIVE
│   └── ⚠️ FALLBACK: If over budget, reduce to 60 months or 6 instruments
│
├── Run o4-mini × all instruments × all months
│   └── With logprobs, reasoning_effort="medium"
│   └── Estimated cost: ~$20-30
│
├── Run Claude 3.7 (extended thinking) × all instruments × all months
│   └── With logprobs
│   └── Estimated cost: ~$50-70
│
├── Run DeepSeek-R1 × all instruments × all months
│   └── NO logprobs — extract <think> text for proxy entropy
│   └── Estimated cost: ~$10-15
│
├── Run Gemini 2.5 Pro × all instruments × all months
│   └── With logprobs
│   └── Estimated cost: ~$40-60
│   └── ⚠️ OPTIONAL: Drop if over budget. Still have 4 reasoning models.
│
└── While running: pre-process Day 4's standard model results
    └── Parse all responses, compute entropies, save to CSV
```

**Deliverables:**
- [ ] `results/raw/o3/` — all predictions + logprobs
- [ ] `results/raw/o4mini/` — all predictions + logprobs
- [ ] `results/raw/claude37think/` — all predictions + logprobs + thinking
- [ ] `results/raw/deepseekr1/` — all predictions + proxy entropy data
- [ ] `results/raw/gemini25/` — all predictions + logprobs (if budget allows)
- [ ] `results/processed/standard_models.csv` — parsed from Day 4
- [ ] Cost log updated (CRITICAL: track spending!)

---

### ═══════════════════════════════════════════════
### DAY 6 (Feb 25) — QUANTITATIVE ANALYSIS
### ═══════════════════════════════════════════════

**Goal:** Compute all metrics. Test all hypotheses. Find the story.

```
MORNING (4 hours):
├── Parse all Day 5 results → unified DataFrame
│   Columns: model, instrument, month, prediction, actual_return,
│            direction_correct, probability, entropy, reasoning_length,
│            tokens_used, cost_usd
│
├── Compute per-model strategy returns
│   └── For each model: construct portfolio using its predictions
│   └── Compare Sharpe ratios: LLM strategies vs classical TSMOM
│
├── Compute calibration metrics per model
│   └── Brier score, ECE, calibration curves
│   └── Compare: standard vs reasoning (same family)
│
└── Build comparison tables:
    Table 1: Performance (Sharpe, Return, MaxDD) by model
    Table 2: Calibration (Brier, ECE) by model
    Table 3: Per-asset-class breakdown

AFTERNOON (4 hours):
├── ENTROPY ANALYSIS (the core contribution)
│   ├── Correlation: entropy vs forecast error (per model)
│   │   → Scatter plot: H_mean vs |predicted - actual|
│   │   → Spearman correlation + p-value
│   │
│   ├── Entropy discrimination (matching Lossfunk's approach)
│   │   → Separate correct vs incorrect predictions
│   │   → Compute Cohen's d for entropy distributions
│   │   → KEY: d > 0.5 = entropy is a useful confidence signal
│   │
│   ├── Entropy-filtered strategy backtest
│   │   → For each threshold method (τ_1 through τ_4):
│   │     • Filter: only trade when H ≤ τ
│   │     • Compute: Sharpe of filtered vs unfiltered strategy
│   │     • Compute: what % of trades are filtered out?
│   │
│   └── ROC curve: entropy as classifier for "correct prediction?"
│       → AUC > 0.6 = entropy has predictive value
│
├── Proxy entropy validation (DeepSeek-R1)
│   └── For models WITH logprobs: also compute proxy entropy
│   └── Correlate proxy vs true entropy
│   └── Does proxy entropy also discriminate correct/incorrect?
│
└── Statistical tests
    ├── Paired Wilcoxon: standard vs reasoning Brier scores
    ├── Bootstrap 95% CIs for all Sharpe ratio differences
    └── Bonferroni correction for multiple comparisons

EVENING (2 hours):
└── Write up hypothesis test results
    └── analysis/hypothesis_results.md
    H1: Reasoning improves calibration more than accuracy    → RESULT
    H2: Reasoning helps most in weakest asset classes       → RESULT
    H3: Low-entropy predictions are more accurate           → RESULT
    H4: Entropy-filtered strategy beats unfiltered          → RESULT
    H5: Reasoning models show stronger entropy discrimination→ RESULT
```

**Deliverables:**
- [ ] `results/processed/all_models.csv` — unified results
- [ ] `analysis/metrics_summary.csv` — all computed metrics
- [ ] `analysis/entropy_analysis.csv` — entropy correlations
- [ ] `analysis/hypothesis_results.md` — H1-H5 test results
- [ ] Preliminary story identified: what's the headline?

---

### ═══════════════════════════════════════════════
### DAY 7 (Feb 26) — VISUALIZATIONS + CASE STUDIES
### ═══════════════════════════════════════════════

**Goal:** Generate all figures. Document compelling examples.

```
MORNING (4 hours):
├── Generate core figures:
│
│   Figure 1: STRATEGY COMPARISON
│   ┌─────────────────────────────────────────────┐
│   │ Cumulative returns: Classical TSMOM vs       │
│   │ Best LLM strategy vs Entropy-filtered LLM   │
│   │ (line chart, 2015-2025)                      │
│   └─────────────────────────────────────────────┘
│
│   Figure 2: ENTROPY DISCRIMINATION
│   ┌─────────────────────────────────────────────┐
│   │ Histogram: entropy distribution for correct  │
│   │ vs incorrect predictions (per model)         │
│   │ Show Cohen's d on each panel                 │
│   └─────────────────────────────────────────────┘
│
│   Figure 3: ENTROPY vs FORECAST ERROR
│   ┌─────────────────────────────────────────────┐
│   │ Scatter: H_mean (x) vs |pred - actual| (y)  │
│   │ One panel per model, with regression line    │
│   └─────────────────────────────────────────────┘
│
│   Figure 4: CALIBRATION CURVES
│   ┌─────────────────────────────────────────────┐
│   │ Standard vs Reasoning (same family overlaid) │
│   │ 3 panels: GPT family, Claude family, DSek   │
│   └─────────────────────────────────────────────┘
│
│   Figure 5: ENTROPY FILTER PERFORMANCE
│   ┌─────────────────────────────────────────────┐
│   │ Sharpe ratio vs entropy percentile threshold │
│   │ (keep top X% most confident predictions)     │
│   │ One line per model                           │
│   └─────────────────────────────────────────────┘
│
│   Figure 6: SHARPE HEATMAP
│   ┌─────────────────────────────────────────────┐
│   │ Heatmap: model (rows) × asset class (cols)  │
│   │ Color = Sharpe ratio                         │
│   └─────────────────────────────────────────────┘
│
│   Figure 7: COST-ADJUSTED PERFORMANCE
│   ┌─────────────────────────────────────────────┐
│   │ Sharpe ratio vs $ cost per forecast          │
│   │ Bubble size = number of trades taken          │
│   └─────────────────────────────────────────────┘
│
└── Save all figures as PNG (300 dpi) + source code in notebooks

AFTERNOON (4 hours):
├── Case study analysis: find the 5-10 most interesting examples
│   ├── Case 1: Reasoning model CAUGHT a regime change that
│   │          standard model missed (entropy was low → confident
│   │          AND correct)
│   ├── Case 2: High-entropy prediction that was correctly filtered
│   │          out (saved money by not trading)
│   ├── Case 3: Reasoning model OVERTHOUGHT and got it wrong
│   │          (entropy was low but answer was wrong — overconfidence)
│   ├── Case 4: Proxy entropy worked for DeepSeek-R1 when
│   │          true entropy wasn't available
│   └── Case 5: Standard model fluked a correct answer with
│              HIGH entropy (lucky, not skilled)
│
├── For each case: extract full reasoning trace, annotate
│   what the model did right/wrong, show entropy values
│
└── Write: analysis/case_studies.md
```

**Deliverables:**
- [ ] `figures/` — 7+ publication-quality figures
- [ ] `analysis/case_studies.md` — 5-10 annotated examples
- [ ] `notebooks/visualizations.ipynb` — reproducible figure code

---

### ═══════════════════════════════════════════════
### DAY 8 (Feb 27) — WRITE RESEARCH NOTE
### ═══════════════════════════════════════════════

**Goal:** Write the 4-6 page research note.

```
STRUCTURE:
──────────

1. ABSTRACT (150 words)
   "We test whether sequence-level entropy, a confidence signal
    introduced by Sharma & Chopra (2025), can predict the reliability
    of LLM forecasts for time-series momentum strategies..."

2. INTRODUCTION (0.5 page)
   ├── TSMOM is the most documented momentum strategy (cite MOP 2012)
   ├── LLMs are increasingly used for financial forecasting (cite Lossfunk)
   ├── Gap: no one has tested entropy-based confidence filtering
   │   on financial time series
   └── Our contribution: [3 bullet points]

3. RELATED WORK (0.5 page)
   ├── Time-series momentum (MOP 2012, AQR data)
   ├── LLM forecasting (Lossfunk AAAI 2026, ForecastBench)
   └── Entropy as confidence (Lossfunk NeurIPS 2025)

4. METHOD (1 page)
   ├── Data: ETFs, monthly returns, 2015-2025
   ├── Models: 8 models (3 standard, 5 reasoning)
   ├── Entropy: Shannon entropy from logprobs + proxy for R1
   ├── Strategy: classical TSMOM vs LLM vs entropy-filtered LLM
   └── Metrics: Sharpe, Brier, ECE, Cohen's d, ROC-AUC

5. RESULTS (1.5 pages)
   ├── Table 1: Strategy performance comparison
   ├── Figure 1: Cumulative returns
   ├── Table 2: Entropy discrimination by model
   ├── Figure 2: Entropy distributions (correct vs incorrect)
   ├── Figure 5: Entropy filter → Sharpe improvement curve
   └── Key findings per hypothesis

6. CASE STUDIES (0.5 page)
   └── 2-3 examples with reasoning trace excerpts

7. DISCUSSION (0.5 page)
   ├── What worked, what didn't
   ├── Limitations (ETFs ≠ futures, survivorship bias, lookback bias)
   ├── Connection to Lossfunk's work
   └── Open questions → RESIDENCY PROPOSAL

8. REFERENCES
```

**Deliverables:**
- [ ] `paper/research_note.md` — complete draft
- [ ] `paper/figures/` — figures copied for paper

---

### ═══════════════════════════════════════════════
### DAY 9 (Feb 28) — POLISH + OPEN SOURCE
### ═══════════════════════════════════════════════

**Goal:** Make everything reproducible and public.

```
MORNING (4 hours):
├── Clean all code
│   ├── Add docstrings to public functions
│   ├── Remove debug prints / commented code
│   ├── Ensure consistent style (black formatter)
│   ├── Add type hints to key functions
│   └── Verify requirements.txt is complete
├── Write comprehensive README.md
│   ├── Project title + abstract
│   ├── Key findings (2-3 bullet points)
│   ├── Figures (embed 2-3 key charts)
│   ├── Reproduction instructions
│   │   └── git clone → pip install → python run.py → results/
│   ├── Project structure
│   └── Citation / reference to Lossfunk papers
└── Add Makefile
    ├── make data      → download + process data
    ├── make baseline  → run classical TSMOM
    ├── make standard  → run standard model experiments
    ├── make reasoning → run reasoning model experiments
    ├── make analyze   → compute all metrics + figures
    └── make all       → full pipeline

AFTERNOON (4 hours):
├── Final review of research note
│   ├── Check all numbers match the actual results
│   ├── Check all figures are referenced
│   ├── Proofread for clarity
│   └── Trim to 4-6 pages (cut ruthlessly)
├── Test reproduction: clone repo → fresh venv → run
│   └── Does it actually work from scratch?
├── Push to GitHub
│   └── git add . && git commit && git push
└── Optional high-signal moves:
    ├── Tweet thread: 5-7 tweets summarizing key findings
    │   Tag @paraschopra @lossfunk
    └── Post on LinkedIn with link to repo
```

**Deliverables:**
- [ ] Clean, documented GitHub repo (public)
- [ ] README with embedded key figures
- [ ] Makefile for one-command reproduction
- [ ] Research note finalized

---

### ═══════════════════════════════════════════════
### DAY 10 (Mar 1) — APPLY
### ═══════════════════════════════════════════════

**Goal:** Submit application. Send signal.

```
MORNING (3 hours):
├── Draft application
│   ├── Who I am (1-2 sentences: trading + ML background)
│   ├── What I built (link to repo + research note)
│   ├── What I found (2-3 key findings from the research)
│   ├── How it extends Lossfunk's work
│   │   └── "Your 'Think Just Enough' showed entropy-based confidence
│   │        is an emergent property of reasoning models. I applied
│   │        this to financial momentum forecasting and found [X]."
│   ├── What I'd explore in 6 weeks (residency proposal)
│   │   └── Pick ONE:
│   │     a) Expand to full 58-instrument futures universe
│   │     b) Adaptive entropy thresholds per asset class
│   │     c) Multi-model ensemble with entropy-weighted voting
│   │     d) Real-time entropy monitoring for live strategies
│   └── Why Lossfunk specifically (genuine, not sycophantic)
│
└── Review: read it 3 times, cut everything that's not essential

AFTERNOON (2 hours):
├── Submit application via lossfunk.com/residency/
├── Save application text locally: application/submission.md
├── Optional: email/DM Paras Chopra
│   └── 2 sentences + repo link. Nothing more.
│   └── "I extended your AAAI and NeurIPS papers to financial
│        momentum forecasting. Results and code: [link]"
└── Done.
```

**Deliverables:**
- [ ] Application submitted
- [ ] `application/submission.md` — local backup
- [ ] (Optional) Tweet/DM sent

---

## BUDGET

```
┌──────────────────────────────────────────────────────────────┐
│ BUDGET BREAKDOWN                                             │
├──────────────────────────────┬──────────┬────────────────────┤
│ Item                         │ Cost     │ Notes              │
├──────────────────────────────┼──────────┼────────────────────┤
│ GPT-4.1 (1,200 calls)       │ $25      │ Standard baseline  │
│ Claude 3.7 Sonnet (1,200)   │ $25      │ Standard baseline  │
│ DeepSeek-V3 (1,200)         │ $8       │ Standard baseline  │
│ o3 (1,200 calls)            │ $140     │ Most expensive     │
│ o4-mini (1,200 calls)       │ $25      │ Cheap reasoning    │
│ Claude 3.7 Think (1,200)    │ $60      │ Reasoning          │
│ DeepSeek-R1 (1,200)         │ $12      │ No logprobs        │
│ Gemini 2.5 Pro (1,200)      │ $50      │ OPTIONAL           │
├──────────────────────────────┼──────────┼────────────────────┤
│ TOTAL (with Gemini)          │ ~$345    │                    │
│ TOTAL (without Gemini)       │ ~$295    │                    │
│ MINIMAL (6 models, 60 mo)   │ ~$150    │ Fallback budget    │
├──────────────────────────────┼──────────┼────────────────────┤
│ Buffer for retries/errors    │ +$30     │                    │
├──────────────────────────────┼──────────┼────────────────────┤
│ TOTAL WITH BUFFER            │ ~$325    │                    │
└──────────────────────────────┴──────────┴────────────────────┘
```

---

## RISK REGISTER

```
┌────────────────────────┬─────────┬──────────────────────────────────┐
│ Risk                   │Likelihd │ Mitigation                       │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ API rate limits stall  │ HIGH    │ Use async/parallel calls. Start  │
│ experiments            │         │ experiments early. Have fallback  │
│                        │         │ models ready.                    │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ o3 costs blow budget   │ MEDIUM  │ Monitor cost per call. After 200 │
│                        │         │ calls, check total. Reduce to 60 │
│                        │         │ months or drop o3 for o4-mini.   │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ LLMs can't parse       │ MEDIUM  │ Add retry with simplified prompt.│
│ numerical data well    │         │ Include both raw numbers and     │
│                        │         │ natural-language summary.        │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ Entropy doesn't        │ LOW     │ THIS IS A FINDING. Write it up   │
│ discriminate correct   │         │ as "entropy confidence doesn't   │
│ from incorrect         │         │ transfer to financial domain."   │
│                        │         │ Still publishable.               │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ Classical TSMOM beats  │ MEDIUM  │ Also a finding. "Reasoning adds  │
│ all LLM strategies     │         │ cost without alpha." Explore:    │
│                        │         │ can LLMs detect regime changes   │
│                        │         │ that TSMOM can't?                │
├────────────────────────┼─────────┼──────────────────────────────────┤
│ Day 2 data pipeline    │ LOW     │ yfinance is reliable. AQR data   │
│ fails                  │         │ is a direct download. Have both  │
│                        │         │ sources as backup for each other.│
├────────────────────────┼─────────┼──────────────────────────────────┤
│ Running out of time    │ MEDIUM  │ Day 8-9 compressible to 1 day.   │
│                        │         │ The CODE + RESULTS matter more   │
│                        │         │ than polish. Ship ugly if needed.│
├────────────────────────┼─────────┼──────────────────────────────────┤
│ DeepSeek-R1 proxy      │ LOW     │ Proxy entropy is ITSELF a novel  │
│ entropy is useless     │         │ contribution. Report the failure │
│                        │         │ and suggest logprobs as needed   │
│                        │         │ feature for reasoning APIs.      │
└────────────────────────┴─────────┴──────────────────────────────────┘
```

---

## REPOSITORY ARCHITECTURE

```
entropy-momentum/
│
├── README.md
├── LICENSE (MIT)
├── Makefile
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│   ├── raw/
│   │   ├── aqr_tsmom_factors.xlsx
│   │   └── etf_prices/              (yfinance downloads)
│   └── processed/
│       ├── etf_returns.parquet
│       └── formatted_prompts/       (pre-built LLM inputs)
│
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── download.py              (AQR + yfinance)
│   │   └── formatter.py             (data → LLM prompt)
│   ├── models/
│   │   ├── base.py                  (ModelInterface)
│   │   ├── openai_models.py
│   │   ├── anthropic_models.py
│   │   ├── deepseek_models.py
│   │   └── google_models.py
│   ├── entropy/
│   │   ├── calculator.py            (Shannon entropy from logprobs)
│   │   └── proxy.py                 (linguistic proxy for R1)
│   ├── strategies/
│   │   ├── classical_tsmom.py       (baseline strategy)
│   │   └── entropy_filter.py        (entropy-filtered LLM strategy)
│   ├── analysis/
│   │   ├── metrics.py               (Sharpe, Brier, ECE, etc.)
│   │   ├── entropy_analysis.py      (discrimination, correlation)
│   │   └── visualize.py             (all figure generation)
│   └── evaluate.py                  (main orchestrator)
│
├── results/
│   ├── raw/                         (API responses + logprobs)
│   ├── processed/                   (parsed CSVs)
│   ├── baseline/                    (classical TSMOM backtest)
│   └── metrics/                     (computed metrics)
│
├── analysis/
│   ├── hypothesis_results.md
│   ├── case_studies.md
│   └── notebooks/
│       ├── 01_baseline.ipynb
│       ├── 02_comparison.ipynb
│       ├── 03_entropy.ipynb
│       └── 04_figures.ipynb
│
├── figures/                         (PNG, 300 dpi)
│
├── paper/
│   ├── research_note.md
│   └── figures/
│
├── notes/
│   └── paper_notes.md
│
├── application/
│   └── submission.md
│
└── scripts/
    ├── run_standard.sh
    ├── run_reasoning.sh
    └── analyze.sh
```

---

## DEPENDENCIES

```python
# requirements.txt

# Data
yfinance>=0.2.31
pandas>=2.0
numpy>=1.24
openpyxl>=3.1             # for AQR Excel files
pyarrow>=14.0             # for parquet

# API clients
openai>=1.50
anthropic>=0.40
google-generativeai>=0.8

# Async
aiohttp>=3.9
asyncio

# Analysis
scipy>=1.11               # statistical tests
scikit-learn>=1.3         # ROC-AUC, calibration

# Visualization
matplotlib>=3.8
seaborn>=0.13

# Utilities
python-dotenv>=1.0
tqdm>=4.66
tenacity>=8.2             # retry logic for API calls
jsonlines>=4.0

# Code quality
black>=23.0
```

---

## SUCCESS CRITERIA

```
MINIMUM VIABLE (must have for application):
  ✓ Classical TSMOM baseline working
  ✓ At least 4 models tested (2 standard + 2 reasoning)
  ✓ Entropy computed for at least 2 models with logprobs
  ✓ One clear finding (positive or negative)
  ✓ Code on GitHub (even if rough)
  ✓ 2-3 page research note
  ✓ Application submitted

GOOD:
  ✓ All 8 models tested
  ✓ All 5 hypotheses tested with statistics
  ✓ 5+ figures
  ✓ Proxy entropy for DeepSeek-R1 evaluated
  ✓ Clean, reproducible repo
  ✓ 4-5 page research note with case studies

GREAT (stretch):
  ✓ All of the above
  ✓ Entropy-filtered strategy demonstrably beats unfiltered
  ✓ Tweet thread with engagement
  ✓ Response from Paras/Lossfunk team
```
