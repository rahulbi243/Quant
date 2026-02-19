# Diagram 2: Hypothesis Map & Decision Tree

## Five Hypotheses and What They Mean

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     HYPOTHESIS MAP                                      │
│                                                                         │
│  H1: Reasoning improves CALIBRATION more than ACCURACY                  │
│  ┌──────────────────────────────────────────────┐                       │
│  │  Standard Model          Reasoning Model     │                       │
│  │  Accuracy: 65%    →      Accuracy: 68%  (+3) │  ← Small improvement │
│  │  Brier:    0.22   →      Brier:    0.15 (-7) │  ← BIG improvement  │
│  │                                               │                      │
│  │  = Reasoning helps you KNOW WHAT YOU DON'T    │                      │
│  │    KNOW, not just get more answers right       │                     │
│  └──────────────────────────────────────────────┘                       │
│                                                                         │
│  H2: Reasoning helps MOST where standard models are WEAKEST             │
│  ┌──────────────────────────────────────────────┐                       │
│  │  Domain        Standard    Reasoning   Delta │                       │
│  │  ─────────     ────────    ─────────   ───── │                       │
│  │  Geopolitics   0.12        0.11        -0.01 │  ← Already good      │
│  │  Finance       0.30        0.20        -0.10 │  ← BIG improvement   │
│  │  Sports        0.32        0.22        -0.10 │  ← BIG improvement   │
│  │                                               │                      │
│  │  = Reasoning decomposition helps most in      │                      │
│  │    complex, multi-variable domains             │                     │
│  └──────────────────────────────────────────────┘                       │
│                                                                         │
│  H3: Reasoning RESISTS news-context failure modes                       │
│  ┌──────────────────────────────────────────────┐                       │
│  │  Failure Mode      Standard    Reasoning     │                       │
│  │  ─────────────     ────────    ─────────     │                       │
│  │  Recency Bias      Frequent    Rare          │                       │
│  │  Rumor Anchoring   Frequent    Rare          │                       │
│  │  Definition Drift  Frequent    Rare          │                       │
│  │                                               │                      │
│  │  Reasoning trace: "This is a rumor, not      │                       │
│  │  confirmed. I should weight it less..."       │                      │
│  └──────────────────────────────────────────────┘                       │
│                                                                         │
│  H4: There's a reasoning "SWEET SPOT"                                   │
│  ┌──────────────────────────────────────────────┐                       │
│  │                                               │                      │
│  │  Accuracy  ▲                                  │                      │
│  │            │       ╭──────╮                   │                      │
│  │            │      ╱        ╲                  │                      │
│  │            │     ╱          ╲                 │                      │
│  │            │    ╱            ╲                │                      │
│  │            │   ╱              ╲ ← overthinking│                      │
│  │            │  ╱                               │                      │
│  │            └──────────────────────►           │                      │
│  │              Reasoning Chain Length            │                      │
│  │                                               │                      │
│  │  = Too much thinking DEGRADES performance     │                      │
│  │    (connects to "Think Just Enough" paper)    │                      │
│  └──────────────────────────────────────────────┘                       │
│                                                                         │
│  H5: Superforecaster prompt + Reasoning = BEST combo                    │
│  ┌──────────────────────────────────────────────┐                       │
│  │                                               │                      │
│  │           Bare Prompt    Superforecaster      │                      │
│  │  Standard   0.25            0.20              │                      │
│  │  Reasoning  0.18            0.14  ← BEST?    │                      │
│  │                                               │                      │
│  │  OR is the prompt redundant with reasoning?   │                      │
│  │  Reasoning  0.18            0.18  ← NO HELP  │                      │
│  │                                               │                      │
│  │  = Testing the INTERACTION effect             │                      │
│  └──────────────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Decision Tree: What to Do With Results

```
                        ┌─────────────────────┐
                        │  Run experiments     │
                        │  Compute metrics     │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
        ┌───────────────────┐          ┌───────────────────┐
        │ Reasoning HELPS   │          │ Reasoning DOESN'T │
        │ (lower Brier)     │          │ HELP (same/worse) │
        └────────┬──────────┘          └────────┬──────────┘
                 │                               │
          ┌──────┴──────┐                 ┌──────┴──────┐
          ▼             ▼                 ▼             ▼
   ┌────────────┐ ┌──────────┐    ┌────────────┐ ┌──────────┐
   │ Helps in   │ │ Helps in │    │ Prompting  │ │ Neither  │
   │ ALL domains│ │ SOME     │    │ matters    │ │ helps    │
   │            │ │ domains  │    │ more than  │ │          │
   └─────┬──────┘ └────┬─────┘    │ reasoning │ └────┬─────┘
         │              │          └─────┬──────┘      │
         ▼              ▼                ▼             ▼
   ┌──────────┐  ┌──────────┐    ┌──────────┐  ┌──────────┐
   │Paper:    │  │Paper:    │    │Paper:    │  │Paper:    │
   │"Reasoning│  │"Jagged   │    │"Prompting│  │"The Fore-│
   │ Closes   │  │ Reasoning│    │ > Archi- │  │ casting  │
   │ the Gap" │  │ Frontier"│    │ tecture" │  │ Plateau" │
   └──────────┘  └──────────┘    └──────────┘  └──────────┘
         │              │                │             │
         ▼              ▼                ▼             ▼
   ┌──────────────────────────────────────────────────────┐
   │           RESIDENCY PROPOSAL (pick one)              │
   │                                                      │
   │  A) Adaptive reasoning budget per question           │
   │  B) Domain-specific reasoning strategies             │
   │  C) Prompt optimization systems                      │
   │  D) Beyond reasoning: retrieval + ensemble methods   │
   └──────────────────────────────────────────────────────┘
```

## Every Outcome Is Publishable

```
   ┌───────────────────────────────────────────────────────────────┐
   │                                                               │
   │   "Reasoning helps"          →  Quantify HOW MUCH and WHERE  │
   │   "Reasoning hurts"          →  Challenge a popular belief   │
   │   "Depends on the domain"    →  Nuanced, high-value finding  │
   │   "Prompting matters more"   →  Practical insight for field  │
   │   "Sweet spot exists"        →  Connects to compute efficiency│
   │                                                               │
   │   ═══════════════════════════════════════════════════════     │
   │   THERE IS NO "IT DIDN'T WORK" OUTCOME.                      │
   │   THIS IS WHAT MAKES IT GOOD RESEARCH.                        │
   │   ═══════════════════════════════════════════════════════     │
   │                                                               │
   └───────────────────────────────────────────────────────────────┘
```
