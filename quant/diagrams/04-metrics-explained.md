# Diagram 4: Metrics Explained Visually

## Brier Score — The Most Important Metric

```
  BRIER SCORE = (1/N) × Σ (prediction - outcome)²

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  Example: 4 predictions about "Will X happen?"              │
  │                                                             │
  │  Question    Predicted    Actual    (pred - actual)²        │
  │  ────────    ─────────    ──────    ────────────────        │
  │  Q1          0.90 (90%)   1 (YES)   (0.90-1)² = 0.01      │
  │  Q2          0.30 (30%)   0 (NO)    (0.30-0)² = 0.09      │
  │  Q3          0.70 (70%)   1 (YES)   (0.70-1)² = 0.09      │
  │  Q4          0.50 (50%)   0 (NO)    (0.50-0)² = 0.25      │
  │                                                             │
  │  Brier = (0.01 + 0.09 + 0.09 + 0.25) / 4 = 0.11           │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  INTERPRETING BRIER SCORES:

    0.00  ████████████████████████████████  Perfect (impossible)
    0.05  █████████████████████████████     Excellent (superforecasters)
    0.08  ████████████████████████████      Superforecaster level (~0.081)
    0.10  ███████████████████████████       Best LLMs currently (~0.101)
    0.12  ██████████████████████████        Lossfunk best result (geopolitics)
    0.15  ████████████████████████          Good
    0.20  █████████████████████             Mediocre
    0.25  ██████████████████                Random guessing (coin flip)
    0.30  ████████████████                  Lossfunk worst (finance/sports)
    0.50  ████████████                      Terrible
    1.00                                    Always maximally wrong


  WHY BRIER > ACCURACY FOR FORECASTING:

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  Scenario: "Will the S&P close above 5000?"             │
    │  Actual outcome: YES                                    │
    │                                                         │
    │  Model A says: 90% → Correct! Brier: (0.9-1)² = 0.01  │
    │  Model B says: 51% → Correct! Brier: (0.51-1)² = 0.24 │
    │                                                         │
    │  Both get ACCURACY right (predicted YES correctly)      │
    │  But Model A's CALIBRATION is far superior              │
    │                                                         │
    │  Brier Score captures this difference. Accuracy doesn't.│
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

## Calibration Curve — Visual Check of How Well-Calibrated a Model Is

```
  PERFECT CALIBRATION (what we want):

    Actual    ▲
    Frequency │
    (%)       │
     100      │                              ╱
              │                           ╱
      80      │                        ╱
              │                     ╱
      60      │                  ╱         ← Perfect: 45-degree line
              │               ╱              When model says "60%",
      40      │            ╱                 events happen 60% of the time
              │         ╱
      20      │      ╱
              │   ╱
       0      │╱───────────────────────────►
              0    20    40    60    80   100
                    Predicted Probability (%)


  OVERCONFIDENT MODEL (common failure):

    Actual    ▲
    Frequency │
    (%)       │                   ╱╱╱  perfect
     100      │              ___╱╱
              │          __╱╱       ← Model says "80%" but events
      80      │       _╱╱             only happen 65% of the time
              │     ╱╱
      60      │   ╱╱       ← The GAP between the curve and the
              │  ╱╱           diagonal = calibration error
      40      │ ╱╱
              │╱╱
      20      │╱
              │
       0      │───────────────────────────►
              0    20    40    60    80   100


  UNDERCONFIDENT MODEL (hedges too much):

    Actual    ▲
    Frequency │
    (%)       │                ╱╱ perfect
     100      │             ╱╱
              │          ╱╱╱╱
      80      │        ╱╱╱        ← Model says "50%" but events
              │      ╱╱╱             happen 70% of the time
      60      │    ╱╱╱
              │  ╱╱╱         ← The model doesn't "trust itself"
      40      │╱╱╱              enough — a common reasoning model
              ╱╱                  issue due to excessive hedging
      20     ╱╱│
            ╱  │
       0   ╱   │───────────────────────────►
              0    20    40    60    80   100
```

## Expected Calibration Error (ECE) — Quantifies the Calibration Curve

```
  HOW ECE WORKS:

  1. Group all predictions into BINS by confidence level:

     Bin 1: 0-10%  │████│  15 predictions
     Bin 2: 10-20% │██████│  22 predictions
     Bin 3: 20-30% │████████│  30 predictions
     Bin 4: 30-40% │██████████│  35 predictions
     Bin 5: 40-50% │████████████│  42 predictions
     Bin 6: 50-60% │████████████│  40 predictions
     Bin 7: 60-70% │██████████│  33 predictions
     Bin 8: 70-80% │████████│  28 predictions
     Bin 9: 80-90% │██████│  20 predictions
     Bin10: 90-100%│████│  15 predictions

  2. For each bin, compute:
     - Average PREDICTED probability (what the model said)
     - Actual FREQUENCY of YES outcomes (what really happened)
     - The GAP between them

  3. ECE = weighted average of all gaps

  Example:
     Bin 7 (60-70%): Model predicted avg 65%, actual hit rate 58%
     Gap = |65% - 58%| = 7%
     Weight = 33/250 = 0.132

     ECE contribution from Bin 7 = 0.132 × 7% = 0.92%

  INTERPRETING ECE:
     0.00 - 0.02  Excellent calibration
     0.02 - 0.05  Good calibration
     0.05 - 0.10  Moderate calibration issues
     0.10 - 0.20  Poor calibration
     0.20+        Severely miscalibrated
```

## Reasoning Length vs. Accuracy — The "Sweet Spot" Hypothesis

```
  Expected pattern (based on DeepSeek-R1 research):

  Accuracy  ▲
  (%)       │
            │         ╭────────╮
   85       │        ╱          ╲
            │       ╱            ╲
   80       │      ╱              ╲
            │     ╱                ╲
   75       │    ╱                  ╲
            │   ╱         SWEET      ╲
   70       │  ╱          SPOT        ╲
            │ ╱                        ╲
   65       │╱                          ╲
            │                            ╲
   60       │                             ╲
            └──────────────────────────────────►
            100   500  1000  2000  5000  10000
                  Reasoning tokens used

            ◄─────►      ◄────────────────────►
           Too little    Too much ("overthinking")
           thinking       • introduces doubt
                          • tangential reasoning
                          • excessive hedging
                          • self-contradictions
```

## Cost-Adjusted Brier Score — Your Unique Contribution

```
  WHY THIS MATTERS:

  ┌────────────────────────────────────────────────────────┐
  │                                                        │
  │  Model          Brier    Cost/Query    Brier per $     │
  │  ────────       ─────    ──────────    ──────────      │
  │  o3             0.14     $0.15         0.93            │
  │  o4-mini        0.17     $0.02         8.50            │
  │  Claude Think   0.15     $0.08         1.88            │
  │  GPT-4.1        0.22     $0.03         7.33            │
  │  DeepSeek-R1    0.16     $0.01         16.00  ← BEST  │
  │                                        $/BRIER         │
  │                                                        │
  │  = Some models give much better bang-for-buck          │
  │    This matters for production forecasting systems     │
  │                                                        │
  └────────────────────────────────────────────────────────┘

  (Numbers above are HYPOTHETICAL — this is what you'll measure)
```
