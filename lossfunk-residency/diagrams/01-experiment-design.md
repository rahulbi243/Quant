# Diagram 1: Experiment Design Overview

## How the Experiment Works

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATASET CONSTRUCTION                             │
│                                                                         │
│   Polymarket ──┐                                                        │
│   Metaculus  ──┼──► ~10,000 questions ──► Filter ──► 200-300 questions  │
│   Manifold   ──┘                           │                            │
│                                            ▼                            │
│                                   ┌────────────────┐                    │
│                                   │ Remove:        │                    │
│                                   │ • Ambiguous    │                    │
│                                   │ • Pre-cutoff   │                    │
│                                   │ • Searchable   │                    │
│                                   │ • Non-binary   │                    │
│                                   └────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CATEGORIZE INTO 6 DOMAINS                          │
│                                                                         │
│   ┌──────────┐ ┌──────────────┐ ┌────────┐                             │
│   │ Politics │ │Entertainment │ │ Sports │                              │
│   │  30-50   │ │    30-50     │ │ 30-50  │                              │
│   └──────────┘ └──────────────┘ └────────┘                              │
│   ┌────────────┐ ┌─────────┐ ┌────────────┐                            │
│   │ Technology │ │ Finance │ │ Geopolitics│                             │
│   │   30-50    │ │  30-50  │ │   30-50    │                             │
│   └────────────┘ └─────────┘ └────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TEST EACH QUESTION AGAINST                           │
│                                                                         │
│  ┌───────────────────────┐    ┌───────────────────────┐                 │
│  │   STANDARD MODELS     │    │   REASONING MODELS    │                 │
│  │                       │    │                       │                 │
│  │  • Claude 3.7 Sonnet  │◄──►│  • Claude 3.7 Think  │  ← Same family │
│  │  • GPT-4.1            │◄──►│  • o3                │  ← Same family │
│  │  • DeepSeek-V3        │◄──►│  • DeepSeek-R1       │  ← Same family │
│  │                       │    │  • o4-mini            │                 │
│  │                       │    │  • Gemini 2.5 Pro     │                 │
│  └───────────────────────┘    └───────────────────────┘                 │
│                                                                         │
│  Each model tested under 3 CONDITIONS:                                  │
│                                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐            │
│  │ A: Bare     │  │ B: + News    │  │ C: Superforecaster  │            │
│  │    Prompt   │  │    Context   │  │    Prompt           │            │
│  └─────────────┘  └──────────────┘  └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MEASURE & COMPARE                                │
│                                                                         │
│  Primary Metrics          New Metrics                                   │
│  ─────────────────        ────────────────────────────                  │
│  • Accuracy               • Reasoning length vs accuracy               │
│  • Brier Score             • Reasoning strategy taxonomy               │
│  • ECE                     • Failure mode frequency                    │
│                            • Cost-adjusted Brier score                 │
│                                                                         │
│  Total API calls: ~6,000-8,000                                          │
│  Estimated cost: $85-170                                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## The Key Comparison (Isolating Reasoning Effect)

```
    SAME MODEL FAMILY               DIFFERENT REASONING
    ─────────────────               ────────────────────

    Claude 3.7 Sonnet  ─── vs ───  Claude 3.7 (thinking)
         │                              │
         │    Only difference:          │
         │    reasoning tokens          │
         ▼                              ▼
    Brier = ?                      Brier = ?
    ECE   = ?                      ECE   = ?

    If reasoning model is better → reasoning HELPS forecasting
    If same or worse → reasoning DOESN'T HELP (also valuable!)
```
