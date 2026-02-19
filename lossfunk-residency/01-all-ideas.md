# 5 Project Ideas — Ranked by Signal Strength

---

## Idea #1: Adaptive Compute Allocation for LLM Reasoning (BEST FIT)

**Extends:** "Think Just Enough" (NeurIPS 2025)

**What:** Build a system that dynamically decides how much reasoning budget to give
an LLM per query using sequence-level entropy as a confidence signal. Extend to
multi-agent settings or benchmark on newer models.

**Why it wins:**
- Directly extends their own work — shows you read their papers
- Touches efficiency + reasoning — two of the hottest areas in AI
- Practical implications for cost reduction in production systems

**Rough plan:**
- Days 1-2: Reproduce their results
- Days 3-7: Extend to new domain (code generation or math)
- Days 8-10: Write up + open-source

**Difficulty:** High (needs solid ML engineering)
**Uniqueness:** Medium (others may think of this)

---

## Idea #2: GPU Kernel Benchmarking & Optimization

**Extends:** Flash-Kernels, KernelBench-v2 repos

**What:** Write custom CUDA/Triton kernels for specific operations (sparse attention,
quantized matmul) and benchmark against existing implementations. Contribute PRs
to their repos.

**Why it wins:**
- Few applicants will have systems-level GPU skills — extremely rare
- Directly contributes to their open-source projects
- Shows engineering depth, not just ML theory

**Rough plan:**
- Days 1-2: Study their kernel repos and benchmarks
- Days 3-8: Implement + benchmark 2-3 kernels
- Days 9-10: Open PRs + writeup

**Difficulty:** Very High (needs CUDA expertise)
**Uniqueness:** Very High (rare skillset)

---

## Idea #3: LLM-as-Judge Calibration Study

**Extends:** IPO paper (ACL 2025) — "Your Language Model is Secretly a Preference Classifier"

**What:** How well-calibrated are LLMs as judges across domains? Build an evaluation
framework measuring calibration drift across model sizes, prompting strategies, and
domains.

**Why it wins:**
- Builds on their flagship ACL paper
- Evaluation/benchmarking is a Lossfunk core strength (ISO-Bench)
- Highly relevant to current RLHF/DPO discourse

**Rough plan:**
- Days 1-3: Build eval framework
- Days 4-7: Run experiments across 3-5 models
- Days 8-10: Analysis + open-source

**Difficulty:** Medium
**Uniqueness:** Medium

---

## Idea #4: AI Research Automation Pipeline

**Extends:** ai-scientist-artefacts-v1, ai-research-mentor, ICLR 2026 agent paper

**What:** Build an agent that reads papers, identifies extension opportunities, designs
experiments, and generates code scaffolds. Use their stateful agent specialization
approach.

**Why it wins:**
- Meta-research is Paras's obsession (multiple blog posts on "how to do research")
- Combines agents + science — two Lossfunk focus areas
- Accepted at Agents4Science 2025 — they're actively publishing here

**Rough plan:**
- Days 1-3: Build paper-reading agent
- Days 4-7: Add experiment design capability
- Days 8-10: Demo on 3 recent papers + open-source

**Difficulty:** Medium-High
**Uniqueness:** Medium (many people building research agents)

---

## Idea #5: Forecasting Calibration of Reasoning Models ← RECOMMENDED

**Extends:** "Future Is Unevenly Distributed" (AAAI 2026) + "Think Just Enough" (NeurIPS 2025)

**What:** Test whether reasoning models (o3, DeepSeek-R1, Claude w/ extended thinking)
actually improve forecasting calibration compared to standard models. Fills a gap
in Lossfunk's own paper where DeepSeek-R1 "did not provide reasoning traces."

**Why it wins:**
- Directly extends TWO of their papers
- Your trading background = genuine domain edge in calibration/prediction
- Fills an explicit gap they identified but didn't explore
- "Research, not product" — you're asking a question, not building a tool

**Rough plan:**
- Days 1-2: Dataset collection + infrastructure
- Days 3-5: Run all experiments
- Days 6-7: Analysis + hypothesis testing
- Days 8-9: Write-up + open-source
- Day 10: Apply

**Difficulty:** Medium
**Uniqueness:** High (trading + ML + their specific gap)

---

## Recommendation Matrix

```
                    Difficulty    Uniqueness    Lossfunk Fit    Your Edge
                    ----------    ----------    ------------    ---------
Idea 1 (Compute)   ████████░░    ██████░░░░    ██████████░░    ████░░░░░░
Idea 2 (CUDA)      ██████████    ██████████    ████████░░░░    ██░░░░░░░░
Idea 3 (Judge)     ██████░░░░    ██████░░░░    ████████░░░░    ████░░░░░░
Idea 4 (Agent)     ████████░░    ██████░░░░    ████████░░░░    ██████░░░░
Idea 5 (Forecast)  ██████░░░░    ████████░░    ██████████░░    ██████████  ← BEST
```

**Bottom line:** Idea #5 maximizes the intersection of (your trading edge) x (Lossfunk relevance) x (feasibility in 10 days).
