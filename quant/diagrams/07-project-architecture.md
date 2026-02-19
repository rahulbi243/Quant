# Diagram 7: Project Code Architecture

## Repository Structure

```
reasoning-forecasting/
│
├── README.md                    ← Project overview, reproduction instructions
├── LICENSE                      ← MIT
├── requirements.txt             ← Python dependencies
├── Makefile                     ← One-command reproduction
├── .env.example                 ← API key template (never commit real keys)
│
├── data/
│   ├── raw/
│   │   ├── polymarket.json      ← Raw scraped questions
│   │   ├── metaculus.json
│   │   └── manifold.json
│   ├── filtered/
│   │   └── questions.json       ← Cleaned, categorized evaluation set
│   └── news_context/
│       └── {question_id}.json   ← News snippets per question
│
├── src/
│   ├── __init__.py
│   ├── collect.py               ← Data collection from prediction markets
│   ├── filter.py                ← Multi-stage question filtering
│   ├── evaluate.py              ← Core evaluation harness
│   ├── prompts.py               ← 3 prompt templates
│   ├── metrics.py               ← Brier, ECE, accuracy implementations
│   ├── models/
│   │   ├── __init__.py
│   │   ├── openai_models.py     ← GPT-4.1, o3, o4-mini
│   │   ├── anthropic_models.py  ← Claude standard + thinking
│   │   ├── deepseek_models.py   ← DeepSeek-V3, R1
│   │   └── google_models.py     ← Gemini 2.5 Pro
│   └── analysis/
│       ├── quantitative.py      ← Statistical tests, comparisons
│       ├── qualitative.py       ← Reasoning trace classification
│       └── visualize.py         ← Chart generation
│
├── results/
│   ├── raw/
│   │   ├── standard_models/     ← Raw API responses
│   │   └── reasoning_models/    ← Raw API responses + reasoning traces
│   ├── processed/
│   │   ├── standard_models.csv  ← Parsed predictions
│   │   └── reasoning_models.csv
│   └── metrics/
│       └── summary.csv          ← All computed metrics
│
├── analysis/
│   ├── notebooks/
│   │   ├── 01_baseline.ipynb    ← Baseline validation
│   │   ├── 02_comparison.ipynb  ← Standard vs reasoning comparison
│   │   ├── 03_calibration.ipynb ← Calibration curve analysis
│   │   ├── 04_reasoning.ipynb   ← Reasoning trace analysis
│   │   └── 05_failure.ipynb     ← Failure mode analysis
│   ├── hypothesis_tests.md      ← H1-H5 test results
│   └── case_studies.md          ← Detailed examples
│
├── figures/
│   ├── calibration_curves.png
│   ├── brier_heatmap.png
│   ├── reasoning_length.png
│   ├── domain_comparison.png
│   ├── strategy_distribution.png
│   └── cost_adjusted.png
│
├── paper/
│   ├── research_note.md         ← 3-5 page technical note
│   └── figures/                 ← Publication-quality figures
│
└── scripts/
    ├── run_standard.sh          ← Run standard model experiments
    ├── run_reasoning.sh         ← Run reasoning model experiments
    └── analyze.sh               ← Run full analysis pipeline
```

## Data Flow

```
┌────────────┐   ┌────────────┐   ┌────────────┐
│ Polymarket │   │  Metaculus  │   │  Manifold  │
│    API     │   │    API     │   │    API     │
└─────┬──────┘   └─────┬──────┘   └─────┬──────┘
      │                │                │
      └────────────────┼────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │   collect.py   │  ← Scrape ~10K questions
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │   filter.py    │  ← Multi-stage filtering
              │                │     → 200-300 questions
              │  • Post-cutoff │
              │  • Binary      │
              │  • Unambiguous │
              │  • Non-trivial │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ questions.json │  ← Categorized dataset
              │                │
              │ {id, question, │
              │  category,     │
              │  resolution,   │
              │  outcome}      │
              └────────┬───────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────────┐
    │ Cond A:  │ │ Cond B:  │ │ Cond C:      │
    │ Bare     │ │ + News   │ │ Superforecaster│
    │ Prompt   │ │ Context  │ │ Prompt       │
    └────┬─────┘ └────┬─────┘ └──────┬───────┘
         │            │              │
         └────────────┼──────────────┘
                      │
                      ▼
              ┌────────────────┐
              │  evaluate.py   │  ← Send to each model
              │                │     Store response +
              │  for model in  │     reasoning trace +
              │    models:     │     tokens + latency +
              │    for q in    │     cost
              │      questions:│
              │      predict() │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │  results/raw/  │  ← ~6,000 raw responses
              └────────┬───────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌────────────┐
   │ metrics.py │ │qualitat- │ │visualize.py│
   │            │ │ive.py    │ │            │
   │ • Brier    │ │          │ │ • Calibr.  │
   │ • ECE      │ │ • Trace  │ │   curves   │
   │ • Accuracy │ │   classif│ │ • Heatmaps │
   │ • Stats    │ │ • Failure│ │ • Scatter  │
   │   tests    │ │   modes  │ │ • Bar      │
   └────────────┘ └──────────┘ └────────────┘
          │            │            │
          └────────────┼────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ research_note  │  ← 3-5 page write-up
              │    .md         │     with figures
              └────────────────┘
```

## Key Dependencies (requirements.txt)

```
# API clients
openai>=1.0
anthropic>=0.30
google-generativeai>=0.5

# Data collection
requests>=2.31
aiohttp>=3.9        # async API calls for speed

# Analysis
pandas>=2.0
numpy>=1.24
scipy>=1.11         # statistical tests

# Visualization
matplotlib>=3.8
seaborn>=0.13
plotly>=5.18        # interactive charts

# Utilities
python-dotenv>=1.0  # API key management
tqdm>=4.66          # progress bars
jsonlines>=4.0      # streaming JSON storage
```
