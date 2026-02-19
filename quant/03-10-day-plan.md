# 10-Day Execution Plan

> Start date: Feb 18, 2026
> Deadline: Feb 28, 2026

---

## Day 1 (Feb 18) — Setup & Paper Study

### Morning
- [ ] Read Lossfunk's paper end-to-end: arxiv.org/abs/2511.18394
- [ ] Read the blog companion: letters.lossfunk.com/p/your-llm-is-a-confused-oracle
- [ ] Read "Think Just Enough" paper (NeurIPS 2025)
- [ ] Take notes on: metrics used, dataset construction, filtering criteria, model configs

### Afternoon
- [ ] Set up project repo (GitHub, public from day 1)
- [ ] Set up Python environment (venv, requirements.txt)
- [ ] Get API keys: OpenAI (o3, o4-mini, GPT-4.1), Anthropic (Claude), DeepSeek, Google (Gemini)
- [ ] Write data models / schema for storing results

### Deliverable
- GitHub repo initialized with README, LICENSE (MIT), and project structure
- Paper notes in `notes/` directory

---

## Day 2 (Feb 19) — Dataset Collection

### Morning
- [ ] Write scrapers for resolved questions:
  - Polymarket API (https://docs.polymarket.com/)
  - Metaculus API (https://www.metaculus.com/api/)
  - Manifold Markets API (https://docs.manifold.markets/)
- [ ] Pull ~500+ resolved binary questions (Jan-Dec 2025)

### Afternoon
- [ ] Filter questions:
  - Remove ambiguous / poorly defined
  - Remove trivially searchable
  - Remove those resolved before model cutoffs
  - Ensure binary (yes/no) resolution
- [ ] Categorize into 6 domains (target 30-50 per domain)
- [ ] Sample final evaluation set: 200-300 questions
- [ ] For "news context" condition: collect 2-3 relevant news snippets per question

### Deliverable
- `data/questions.json` — cleaned, categorized dataset
- `data/news_context/` — news snippets per question
- `scripts/collect_data.py` — reproducible collection pipeline

---

## Day 3 (Feb 20) — Evaluation Harness + Baseline

### Morning
- [ ] Build unified evaluation harness:
  ```
  evaluate(model, question, condition) → {
      answer: float (0-1),
      reasoning_trace: str,
      tokens_used: int,
      latency_ms: int,
      cost_usd: float
  }
  ```
- [ ] Implement 3 prompt templates (bare, news context, superforecaster)
- [ ] Implement Brier score, ECE, accuracy calculators

### Afternoon
- [ ] Run validation: test on 20 questions with Claude 3.7 Sonnet (bare prompt)
- [ ] Compare your Brier scores against Lossfunk's reported numbers
- [ ] Debug any discrepancies
- [ ] If numbers roughly match → proceed. If not → investigate prompt differences

### Deliverable
- `src/evaluator.py` — unified evaluation harness
- `src/metrics.py` — Brier, ECE, accuracy implementations
- `src/prompts.py` — 3 prompt templates
- Baseline validation results

---

## Day 4 (Feb 21) — Run Experiments: Standard Models

### Full Day
- [ ] Run all standard (non-reasoning) models across all conditions:

```
Models:    Claude 3.7 Sonnet, GPT-4.1, DeepSeek-V3
Conditions: Bare, News Context, Superforecaster
Questions: 200-300 each

Total calls: ~3 models x 3 conditions x 250 questions = ~2,250 API calls
```

- [ ] Store all raw responses in `results/raw/`
- [ ] Monitor for rate limits, errors, retries
- [ ] Spot-check 10 responses per model for sanity

### Deliverable
- `results/raw/standard_models/` — all raw API responses
- `results/processed/standard_models.csv` — parsed predictions + metadata
- Cost log: actual $ spent per model

---

## Day 5 (Feb 22) — Run Experiments: Reasoning Models

### Full Day
- [ ] Run all reasoning models across all conditions:

```
Models:     Claude 3.7 (thinking), o3, o4-mini, DeepSeek-R1, Gemini 2.5 Pro
Conditions: Bare, News Context, Superforecaster
Questions:  200-300 each

Total calls: ~5 models x 3 conditions x 250 questions = ~3,750 API calls
```

- [ ] IMPORTANT: Store full reasoning traces (these are critical for analysis)
- [ ] Log thinking token counts separately from output tokens
- [ ] Monitor costs carefully — reasoning models are more expensive

### Deliverable
- `results/raw/reasoning_models/` — all raw responses WITH reasoning traces
- `results/processed/reasoning_models.csv` — parsed predictions + metadata
- Cost log updated

---

## Day 6 (Feb 23) — Quantitative Analysis

### Morning
- [ ] Compute all metrics per model x condition x domain:
  - Accuracy (binary)
  - Brier Score
  - ECE (10 bins)
  - Calibration curves
- [ ] Build comparison tables:
  - Standard vs. Reasoning (same family)
  - Across conditions (bare vs. news vs. superforecaster)
  - Across domains (6 categories)

### Afternoon
- [ ] Statistical tests:
  - Paired t-test or Wilcoxon signed-rank for Brier score differences
  - Bootstrap confidence intervals
  - Effect sizes (Cohen's d)
- [ ] Test each hypothesis (H1-H5) against the data
- [ ] Identify surprising results / outliers

### Deliverable
- `analysis/metrics_summary.csv` — all computed metrics
- `analysis/hypothesis_tests.md` — statistical test results
- `analysis/notebooks/quantitative.ipynb` — reproducible analysis notebook

---

## Day 7 (Feb 24) — Qualitative Analysis + Diagrams

### Morning
- [ ] Reasoning trace analysis:
  - Sample 50 traces from reasoning models
  - Classify reasoning strategies (base rate, decomposition, analogy, etc.)
  - Count frequency of each strategy per domain
  - Identify self-correction patterns

### Afternoon
- [ ] Failure mode analysis:
  - Find instances of recency bias, rumor anchoring, definition drift
  - Compare frequency: standard vs. reasoning models
  - Document 5-10 compelling case studies (specific questions where reasoning
    helped or hurt, with full traces)
- [ ] Generate all visualizations:
  - Calibration curves (per model family)
  - Brier score heatmap (model x domain)
  - Reasoning length vs. accuracy scatter plot
  - Bar charts comparing conditions
  - Reasoning strategy distribution pie charts

### Deliverable
- `analysis/reasoning_traces.md` — qualitative analysis
- `analysis/case_studies.md` — 5-10 detailed examples
- `figures/` — all charts and visualizations (PNG + source code)

---

## Day 8 (Feb 25) — Write Research Note

### Full Day
Write a 3-5 page technical research note:

```
Structure:
1. Abstract (150 words)
2. Introduction & Motivation (0.5 page)
   - Gap in Lossfunk's paper
   - Why reasoning models matter for forecasting
3. Method (1 page)
   - Dataset, models, conditions, metrics
4. Results (1.5 pages)
   - Main findings per hypothesis
   - Key figures and tables
   - Surprising results
5. Case Studies (0.5 page)
   - 2-3 compelling examples with reasoning traces
6. Discussion & Open Questions (0.5 page)
   - What this means
   - What to explore next (= residency proposal)
7. References
```

### Deliverable
- `paper/research_note.md` — complete research note
- `paper/figures/` — publication-quality figures

---

## Day 9 (Feb 26) — Polish + Open Source

### Morning
- [ ] Clean up all code:
  - Add docstrings to key functions
  - Ensure `requirements.txt` is complete
  - Write clear README.md with reproduction instructions
  - Add `Makefile` or shell scripts for one-command reproduction
- [ ] Verify everything runs from scratch (clone → install → run → results)

### Afternoon
- [ ] Final review of research note
- [ ] Create a 1-page summary / TL;DR
- [ ] Push everything to GitHub
- [ ] Share on Twitter/X and tag @paraschopra and @lossfunk (optional but high signal)

### Deliverable
- Clean, documented, reproducible GitHub repo
- Published research note
- (Optional) Twitter thread summarizing findings

---

## Day 10 (Feb 27) — Apply

### Morning
- [ ] Draft application (concise, no fluff):
  - Who you are (trading/ML background)
  - What you built (link to repo + research note)
  - What you found (1-2 key findings)
  - What you'd explore in 6 weeks (residency proposal)
  - Why Lossfunk specifically (reference their papers, not generic praise)

### Afternoon
- [ ] Review and edit application
- [ ] Submit
- [ ] (Optional) Send a short, respectful email/DM to Paras Chopra with your repo link
  and a 2-sentence summary of your findings

### Deliverable
- Submitted application
- Backup: application text saved locally

---

## Budget Estimate

| Item | Estimated Cost |
|------|---------------|
| OpenAI API (o3, o4-mini, GPT-4.1) | $40-80 |
| Anthropic API (Claude standard + thinking) | $20-40 |
| DeepSeek API (R1, V3) | $10-20 |
| Google API (Gemini 2.5 Pro) | $15-30 |
| **Total** | **$85-170** |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| API rate limits | Start experiments early, use exponential backoff, parallelize |
| Dataset too small after filtering | Lower bar slightly, aim for 150 minimum |
| One model's API is down | Drop it, still have 7+ models to compare |
| Results are boring/inconclusive | "No significant effect" IS a finding. Write it up honestly. |
| Running out of time | Days 8-9 can be compressed. The code + results matter more than polish. |
| Over budget | Drop one model (Gemini), reduce to 150 questions |
