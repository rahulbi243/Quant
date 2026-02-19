# Diagram 5: Failure Modes — What Goes Wrong and How Reasoning Might Fix It

## The Three Failure Modes (Identified by Lossfunk)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║  FAILURE MODE 1: RECENCY BIAS                                           ║
║                                                                         ║
║  What happens:                                                          ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Question: "Will the S&P 500 close below 5000 by June 2025?"   │     ║
║  │                                                                 │     ║
║  │  WITHOUT news:                                                  │     ║
║  │  Model: "Based on historical patterns, valuations seem          │     ║
║  │  stretched. I'll say 55% YES."  ← CORRECT                      │     ║
║  │                                                                 │     ║
║  │  WITH news:                                                     │     ║
║  │  News: "S&P 500 hits all-time high of 5,800!"                  │     ║
║  │  Model: "Markets are surging! Only 15% YES."  ← WRONG          │     ║
║  │                                                                 │     ║
║  │  The recent headline OVERRODE better prior reasoning.           │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
║  How reasoning MIGHT fix it:                                            ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Reasoning model's thinking trace:                              │     ║
║  │  "The news says S&P hit all-time highs. But wait —              │     ║
║  │   all-time highs are actually NORMAL in bull markets.           │     ║
║  │   The question is about a decline by June, which is             │     ║
║  │   6 months away. Markets can drop 15% in that time.            │     ║
║  │   I shouldn't anchor on the current headline.                   │     ║
║  │   Maintaining my estimate at 50% YES."                          │     ║
║  │                                          ↑                      │     ║
║  │                               SELF-CORRECTION                   │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝


╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║  FAILURE MODE 2: RUMOR OVERWEIGHTING (Rumor Anchoring)                  ║
║                                                                         ║
║  What happens:                                                          ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Question: "Will the US impose 25% tariffs on EU by March?"    │     ║
║  │                                                                 │     ║
║  │  News articles: "Trade officials are CONSIDERING new tariffs"  │     ║
║  │                  "Sources say tariffs are UNDER DISCUSSION"     │     ║
║  │                  "Tariff proposal COULD be announced"           │     ║
║  │                                                                 │     ║
║  │  Standard model reads "considering/discussion/could" as:       │     ║
║  │  "Tariffs are happening!" → 85% YES  ← WRONG                  │     ║
║  │                                                                 │     ║
║  │  The model treated SPECULATION as FACT.                        │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
║  How reasoning MIGHT fix it:                                            ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Reasoning model's thinking trace:                              │     ║
║  │  "Let me examine the evidence carefully.                        │     ║
║  │   - Article 1 says 'considering' — not decided                 │     ║
║  │   - Article 2 says 'under discussion' — still in talks         │     ║
║  │   - Article 3 says 'could be announced' — speculative          │     ║
║  │                                                                 │     ║
║  │   None of these confirm actual implementation.                  │     ║
║  │   Base rate: trade threats → actual tariffs is ~30-40%.        │     ║
║  │   I'll say 40% YES."                                           │     ║
║  │                              ↑                                  │     ║
║  │                   EVIDENCE EVALUATION                           │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝


╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                         ║
║  FAILURE MODE 3: DEFINITION DRIFT                                       ║
║                                                                         ║
║  What happens:                                                          ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Question: "Will MATS applications exceed 500 this year?"      │     ║
║  │  (MATS = ML Alignment Theory Scholars — an AI safety program)  │     ║
║  │                                                                 │     ║
║  │  News retrieval returns articles about:                        │     ║
║  │  • Mid-America Trucking Show (also called "MATS")              │     ║
║  │  • Floor mats industry report                                  │     ║
║  │  • MATS program at a university (different one)                │     ║
║  │                                                                 │     ║
║  │  Standard model: Confuses the trucking show with the AI        │     ║
║  │  program. Answers about attendance at a trucking convention.   │     ║
║  │                                                                 │     ║
║  │  The semantic GROUNDING shifted to a different meaning.        │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
║  How reasoning MIGHT fix it:                                            ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │  Reasoning model's thinking trace:                              │     ║
║  │  "The question mentions 'MATS applications.' Let me            │     ║
║  │   check what MATS refers to in context...                      │     ║
║  │                                                                 │     ║
║  │   The resolution criteria mention 'ML Alignment Theory         │     ║
║  │   Scholars.' So this is about an AI safety program.            │     ║
║  │                                                                 │     ║
║  │   The news articles about trucking shows are IRRELEVANT.       │     ║
║  │   I'll ignore those and focus on AI safety program data."      │     ║
║  │                                          ↑                      │     ║
║  │                              CONTEXT ANCHORING                  │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

## Summary: What You're Testing

```
┌──────────────────┬────────────────────────┬─────────────────────────┐
│ Failure Mode     │ Standard Model         │ Reasoning Model         │
│                  │ Behavior               │ Hypothesized Behavior   │
├──────────────────┼────────────────────────┼─────────────────────────┤
│                  │                        │                         │
│ Recency Bias     │ Anchors on latest      │ Notices recency, weighs │
│                  │ headline, overrides    │ against base rates,     │
│                  │ prior reasoning        │ SELF-CORRECTS           │
│                  │                        │                         │
├──────────────────┼────────────────────────┼─────────────────────────┤
│                  │                        │                         │
│ Rumor            │ Treats "considering"   │ Distinguishes confirmed │
│ Overweighting    │ as "confirmed",        │ vs speculative, applies │
│                  │ speculation = fact     │ EVIDENCE EVALUATION     │
│                  │                        │                         │
├──────────────────┼────────────────────────┼─────────────────────────┤
│                  │                        │                         │
│ Definition       │ Loses semantic         │ Checks resolution       │
│ Drift            │ grounding when terms   │ criteria, filters       │
│                  │ are ambiguous          │ IRRELEVANT context      │
│                  │                        │                         │
└──────────────────┴────────────────────────┴─────────────────────────┘

YOUR JOB: Verify whether reasoning models ACTUALLY do these things,
           or whether they fail in the same ways (or new ways).
```
