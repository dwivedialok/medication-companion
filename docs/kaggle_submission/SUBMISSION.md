# Kaggle submission — final checklist

Complete these steps in the Kaggle Writeup editor. All content is prepared in this repo.

## Writeup fields

| Field | Value |
|-------|-------|
| **Title** | Medication Companion — Cross-Visit Prescription Safety for Patients in India |
| **Subtitle** | A five-agent Google ADK pipeline that reads prescriptions, resolves Indian brand names, checks drug interactions across doctor visits, and explains findings in regional languages with audio. |
| **Track** | Agents for Good |
| **Project Link** | https://github.com/dwivedialok/medication-companion |
| **Body** | Copy from [`WRITEUP.md`](WRITEUP.md) (paste into Kaggle editor; verify ≤2,500 words) |

## Media Gallery (required)

Upload from [`media/`](media/):

1. **Cover image (required):** `00_cover_image.png`
2. **Video (required):** YouTube URL — record using [`video_script.md`](video_script.md), then paste URL here:

   ```
   VIDEO_URL: __PASTE_AFTER_RECORDING__
   ```

3. **Additional images (recommended — see `media/README.md` for day mapping):**
   - `06_agent_pipeline_flow.png` — **Agent 1→5 pipeline** (Day 1)
   - `01_smoke_prescription.png` — test prescription input
   - `05_result_screen_en.png` — English result screen
   - `04_cover_result_hi.png` — Hindi result + audio (Day 5 / accessibility)
   - `eValCustomMetrics.jpg` — LLM-as-Judge 10/10 scores (Day 4)
   - Optional: architecture diagram PNG from `architecture_diagram.md` via mermaid.live (Day 5)

## Links to include in writeup body

| Resource | URL |
|----------|-----|
| GitHub (primary Project Link) | https://github.com/dwivedialok/medication-companion |
| Kaggle notebook | `__PASTE_AFTER_PUBLISHING__` — follow [`publish_notebook.md`](publish_notebook.md) |
| Live PWA | https://medication-companion-dev.web.app |

## Demo account (live PWA)

Verified E2E on 2026-06-24 against dev deployment:

```
Email:    kaggle-demo@medication-companion.dev
Password: KaggleDemo2026!MC
```

**Test steps:**
1. Sign in at https://medication-companion-dev.web.app
2. Select **Hindi** on home screen
3. Upload `data/sample/smoke_4drug_2interactions.png`
4. Expect **HIGH** severity, 3 interactions, Hindi summary + audio

## Pre-submit verification

- [ ] Writeup body ≤2,500 words
- [ ] Track = **Agents for Good**
- [ ] Cover image attached
- [ ] YouTube video attached (≤5 min)
- [ ] GitHub set as Project Link
- [ ] Notebook URL pasted in writeup (after publishing)
- [ ] Demo credentials in writeup
- [ ] Disclaimer visible in first sections
- [ ] Click **Submit** (draft writeups do not count)

## Quick commands

```bash
# Offline smoke check
uv run python scripts/verify_smoke_fixture.py

# Regenerate HTML mockups / screenshots
uv run python scripts/generate_kaggle_screenshots.py
# Open http://localhost:8765/03_result_screen_hi.html for manual screenshot

# Word count
wc -w docs/kaggle_submission/WRITEUP.md
```

## File index

| File | Purpose |
|------|---------|
| `WRITEUP.md` | Full writeup draft for Kaggle editor |
| `video_script.md` | 5-minute YouTube recording script |
| `publish_notebook.md` | Steps to publish demo notebook on Kaggle |
| `media/00_cover_image.png` | Required cover image |
| `media/06_agent_pipeline_flow.png` | Agent 1→5 SequentialAgent pipeline |
| `media/06_agent_pipeline_flow.html` | Source HTML to regenerate pipeline PNG |
| `media/01_smoke_prescription.png` | Gallery: test Rx |
| `media/04_cover_result_hi.png` | Gallery: Hindi results |
| `media/05_result_screen_en.png` | Gallery: English results |
| `media/eValCustomMetrics.jpg` | Gallery: LLM-as-Judge eval (Day 4) |
| `media/README.md` | Full image guide + day-by-day checklist |
