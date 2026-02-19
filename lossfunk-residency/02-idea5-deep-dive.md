# Idea #5 — Deep Dive: Do Reasoning Chains Improve Forecasting Calibration?

---

## 1. The Research Question

> **Does extended reasoning (thinking tokens, chain-of-thought, self-reflection)
> systematically improve forecasting calibration — and if so, in which domains
> and why?**

### Why This Question Matters

Lossfunk's AAAI 2026 paper tested GPT-5, GPT-4.1, DeepSeek-R1, and Claude 3.7 Sonnet
on 150 prediction-market questions across 6 domains. They found:

- Geopolitics: 84% accuracy, ~0.12 Brier score (strong)
- Finance & Sports: 40-60% accuracy (weak)
- News context hurts as often as it helps

**The gap:** They tested DeepSeek-R1 but noted it "does not provide any reasoning
traces even when explicitly mentioned." They never properly evaluated whether
explicit chain-of-thought reasoning actually improves forecasting.

### The Broader Context

- LLMs now beat crowd forecasters (Brier ~0.101) but trail superforecasters (~0.081)
- Projected LLM-superforecaster parity: late 2026 (95% CI: Dec 2025 - Jan 2028)
- Reasoning models are the current frontier — but nobody has systematically studied
  their forecasting calibration

---

## 2. Hypotheses

### H1: Reasoning improves calibration more than accuracy
**Prediction:** Reasoning models won't get dramatically more questions "right" but
their probability estimates will be better calibrated (lower Brier, lower ECE).
Reasoning helps you know what you don't know.

**Rationale:** Forecasting is fundamentally about probability estimation, not binary
classification. A model that says "65% likely" when the true base rate is 65% is
more useful than one that says "90% likely" even if both get the binary answer right.

### H2: Reasoning helps most where standard models are weakest
**Prediction:** Finance and Sports (worst categories in Lossfunk's paper) will see
the biggest improvement from reasoning models.

**Rationale:** These domains require integrating many uncertain variables — exactly
where explicit decomposition and chain-of-thought should help most. Geopolitics
(already strong) may see diminishing returns.

### H3: Reasoning models resist news-context failure modes
**Prediction:** The three failure modes Lossfunk identified (recency bias, rumor
overweighting, definition drift) occur at lower rates in reasoning traces.

**Rationale:** If a model explicitly reasons "this is a rumor, not confirmed policy,"
it should be less susceptible to rumor anchoring. Extended thinking enables
self-correction.

### H4: There's a reasoning "sweet spot"
**Prediction:** Performance peaks at moderate reasoning length, then declines for
extremely long chains.

**Rationale:** Recent work on DeepSeek-R1 shows correct solutions have shorter
thinking chains than incorrect ones. Over-reasoning may introduce doubt, hedging,
or tangential considerations that degrade forecasts.

### H5: Superforecaster prompting + reasoning = best combination
**Prediction:** Structured decomposition prompts synergize with reasoning tokens
for a compounding effect.

**Alternative:** The prompt may be redundant — the model already does decomposition
internally. Testing the interaction effect is the point.

---

## 3. Methodology

### 3.1 Dataset Construction

**Sources:**
- Polymarket (crypto-native, high liquidity, politics/finance heavy)
- Metaculus (science/tech/geopolitics, well-calibrated community)
- Manifold Markets (broad coverage, lower liquidity)

**Target:** 200-300 resolved binary questions

**Categories (matching Lossfunk):**
1. Politics (elections, policy, legislation)
2. Entertainment (box office, awards, releases)
3. Sports (match outcomes, records, transfers)
4. Technology (product launches, company milestones)
5. Finance (market movements, earnings, economic indicators)
6. Geopolitics (international relations, conflicts, treaties)

**Filtering criteria:**
- Resolution date AFTER all models' training cutoffs
- Unambiguous resolution criteria
- Not trivially searchable (no "did X already happen?")
- Binary outcome (yes/no)
- Multi-stage aggressive filtering (match Lossfunk's approach)

### 3.2 Models

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL COMPARISON MATRIX                       │
├──────────────────────┬──────────────┬───────────────────────────┤
│ Model                │ Type         │ Purpose                   │
├──────────────────────┼──────────────┼───────────────────────────┤
│ Claude 3.7 Sonnet    │ Standard     │ Lossfunk baseline         │
│ Claude 3.7 (thinking)│ Reasoning    │ A/B vs standard Claude    │
│ GPT-4.1              │ Standard     │ Lossfunk baseline         │
│ o3                   │ Reasoning    │ OpenAI reasoning flagship │
│ o4-mini              │ Reasoning    │ Cost-efficient reasoning  │
│ DeepSeek-R1          │ Reasoning    │ Open-source, Lossfunk tested│
│ DeepSeek-V3          │ Standard     │ Non-reasoning control     │
│ Gemini 2.5 Pro       │ Reasoning    │ Google's reasoning entry  │
└──────────────────────┴──────────────┴───────────────────────────┘
```

**Key design:** Test reasoning vs. non-reasoning variants OF THE SAME FAMILY:
- Claude standard vs. Claude thinking → isolates reasoning effect
- GPT-4.1 vs. o3 → isolates reasoning effect
- DeepSeek-V3 vs. R1 → isolates reasoning effect

### 3.3 Experimental Conditions

Each question is tested under 3 prompt conditions:

**Condition A — Bare Prompt:**
```
Question: [question text]
Resolution criteria: [criteria]
Provide your probability estimate (0-100%) that this resolves YES.
```

**Condition B — With News Context:**
```
Question: [question text]
Resolution criteria: [criteria]
Here are relevant recent news articles:
[article summaries]
Provide your probability estimate (0-100%) that this resolves YES.
```

**Condition C — Superforecaster Prompt:**
```
You are an expert superforecaster. For the following question:
1. Identify the base rate for similar events
2. List factors that push the probability UP
3. List factors that push the probability DOWN
4. Consider the inside view vs. outside view
5. Provide a probability RANGE first, then a final point estimate

Question: [question text]
Resolution criteria: [criteria]
```

### 3.4 Evaluation Metrics

**Primary (matching Lossfunk for direct comparison):**

| Metric | Formula | What It Measures |
|--------|---------|------------------|
| Accuracy | correct / total | Binary hit rate |
| Brier Score | (1/N) * sum((f_i - o_i)^2) | Probabilistic calibration (lower = better) |
| ECE | sum((|B_m|/N) * |acc(B_m) - conf(B_m)|) | Confidence-accuracy gap across bins |

**New metrics you add:**

| Metric | What It Measures |
|--------|------------------|
| Reasoning length vs. accuracy | Do longer chains = better predictions? |
| Reasoning quality taxonomy | What strategies does the model use? |
| Failure mode frequency | Rate of recency bias / rumor anchoring / definition drift |
| Cost-adjusted Brier score | Brier score per dollar of API cost |
| Calibration curve AUC | Area between perfect calibration and actual curve |

### 3.5 Reasoning Trace Analysis

For every reasoning model response, classify the reasoning strategy:

```
REASONING STRATEGY TAXONOMY
├── Base Rate Lookup
│   └── "Events like this historically resolve YES ~40% of the time"
├── Decomposition
│   └── "This depends on factor A (likely) AND factor B (unlikely)"
├── Analogy
│   └── "Similar to the 2024 election where..."
├── Contrarian Check
│   └── "The obvious answer is X, but let me consider..."
├── Hedging / Uncertainty
│   └── "I'm not confident because..."
├── News Integration
│   └── "Recent reports suggest..."
└── Self-Correction
    └── "Wait, I initially thought X but actually..."
```

---

## 4. Expected Results & What They Mean

### Scenario A: Reasoning significantly improves calibration
→ Write up as "Reasoning Closes the Forecasting Gap" — reasoning models bring
  LLMs closer to superforecaster performance. Residency proposal: investigate
  optimal reasoning strategies per domain.

### Scenario B: Reasoning helps in some domains but hurts in others
→ Write up as "The Jagged Reasoning Frontier" — reasoning has domain-dependent
  effects. Residency proposal: build domain-adaptive reasoning allocation.
  (Connects to "Think Just Enough" paper.)

### Scenario C: Reasoning doesn't significantly help
→ This is ALSO a valuable finding. Write up as "More Thinking ≠ Better Forecasting"
  — challenges the assumption that reasoning tokens improve all tasks. Residency
  proposal: investigate what IS needed beyond reasoning (retrieval? ensembles?
  fine-tuning on forecaster data?).

### Scenario D: Superforecaster prompt is the dominant factor
→ Write up as "Prompting > Architecture for Forecasting" — the structured
  decomposition matters more than internal reasoning tokens. Residency proposal:
  optimize forecasting prompts, build prompt-selection systems.

**Key insight: Every outcome is publishable.** This is what makes it good research.

---

## 5. What to Propose for the 6-Week Residency

Based on your 10-day findings, propose ONE of these extensions:

1. **Adaptive reasoning budget for forecasting** — Combine with "Think Just Enough"
   to dynamically allocate reasoning tokens per question based on entropy signals.

2. **Multi-agent forecasting tournament** — Pit reasoning models against each other
   in adversarial debate format. Do ensemble forecasts beat individuals?

3. **Temporal calibration decay** — How does forecasting accuracy degrade as you
   move further from training cutoff? Is there a "forecasting horizon"?

4. **Cheap superforecasting** — Fine-tune a small model on superforecaster reasoning
   traces to match o3 at 1/100th the cost.

---

## 6. Why This Beats Other Applicants

1. **You show up with working code and results** — not just ideas
2. **It extends TWO Lossfunk papers** — forecasting + reasoning efficiency
3. **Your trading background is a genuine edge** — calibration and prediction markets
   are your native domain, not something you learned from a tutorial
4. **It's research, not a product** — the question "does reasoning help?" is genuinely
   open and scientifically interesting
5. **Every outcome is interesting** — no "it didn't work" dead end
