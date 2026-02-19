# Lossfunk Paper Analysis: "Future Is Unevenly Distributed"

> **Paper:** Future Is Unevenly Distributed: Forecasting Ability of LLMs Depends on What We're Asking
> **Authors:** Chinmay Karkar, Paras Chopra (Lossfunk)
> **Venue:** AAAI 2026 Workshop — AIR-FM (Assessing and Improving Reliability of Foundation Models)
> **arXiv:** https://arxiv.org/abs/2511.18394

---

## What They Did

Evaluated LLMs on real-world forecasting questions from prediction markets to understand
where and how LLM forecasting ability varies.

## Dataset

- **Source:** Polymarket, Metaculus, Manifold Markets
- **Initial pool:** ~10,000 questions
- **After aggressive multi-stage filtering:** 392 questions
- **Final evaluation set:** 150 questions (25 per category, uniformly sampled)
- **Time period:** Questions about events from Jan-Jul 2025 (beyond model cutoffs)

## Categories (6 domains, 5 sub-categories each)

```
1. Politics         → elections, policy, legislation, appointments, referendums
2. Entertainment    → box office, awards, releases, ratings, cancellations
3. Sports           → match outcomes, records, transfers, championships, injuries
4. Technology       → product launches, milestones, regulations, partnerships, failures
5. Finance          → market movements, earnings, economic indicators, IPOs, mergers
6. Geopolitics      → international relations, conflicts, treaties, sanctions, summits
```

## Models Tested

| Model | Provider | Notes |
|-------|----------|-------|
| GPT-5 | OpenAI | Latest flagship |
| GPT-4.1 | OpenAI | Previous gen |
| DeepSeek-R1 | DeepSeek | "Did not provide reasoning traces even when explicitly mentioned" |
| Claude 3.7 Sonnet | Anthropic | Standard (no extended thinking) |

All tested at temperature=0.0, max 4,500 tokens.

## Evaluation Metrics

### Accuracy
Simple binary correct/incorrect.

### Brier Score
```
Brier = (1/N) * Σ(f_i - o_i)²

where:
  f_i = predicted probability (0 to 1)
  o_i = actual outcome (0 or 1)

Lower = better
Perfect = 0.0
Random = 0.25
```

### Expected Calibration Error (ECE)
```
ECE = Σ (|B_m| / N) * |accuracy(B_m) - confidence(B_m)|

where:
  B_m = bin m of predictions grouped by confidence
  |B_m| = number of predictions in bin m
  accuracy(B_m) = fraction that actually resolved YES in bin m
  confidence(B_m) = average predicted probability in bin m

Lower = better
Perfect = 0.0
```

## Key Results

### Without News Context
```
Domain          Best Model          Accuracy    Brier Score
─────────────────────────────────────────────────────────
Geopolitics     Claude/GPT-5        ~84%        ~0.12
Politics        GPT-5               ~72%        ~0.18
Technology      Claude 3.7          ~68%        ~0.20
Entertainment   GPT-4.1             ~60%        ~0.24
Finance         Variable            ~48%        ~0.30
Sports          Variable            ~44%        ~0.32
```

### Effect of News Context
```
Domain          Effect of Adding News
──────────────────────────────────────
Finance         IMPROVED (context helps with market data)
Sports          IMPROVED (recent results/injuries help)
Entertainment   DEGRADED (noise, rumor anchoring)
Technology      DEGRADED (speculative reporting hurts)
Politics        MIXED
Geopolitics     MIXED
```

## Three Failure Modes Identified

### 1. Recency Bias
The model overweights recent headlines, abandoning prior reasoning.

**Example:** An S&P 500 question. Without news, the model correctly predicted a
bearish outcome. With news about "market hitting all-time highs," it flipped to
bullish — and was wrong. The recent headline overrode the model's better initial
judgment.

### 2. Rumor Overweighting (Rumor Anchoring)
The model treats speculative information as confirmed fact.

**Example:** A tariff question. News articles discussed tariff "possibilities" and
"considerations." The model interpreted these as "enacted policies" and made
predictions as if the tariffs were already in place.

### 3. Definition Drift
Acronyms or terms become ambiguous when news context introduces alternative meanings.

**Example:** A question about "MATS applications" (referring to an academic ML
alignment program). After news retrieval, articles about a trucking/transportation
show called "MATS" were included. The model's semantic grounding shifted, and it
answered about the wrong MATS entirely.

## The Gap You're Filling

The paper explicitly notes:
> "DeepSeek-R1 does not provide any reasoning traces even when explicitly mentioned"

This means:
1. They couldn't analyze HOW reasoning models think about forecasts
2. They didn't test reasoning vs. non-reasoning variants of the same family
3. They didn't test whether reasoning helps resist the three failure modes
4. They didn't test newer reasoning models (o3, Claude thinking, Gemini 2.5 Pro)

**Your project fills ALL of these gaps.**

## What Paras/Chinmay Would Want to See Next

Based on the paper's limitations and Lossfunk's other work:
1. Does reasoning improve calibration? (Your core question)
2. Can adaptive compute allocation optimize forecasting cost/quality? (Connects to "Think Just Enough")
3. What retrieval strategies avoid the failure modes? (Beyond simple news injection)
4. How does forecasting degrade with temporal distance from training? (Temporal calibration)
