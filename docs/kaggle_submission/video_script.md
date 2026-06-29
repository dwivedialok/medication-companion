# Kaggle Demo Video Script (~4 minutes, English)

Upload the recorded video to YouTube (public or unlisted) and paste the URL into the Kaggle Writeup Media Gallery.

**Target length:** 3:45–4:15  
**Language:** English throughout (wider judge coverage; regional audio capability shown via language picker)  
**Recording:** 1080p screen capture + live microphone (OBS / QuickTime)  
**URL:** https://medication-companion-dev.web.app  
**Test image:** `data/sample/smoke_4drug_2interactions.png` (Ecosprin, Nise, Warf, Flagyl)

**Recording rule:** Do **not** navigate away from the analysis / loading screen while the pipeline runs — job polling is tied to that route. Architecture is **voiceover only** during the wait; full diagrams, eval scores, and Gherkin specs live in the [Kaggle writeup](WRITEUP.md).

---

## Scene 1 — Home & problem (0:00–0:30)

**On screen:**
1. Sign in with demo credentials.
2. Land on **Home** — pause on greeting card and disclaimer.
3. Open **Audio language** dropdown → briefly highlight all five: **English, Hindi, Tamil, Telugu, Bengali**.
4. Select **English** and leave it there.

**Voiceover:**
> In India, patients often visit multiple doctors. Every year, billions of prescriptions are dispensed, and most are written using brand names rather than generic drug names. Patients often visit multiple doctors over time — a cardiologist, a GP, a specialist, or even local clinics — and those prescriptions may not get reconciled together for any harmful drug interactions. Medication Companion reads prescription photos, resolves Indian brand names to generics, and checks drug interactions against your medication history. The app supports five regional languages; I'll stay in English so every judge can follow along.




---

## Scene 2 — Capture flow (0:30–0:50)

**On screen:**
1. Tap **Analyse prescription**.
2. On the upload screen, **tap Camera** (show the option exists).
3. Then tap **Gallery** and pick `smoke_4drug_2interactions.png`.
4. Confirm preview, tap submit to start analysis.

**Voiceover:**
> Patients can photograph a prescription or pick one from the gallery — useful when they already have a photo from WhatsApp or a clinic visit. I'm using a deterministic test prescription with four common Indian brands.

---

## Scene 3 — Processing + architecture voiceover (0:50–1:30)

**On screen:**
- **Stay on the loading screen** — do not switch tabs or open diagrams.
- Show the step labels: "Reading prescription…", "Checking interactions…", "Generating explanation…".

**Voiceover (fill the ~40s wait):**
> This porocessing involves multiple components and eventaully it reaches Agentic pipeline running on Google ADK.  There are Five specialized agents: Agent 1, the **Reader** does vision OCR and Gate 1 quality check; Agent 2 the **Resolver** maps brands like Ecosprin to aspirin using deterministic drug-lookup tools; then **Safety Agent** checks every drug pair and compares against Vertex AI Memory Bank from prior visits; 

**Education Agent** writes plain-language explanations; Finally **Localisation** translates and generates text-to-speech.
>
---

## Scene 4 — Results: severity, drugs, memory tags (1:30–2:05)

**On screen:**
1. Result screen loads — pause on **HIGH** severity banner.
2. Scroll **Medications found** — point at each card:
   - Brand name → generic (e.g. Ecosprin → aspirin)
   - **NEW** vs **EXISTING** badge on each row
3. Scroll **Interactions** — highlight severity chips; if any show **"Detected from your medication history"**, point at that.

**Voiceover:**
> The system found high-severity interactions. Each Indian brand is resolved to its generic name.
>
> Notice the **NEW** and **EXISTING** tags. **NEW** means this drug appeared for the first time on today's prescription. **EXISTING** means it was already in the patient's memory from a prior visit. On this demo account, earlier uploads have seeded memory — so you may see mostly EXISTING tags. That's intentional: it shows cross-visit safety, not just what's on today's paper.
>
> Interactions marked "from your medication history" are cross-visit findings — the core value of the product.

**If every drug shows EXISTING:** say explicitly that a first-time user would see all **NEW** on visit one; cross-visit interactions appear on later uploads.

---

## Scene 5 — Summary (2:05–2:20)

**On screen:** Scroll to **Summary** card; let the text be visible on screen (do not read it all aloud).

**Voiceover:**
> Agent 4 turns the clinical findings into a patient-friendly summary — no diagnosis, no dose advice, just what to be aware of and why it matters.

---

## Scene 6 — Audio playback (~30 sec) (2:20–2:50)

**On screen:** Tap **Play** on **Audio explanation**. Let it run ~30 seconds, then pause.

**Voiceover (before/during play):**
> Agent 5 generates spoken audio in the patient's chosen language — important for patients with low literacy. The consult-your-doctor disclaimer is preserved. I'll play the first thirty seconds.

**Tip:** Ensure system volume is audible in the recording.

---

## Scene 7 — Doctor questions + disclaimer (2:50–3:05)

**On screen:**
1. Scroll to **Questions for your doctor** — show 2–3 bullet points.
2. Scroll to bottom **disclaimer** ("discuss with your doctor or pharmacist").

**Voiceover:**
> The app also suggests concrete questions to ask your doctor — not medical orders, just conversation starters. Every output ends with a mandatory disclaimer: this is educational information, not a substitute for professional care.

---

## Scene 8 — Past prescriptions & Gate 1 reject (3:05–3:35)

**On screen:**
1. Tap **Back to home** → **Past prescriptions**.
2. Scroll the list — show a successful past analysis (severity chip) and a **Needs retake** entry.
3. Tap the Gate 1 reject → dialog **"Couldn't analyse this image"** → point at **Retake photo** (no need to retake live).

**Voiceover:**
> Every analysis is saved in history. Agent 1's Gate 1 rejects blurry or non-prescription images early — before wasting a full pipeline run — spec-defined refusal behaviour in `specs/safety_refusal.feature`. Here you can see a failed upload flagged as "needs retake." Good uploads show severity and drug count at a glance.

---

## Scene 9 — Close: eval, SDD, links (3:35–4:00)

**On screen:** End slide or stay on history/home. Optional: flash for 2 seconds each (after analysis is complete — safe to show static images):
- `media/eValCustomMetrics.jpg` — LLM-as-Judge 10/10 scores
- Screenshot of `specs/pipeline.feature` cross-visit scenario

**On screen (links):**
- GitHub: https://github.com/3amwave/medication-companion
- Live demo: https://medication-companion-dev.web.app
- Kaggle notebook: *(paste URL after publishing)*
- Demo login: kaggle-demo@medication-companion.dev

**Voiceover:**
> This is spec-driven and eval-gated production code — Gherkin scenarios and YAML schemas define behaviour before implementation; LLM-as-Judge scores drug safety and patient clarity asynchronously to BigQuery — ten out of ten on our smoke fixture. Forty-plus automated tests run in CI. Full architecture, eval metrics, Gherkin scenarios, and the runnable notebook are in the Kaggle writeup. MIT licensed on GitHub. Thank you.

---

## What the writeup covers (mention in video, prove in writeup)

| Topic | Writeup / repo reference |
|-------|--------------------------|
| Architecture diagram | `media/architecture_diagram.md` → export PNG via mermaid.live |
| Agent pipeline visual | `media/06_agent_pipeline_flow.png` |
| LLM-as-Judge eval | `WRITEUP.md` § Evaluation; `media/eValCustomMetrics.jpg` |
| Spec-driven development | `specs/pipeline.feature`, `specs/safety_refusal.feature`, YAML schemas |
| Cross-visit BDD scenario | `specs/pipeline.feature` — warfarin in memory + new aspirin → HIGH |
| Course day mapping | `media/README.md` |

---

## Pre-recording checklist

- [ ] Demo account works (`scripts/test_prescription.py` against dev URL)
- [ ] Past prescriptions list includes at least one Gate 1 **Needs retake** entry
- [ ] Incognito or cleared cache; notifications off
- [ ] **English** selected on home screen before upload
- [ ] `smoke_4drug_2interactions.png` in an easy Gallery folder (or desktop for drag-and-drop)
- [ ] Audio play tested once (volume audible in recording)
- [ ] Optional end-slide assets ready: `eValCustomMetrics.jpg`, `pipeline.feature` screenshot

## Post-recording

1. Upload to YouTube (public or unlisted).
2. Paste URL into `docs/kaggle_submission/SUBMISSION.md` → Video URL field.
3. Attach to Kaggle Media Gallery.

## Optional post-production (not required)

- Picture-in-picture `06_agent_pipeline_flow.png` over the Scene 3 spinner recording (adds a visual without leaving the live page during recording).
- Trim dead air to stay under 4:15.
