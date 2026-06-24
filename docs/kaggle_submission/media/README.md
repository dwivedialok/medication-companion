# Kaggle Media Gallery — image guide

Recommended images for the Kaggle Writeup Media Gallery, mapped to course days and judging criteria.

## Required (Kaggle rules)

| File | Purpose |
|------|---------|
| `00_cover_image.png` | **Cover image** — Hindi result screen with HIGH severity |
| YouTube video (≤5 min) | Live demo walkthrough |

## Core gallery (upload all)

| File | Course day | What it shows |
|------|------------|---------------|
| `06_agent_pipeline_flow.png` | **Day 1** | Five-agent SequentialAgent flow (Reader → Resolver → Safety → Education → Localisation) |
| `01_smoke_prescription.png` | Demo | Deterministic test Rx (Ecosprin, Nise, Warf, Flagyl) |
| `04_cover_result_hi.png` | **Day 5** / Agents for Good | Hindi result + audio — accessibility |
| `05_result_screen_en.png` | Demo | English result with interaction cards |
| `eValCustomMetrics.jpg` | **Day 4** | LLM-as-Judge scores: `drug_safety_score` 10/10, `patient_clarity_score` 10/10 |

## Optional (strong additions)

| Asset | Course day | How to create |
|-------|------------|---------------|
| `architecture_diagram.md` → export PNG | **Day 5** | Full system: PWA → Auth Broker → Agent Runtime → GCS/Memory/BigQuery. Export via [mermaid.live](https://mermaid.live) |
| Kaggle notebook screenshot | **Day 2–3** | Screenshot of notebook cells 4–6 running (drug_lookup + memory demo) |
| Gate 1 reject screenshot | **Day 1** | Upload blurry image in PWA → retake message |
| `specs/pipeline.feature` screenshot | **Day 5** | Spec-driven development — Gherkin cross-visit scenario |
| Login / language selector screenshot | Demo | Flutter home screen with 5-language picker |

## Day-by-day coverage checklist

| Day | Topic | Best image |
|-----|-------|------------|
| **Day 1** | Agents & autonomous decisions | `06_agent_pipeline_flow.png` (+ optional Gate 1 reject) |
| **Day 2** | Tools & FunctionTools | Pipeline diagram (Resolver tools) or notebook `drug_lookup` output |
| **Day 3** | Memory & cross-visit safety | Result screen showing interactions + writeup cross-visit narrative |
| **Day 4** | Quality & LLM-as-Judge | **`eValCustomMetrics.jpg`** |
| **Day 5** | Spec-driven production | Architecture diagram PNG or CI/deploy mention in writeup |

## Should you include `eValCustomMetrics.jpg`?

**Yes — strongly recommended.** It is the clearest visual proof of Day 4 (LLM-as-Judge). The screenshot shows:

- Perfect `drug_safety_score` (10/10) — faithful interaction reproduction, correct brand→generic mapping, combo_splitter noted
- Perfect `patient_clarity_score` (10/10) — plain language, doctor questions, mandatory consult redirect

Judges evaluating "implementation quality" and "effective use of agent technologies" respond well to measurable eval output, not just architecture diagrams.

## Regenerate pipeline diagram

```bash
# Edit 06_agent_pipeline_flow.html if needed, then:
python3 -m http.server 8766 --directory docs/kaggle_submission/media
# Open http://localhost:8766/06_agent_pipeline_flow.html and screenshot
```

Or open `06_agent_pipeline_flow.html` in a browser and save as PNG.

## Suggested upload order in Kaggle editor

1. `00_cover_image.png` (cover)
2. `06_agent_pipeline_flow.png` (architecture story)
3. `01_smoke_prescription.png` (input)
4. `05_result_screen_en.png` + `04_cover_result_hi.png` (output)
5. `eValCustomMetrics.jpg` (quality flywheel)
6. Video URL
