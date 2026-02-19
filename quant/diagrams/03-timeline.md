# Diagram 3: 10-Day Timeline

## Visual Timeline

```
Feb 18                                                              Feb 27
  │                                                                    │
  ▼                                                                    ▼

  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
  │ D1  │ D2  │ D3  │ D4  │ D5  │ D6  │ D7  │ D8  │ D9  │ D10 │
  │     │     │     │     │     │     │     │     │     │     │
  │SETUP│DATA │BUILD│ RUN │ RUN │QUANT│QUAL │WRITE│CLEAN│APPLY│
  │     │     │     │STD  │REAS │ANLY │ANLY │ UP  │ +OS │     │
  │     │     │     │     │     │     │     │     │     │     │
  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘

  ◄──── FOUNDATION ────►◄── EXPERIMENTS ──►◄ ANALYSIS ►◄─ OUTPUT ─►
       (3 days)              (2 days)       (2 days)    (3 days)
```

## Phase Breakdown

```
╔═══════════════════════════════════════════════════════════════════╗
║  PHASE 1: FOUNDATION (Days 1-3)                                  ║
║                                                                   ║
║  Day 1: Read papers + Setup repo                                 ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Read "Future Is Unevenly Distributed" end-to-end      │   ║
║  │     Read "Think Just Enough"                               │   ║
║  │     Read "Your LLM is a Confused Oracle" blog post         │   ║
║  │ PM: Initialize GitHub repo (PUBLIC from day 1)             │   ║
║  │     Get API keys (OpenAI, Anthropic, DeepSeek, Google)     │   ║
║  │     Define data schemas                                    │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 2: Collect & clean dataset                                  ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Write scrapers (Polymarket, Metaculus, Manifold)       │   ║
║  │     Pull 500+ resolved binary questions                    │   ║
║  │ PM: Filter → 200-300 questions                             │   ║
║  │     Categorize into 6 domains                              │   ║
║  │     Collect news snippets for Condition B                  │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 3: Build evaluation harness + validate baseline             ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Build evaluate(model, question, condition) function    │   ║
║  │     Implement 3 prompt templates                           │   ║
║  │     Implement Brier, ECE, accuracy calculators             │   ║
║  │ PM: Validate on 20 questions vs Lossfunk's numbers         │   ║
║  │     Debug any discrepancies                                │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Deliverables: Repo, dataset, working harness, validated baseline ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║  PHASE 2: EXPERIMENTS (Days 4-5)                                 ║
║                                                                   ║
║  Day 4: Standard models                                          ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ Claude 3.7 × 3 conditions × 250 Qs  = ~750 calls          │   ║
║  │ GPT-4.1    × 3 conditions × 250 Qs  = ~750 calls          │   ║
║  │ DeepSeek-V3× 3 conditions × 250 Qs  = ~750 calls          │   ║
║  │ ──────────────────────────────────────────────             │   ║
║  │ Total: ~2,250 API calls                                    │   ║
║  │ Store all raw responses                                    │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 5: Reasoning models                                         ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ Claude Think × 3 conditions × 250 Qs = ~750 calls         │   ║
║  │ o3          × 3 conditions × 250 Qs  = ~750 calls         │   ║
║  │ o4-mini     × 3 conditions × 250 Qs  = ~750 calls         │   ║
║  │ DeepSeek-R1 × 3 conditions × 250 Qs  = ~750 calls         │   ║
║  │ Gemini 2.5  × 3 conditions × 250 Qs  = ~750 calls         │   ║
║  │ ──────────────────────────────────────────────             │   ║
║  │ Total: ~3,750 API calls                                    │   ║
║  │ STORE FULL REASONING TRACES (critical!)                    │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Deliverables: ~6,000 predictions with metadata + traces          ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║  PHASE 3: ANALYSIS (Days 6-7)                                    ║
║                                                                   ║
║  Day 6: Quantitative                                             ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Compute Brier, ECE, accuracy per model×condition×domain│   ║
║  │     Build comparison tables                                │   ║
║  │ PM: Statistical tests (paired t-test, bootstrap CIs)       │   ║
║  │     Test H1-H5 against data                                │   ║
║  │     Identify outliers and surprises                        │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 7: Qualitative + Visualizations                             ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Classify 50 reasoning traces by strategy type          │   ║
║  │     Count failure modes: standard vs reasoning             │   ║
║  │ PM: Generate all charts:                                   │   ║
║  │     • Calibration curves     • Brier heatmaps             │   ║
║  │     • Reasoning length plots • Strategy distributions      │   ║
║  │     Document 5-10 case studies                             │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Deliverables: Metrics, stats, figures, case studies              ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║  PHASE 4: OUTPUT (Days 8-10)                                     ║
║                                                                   ║
║  Day 8: Write research note                                      ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ 3-5 page technical note:                                   │   ║
║  │ Abstract → Method → Results → Case Studies → Open Questions│   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 9: Clean code + open-source                                 ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ Docstrings, README, requirements.txt, Makefile             │   ║
║  │ Verify clone→install→run→results works from scratch        │   ║
║  │ Push to GitHub                                             │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Day 10: APPLY                                                   ║
║  ┌────────────────────────────────────────────────────────────┐   ║
║  │ AM: Draft application                                      │   ║
║  │     Link: repo + research note + 6-week proposal           │   ║
║  │ PM: Review, edit, submit                                   │   ║
║  │     Optional: DM Paras with 2-sentence summary             │   ║
║  └────────────────────────────────────────────────────────────┘   ║
║                                                                   ║
║  Deliverables: Research note, clean repo, submitted application   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Critical Path (What Can't Slip)

```
   Day 2 (Dataset)  ──BLOCKS──►  Day 4-5 (Experiments)
   Day 3 (Harness)  ──BLOCKS──►  Day 4-5 (Experiments)
   Day 4-5 (Expts)  ──BLOCKS──►  Day 6-7 (Analysis)
   Day 6-7 (Analysis)──BLOCKS──► Day 8 (Write-up)

   ⚠️  If Day 2 or 3 slips → everything slips
   ⚠️  Days 8-9 CAN be compressed to 1 day in emergency
   ⚠️  Day 10 (apply) is non-negotiable
```
