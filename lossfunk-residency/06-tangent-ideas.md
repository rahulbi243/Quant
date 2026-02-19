# Tangent Ideas — Derived from Your Resources

> **Source material:**
> 1. QuantMuse — production quant trading platform (Python/C++, multi-factor, LLM-integrated)
> 2. @quantscience_ tweet — "Time Series Momentum" is the #1 hedge fund method (Moskowitz, Ooi, Pedersen paper)
> 3. @RohOnChain tweet — AI crypto trading agents
> 4. @heynavtoor tweet — "12 Claude prompts that replace $400K/year quant researchers"
>
> Cross-referenced with Lossfunk's research areas and what makes a strong residency application.

---

## The Big Synthesis

Your resources all orbit one theme: **AI is eating quantitative finance, but nobody
is rigorously studying HOW WELL it actually works.** Everyone is building trading
bots and sharing prompts, but no one is doing the Lossfunk-style careful measurement
of where AI reasoning succeeds and fails in financial contexts.

That's your edge. You don't build another bot. You **study the bots.**

---

## Tangent A: Can LLMs Discover Time-Series Momentum? (Research-Heavy)

### The Idea

Time-series momentum (TSMOM) is the most documented hedge fund alpha source
(Moskowitz, Ooi, Pedersen 2012 — Sharpe ratio 1.31 across 58 instruments). The
question: **Can LLMs rediscover or improve upon TSMOM strategies from raw data,
and how do reasoning models compare to standard models at this task?**

### Why It Fits Lossfunk

- Extends their forecasting paper into a SPECIFIC financial domain (their weakest category)
- Tests whether LLM "reasoning" about price series is real or pattern-matching noise
- Connects to their "Think Just Enough" paper — how much reasoning does a model
  need to identify momentum signals?

### What You'd Actually Do

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  EXPERIMENT DESIGN                                                  │
│                                                                     │
│  Give LLMs historical price data for 58 instruments (matching       │
│  the original TSMOM paper) and ask them to:                         │
│                                                                     │
│  Task 1: PREDICT — given 12 months of returns, predict next month   │
│           direction (long/short signal)                              │
│                                                                     │
│  Task 2: EXPLAIN — articulate WHY the signal exists                 │
│           (can they rediscover momentum without being told?)        │
│                                                                     │
│  Task 3: IMPROVE — suggest modifications to the vanilla TSMOM       │
│           strategy (alternative lookback windows, volatility         │
│           weighting schemes, regime detection)                      │
│                                                                     │
│  Compare: Standard LLMs vs Reasoning LLMs vs Classical TSMOM       │
│                                                                     │
│  Metrics: Sharpe ratio, max drawdown, hit rate, correlation to     │
│           original TSMOM returns                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Hypotheses

```
H1: LLMs can match TSMOM direction predictions (~55-60% hit rate)
    but with WORSE calibration on magnitude

H2: Reasoning models will identify momentum-like patterns without
    being explicitly told about TSMOM

H3: LLMs will add value in REGIME DETECTION — identifying when
    momentum works vs. when it reverses (the "momentum crash" problem)

H4: The combination of classical TSMOM + LLM regime overlay
    will have a higher Sharpe than either alone
```

### Your Trading Edge

You actually understand TSMOM from practice. Most ML researchers who'd apply to
Lossfunk wouldn't know what a lookback window is or why momentum crashes happen.
You can evaluate LLM outputs for financial plausibility, not just statistical metrics.

### Feasibility: 10 Days

```
Days 1-2: Get TSMOM data (futures data from Yahoo/Quandl, replicate baseline)
Days 3-4: Build LLM evaluation harness (feed price series, collect predictions)
Days 5-6: Run standard vs reasoning models on prediction + explanation tasks
Days 7-8: Analyze: do LLMs find momentum? Do they find the crash risk?
Days 9-10: Write up + apply
```

**Estimated cost:** $50-100 (API calls on numerical data are token-cheap)

---

## Tangent B: LLM-as-Quant-Researcher — Prompt Engineering vs. Reasoning (Applied)

### The Idea

The @heynavtoor tweet claims "12 Claude prompts replace $400K/year quant researchers."
Goldman Sachs is actively deploying Claude for accounting/compliance. The question:
**When you prompt an LLM to do quant research, does REASONING actually improve
the quality, or is prompt engineering sufficient?**

### Why It Fits Lossfunk

- Directly tests their "Think Just Enough" thesis in a new domain
- Connects to their interest in AI agents (can LLMs do autonomous multi-step
  financial analysis?)
- Financial research has GROUND TRUTH — you can backtest strategies the LLM suggests

### What You'd Actually Do

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  BENCHMARK: "Quant Research Tasks"                                  │
│                                                                     │
│  Task 1: FACTOR DISCOVERY                                           │
│  ├── Input: 10 years of stock data (returns, fundamentals)          │
│  ├── Ask: "Identify factors that predict future returns"            │
│  └── Ground truth: known factors (momentum, value, quality, etc.)   │
│                                                                     │
│  Task 2: STRATEGY DESIGN                                            │
│  ├── Input: asset class + return series                             │
│  ├── Ask: "Design a systematic trading strategy"                    │
│  └── Ground truth: backtest the suggested strategy's Sharpe ratio   │
│                                                                     │
│  Task 3: RISK ANALYSIS                                              │
│  ├── Input: portfolio + recent market data                          │
│  ├── Ask: "What are the key risks and how to hedge?"               │
│  └── Ground truth: compare to actual drawdowns that followed        │
│                                                                     │
│  Task 4: PAPER REPLICATION                                          │
│  ├── Input: abstract of a quant finance paper                       │
│  ├── Ask: "Write code to replicate this strategy"                  │
│  └── Ground truth: does the code actually produce correct results?  │
│                                                                     │
│  MODELS: Claude (std) vs Claude (thinking) vs o3 vs GPT-4.1        │
│  CONDITIONS: Bare prompt vs Structured quant prompt vs Reasoning    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Key Insight

Unlike generic benchmarks, **quant research has objectively verifiable outcomes**.
If an LLM suggests a strategy, you can backtest it. If it identifies a risk, you
can check if the risk materialized. This creates a clean evaluation framework.

### Connection to QuantMuse

QuantMuse (from your resources) already has a multi-factor framework, backtesting
engine, and LLM integration. You could:
- Use its backtesting infrastructure to evaluate LLM-suggested strategies
- Compare LLM factor discovery against its built-in factor models
- Test whether reasoning models suggest strategies that QuantMuse's classical
  approach would miss

### Feasibility: 10 Days

```
Days 1-2: Define 20 quant research tasks with ground truth
Days 3-4: Run across 4 models × 3 conditions
Days 5-6: Backtest all LLM-suggested strategies
Days 7-8: Compare: reasoning vs prompting vs classical quant
Days 9-10: Write up + apply
```

---

## Tangent C: Prediction Market Microstructure + LLM Agents (Trading-Native)

### The Idea

From the Polymarket-related search results: wallets are making $270K farming
15-minute markets with simple bots, while other bots lose money catastrophically.
The question: **Can reasoning-enabled LLM agents outperform simple rule-based
bots in prediction market trading, and what failure modes emerge?**

### Why It Fits Lossfunk

- Directly extends their forecasting paper into an ACTIVE TRADING context
- Tests their agent research (ICLR 2026: "Automated Stateful Specialization")
- Prediction markets are the ideal testbed: binary outcomes, public data, real stakes
- Failure mode analysis mirrors their paper's approach

### What You'd Actually Do

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ARCHITECTURE: LLM Agent for Prediction Markets                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ PERCEPTION    │    │ REASONING     │    │ ACTION       │          │
│  │              │    │              │    │              │          │
│  │ • Market     │───►│ • Estimate   │───►│ • Size       │          │
│  │   prices     │    │   true prob  │    │   position   │          │
│  │ • Order book │    │ • Identify   │    │ • Place      │          │
│  │ • News feed  │    │   mispricing │    │   orders     │          │
│  │ • Resolution │    │ • Risk check │    │ • Manage     │          │
│  │   criteria   │    │              │    │   portfolio  │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                              │                                      │
│                              ▼                                      │
│                    ┌──────────────┐                                 │
│                    │ COMPARE:     │                                 │
│                    │ • Simple bot │  ← Rule-based (buy <40%, sell  │
│                    │   (no LLM)  │     >60% — like the $270K bot) │
│                    │ • Std LLM   │  ← Standard model forecasting  │
│                    │ • Reasoning  │  ← Extended thinking           │
│                    │   LLM       │                                 │
│                    └──────────────┘                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### The Research Questions

```
Q1: Does an LLM agent identify profitable mispricing that simple bots miss?
Q2: Does reasoning help the agent AVOID bad trades (failure mode resistance)?
Q3: What's the cost-adjusted PnL? (API costs eat into thin-margin markets)
Q4: How does the agent handle the Lossfunk failure modes (recency bias,
    rumor anchoring, definition drift) in a LIVE trading context?
```

### Feasibility: 10 Days (Paper Trading Only)

```
Days 1-2: Pull historical Polymarket data (resolved markets, order books)
Days 3-4: Build simulation: replay historical markets, let agents trade
Days 5-6: Run standard LLM vs reasoning LLM vs simple bot
Days 7-8: Analyze PnL, failure modes, decision quality
Days 9-10: Write up + apply
```

**Note:** No real money needed. Historical replay/simulation is sufficient and
more rigorous than live testing for a research paper.

---

## Tangent D: The Quant Prompt Benchmark — Do LLMs Actually Replace Quant Researchers? (Debunking)

### The Idea

The @heynavtoor tweet claims Claude can "replace $400K/year quant researchers."
Goldman Sachs is deploying Claude for accounting. **Build a rigorous benchmark
that tests this claim.** How good are LLMs at SPECIFIC quant research tasks,
measured against ground truth?

### Why It Fits Lossfunk

- Lossfunk explicitly values "good science in AI" — debunking hype IS good science
- Paras wrote "Manifesto for doing good science" — testing viral claims rigorously
  is exactly this manifesto in action
- Creates an open benchmark (like their ISO-Bench) for the quant finance community

### What You'd Actually Build

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  QUANT-BENCH: A Benchmark for LLM Quantitative Finance Ability     │
│                                                                     │
│  CATEGORY 1: MATHEMATICAL FINANCE (20 tasks)                        │
│  ├── Option pricing (Black-Scholes, binomial trees)                │
│  ├── Portfolio optimization (Markowitz, risk parity)               │
│  ├── Risk metrics (VaR, CVaR, Greeks computation)                  │
│  └── Ground truth: known analytical solutions                      │
│                                                                     │
│  CATEGORY 2: DATA ANALYSIS (20 tasks)                               │
│  ├── Factor regression (Fama-French, Carhart)                      │
│  ├── Time series analysis (stationarity, cointegration)            │
│  ├── Anomaly detection in market data                              │
│  └── Ground truth: textbook answers + standard test datasets       │
│                                                                     │
│  CATEGORY 3: STRATEGY (20 tasks)                                    │
│  ├── "Design a mean-reversion strategy for X"                      │
│  ├── "Backtest momentum on this dataset"                           │
│  ├── "Identify regime changes in this return series"               │
│  └── Ground truth: backtest the LLM's code, compare Sharpe ratios │
│                                                                     │
│  CATEGORY 4: REASONING (20 tasks)                                   │
│  ├── "Why did this strategy fail in 2020?"                         │
│  ├── "What risks does this portfolio have?"                        │
│  ├── "Critique this research paper's methodology"                  │
│  └── Ground truth: expert quant researcher evaluations             │
│                                                                     │
│  TOTAL: 80 tasks × 4-8 models = 320-640 evaluations               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Is Particularly Strong

- **Open-sourceable as a benchmark** (like Lossfunk's ISO-Bench)
- **Viral potential** — "We tested the claim that AI replaces quant researchers. Here's what we found."
- **Reusable** — others can run it on new models as they come out
- **Connects to Goldman Sachs deploying Claude** — timely and relevant

---

## Tangent E: Entropy-Guided Financial Reasoning (Theory-Heavy)

### The Idea

Combine Lossfunk's "Think Just Enough" (entropy as confidence signal) with
financial forecasting. **Can sequence-level entropy in an LLM's reasoning trace
predict WHEN its financial forecasts are reliable vs. unreliable?**

### Why It Fits Lossfunk

- DIRECTLY extends two of their papers simultaneously
- Novel application of their entropy framework to a new domain
- If it works, it's a practical tool for deciding when to trust LLM forecasts

### The Mechanism

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  THE CORE IDEA                                                      │
│                                                                     │
│  When an LLM reasons about a financial question:                    │
│                                                                     │
│  LOW ENTROPY reasoning trace:                                       │
│  "The Fed raised rates 3 times in 2024. Historically, this leads   │
│   to X. The data clearly points to Y. I'm confident: 80% YES."     │
│   ─── Tokens flow smoothly, model is "sure" ───                   │
│   → ENTROPY: LOW                                                   │
│   → PREDICTION: Likely reliable                                    │
│                                                                     │
│  HIGH ENTROPY reasoning trace:                                      │
│  "On one hand... but then again... however... it's also possible   │
│   that... although some argue... I'll say 55% YES."                │
│   ─── Tokens are uncertain, model is "confused" ───               │
│   → ENTROPY: HIGH                                                  │
│   → PREDICTION: Likely unreliable                                  │
│                                                                     │
│  HYPOTHESIS: Sequence-level entropy of the reasoning trace          │
│  CORRELATES with forecast accuracy. We can use it as a              │
│  "confidence filter" — only trust forecasts where entropy is low.  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### What You'd Measure

```
  Brier Score  ▲
  (worse)      │
               │   ●
     0.35      │       ●  ← All predictions (no filter)
               │   ●       ●
     0.30      │               ●
               │
     0.25      │────────────────── Random baseline ──────
               │                       ●
     0.20      │                   ●       ●
               │               ●
     0.15      │           ●
               │       ●  ← Only LOW-entropy predictions
     0.10      │   ●
               │
     0.05      │
               └──────────────────────────────────────────►
                  All     Top 80%  Top 60%  Top 40%  Top 20%
                  preds   (filtered by low entropy)

  If this curve slopes DOWN → entropy is a useful confidence signal
  for financial forecasting. You can "know when you don't know."
```

---

## Comparison Matrix: Which Tangent to Pick?

```
                   Lossfunk   Your       Feasibility  Novelty   Publishability
                   Fit        Edge       (10 days)
                   ─────────  ─────────  ───────────  ────────  ─────────────
A: TSMOM Discovery ████████   ██████████  ████████     ████████  ████████
B: Quant Research   ██████     ████████    ██████       ██████    ██████
C: Prediction Mkt   ████████   ██████████  ██████       ████████  ████████
D: Quant Benchmark  ██████     ████████    ████████     ██████    ██████████
E: Entropy-Guided   ██████████ ████████    ██████       ██████████ ██████████
```

## My Recommendation: Combine A + E

**Pick Tangent A (TSMOM) as the domain, Tangent E (Entropy) as the method.**

The research question becomes:

> **Can sequence-level entropy in LLM reasoning traces predict when
> time-series momentum forecasts are reliable — and does this create
> a better momentum strategy than classical TSMOM?**

This gives you:
- A well-defined financial domain (TSMOM) with 60 years of data
- A Lossfunk-native method (entropy signals from "Think Just Enough")
- A clear ground truth (backtest returns)
- A result that's interesting regardless of outcome
- A natural residency extension (6 weeks to expand to other strategies/domains)

---

## How This Connects Back to Idea #5

These tangents aren't replacements for Idea #5 — they're REFINEMENTS. Instead of
generic "forecasting calibration of reasoning models," you now have:

```
Original Idea #5                  Tangent-Refined Version
────────────────                  ──────────────────────
"Test reasoning models on         "Test reasoning models on TIME-SERIES
 prediction market questions"      MOMENTUM forecasting, using ENTROPY
                                   as a confidence signal, benchmarked
                                   against classical TSMOM strategies"
```

The tangent-refined version is:
- More specific (TSMOM, not "all forecasting")
- More measurable (backtest returns, not just Brier scores)
- More novel (entropy + finance intersection is unexplored)
- More connected to Lossfunk (extends TWO of their papers)
- More connected to YOU (trading background)

---

## References from Resources

- [QuantMuse — Production Quant Trading Platform](https://github.com/0xemmkty/QuantMuse)
- [Time Series Momentum Effect — Quantpedia](https://quantpedia.com/strategies/time-series-momentum-effect)
- [Original TSMOM Paper — Moskowitz, Ooi, Pedersen](http://docs.lhpedersen.com/TimeSeriesMomentum.pdf)
- [Goldman Sachs deploys Anthropic's Claude](https://www.cnbc.com/2026/02/06/anthropic-goldman-sachs-ai-model-accounting.html)
- [Claude Equity Research Plugin](https://github.com/quant-sentiment-ai/claude-equity-research)
- [@quantscience_ — TSMOM tweet](https://x.com/i/status/2024530270116880485)
- [@heynavtoor — Claude quant prompts tweet](https://x.com/i/status/2023309961762336863)
- [Polymarket $270K farming bot](https://x.com/PolymarketStory/status/2008947310957613306)
