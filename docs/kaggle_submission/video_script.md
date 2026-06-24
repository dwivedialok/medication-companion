# Kaggle Demo Video Script (≤5 minutes)

Upload the recorded video to YouTube (public or unlisted) and paste the URL into the Kaggle Writeup Media Gallery.

**Target length:** 4:30–5:00  
**Recording:** 1080p screen capture + voiceover  
**Demo account:** `kaggle-demo@medication-companion.dev` / `KaggleDemo2026!MC`  
**Test image:** `data/sample/smoke_4drug_2interactions.png` (Ecosprin, Nise, Warf, Flagyl)

---

## Scene 1 — Hook (0:00–0:30)

**Visual:** Title slide or talking head.

**Script:**
> In India, patients often see multiple doctors. Doctor A prescribed warfarin last month. Doctor B just prescribed aspirin. Neither prescription looks dangerous on its own — but together they create a serious bleeding risk. Medication Companion is a five-agent AI system that reads your prescription, resolves Indian brand names, and checks drug interactions across visits — then explains the findings in your language with audio.

**On screen:** Simple diagram: Visit 1 (warfarin) + Visit 2 (aspirin) → HIGH interaction.

---

## Scene 2 — Architecture (0:30–1:00)

**Visual:** Architecture diagram from `docs/kaggle_submission/media/architecture_diagram.md` or slide.

**Script:**
> The pipeline runs on Google ADK as five specialized agents: Reader, Resolver, Safety, Education, and Localisation. Deterministic tools ground drug lookup and interaction checking. Vertex AI Memory Bank stores only generic drug names from prior visits — never prescription images. A Flutter PWA talks to a private Agent Runtime through an auth broker.

---

## Scene 3 — Live demo (1:00–2:30)

**Visual:** Browser at https://medication-companion-dev.web.app

**Steps:**
1. Sign in with demo credentials.
2. Select **Hindi** on the home screen.
3. Tap **Analyse prescription** → upload `smoke_4drug_2interactions.png`.
4. Wait for pipeline (~30–45 seconds).
5. Scroll through the result screen:
   - HIGH severity banner
   - Four resolved drugs (Ecosprin → aspirin, etc.)
   - Three HIGH interaction cards
   - Doctor questions in Hindi
   - Disclaimer at bottom

**Script:**
> I'll upload a test prescription with four common Indian brands. The system resolves each brand to its generic name, then checks all drug pairs. It found three high-severity interactions — including aspirin with warfarin and metronidazole with warfarin. The explanation is in plain Hindi, with specific questions to ask your doctor.

---

## Scene 4 — Audio playback (2:30–3:15)

**Visual:** Tap the audio play button on the result screen.

**Script:**
> For patients who struggle with reading, Agent 5 generates text-to-speech audio in the patient's chosen language. The medical meaning and the consult-your-doctor disclaimer are preserved in translation.

**Tip:** Ensure volume is audible in the recording.

---

## Scene 5 — Cross-visit story (3:15–4:00)

**Option A (live):** Sign in as a fresh user or explain seeded memory:
1. First upload a warfarin-only prescription (or mention prior visit in voiceover).
2. Second upload Ecosprin-only → show EXISTING warfarin + NEW aspirin → cross_visit source.

**Option B (voiceover only):** Use the BDD scenario from `specs/pipeline.feature`:
> When memory contains warfarin from a prior visit and today's prescription adds aspirin, Agent 3 flags a HIGH cross-visit interaction. This is the core value — safety that only emerges when today's drugs meet your history.

---

## Scene 6 — Responsible AI (4:00–4:30)

**Visual:** Text slide or scroll to disclaimer.

**Script:**
> This is an educational prototype, not a medical device. The system never diagnoses, never suggests dose changes, and never substitutes over-the-counter advice. Every output ends with "Please discuss this with your doctor or pharmacist." Memory stores only resolved generic names — not prescription images or clinical notes.

---

## Scene 7 — Call to action (4:30–5:00)

**Visual:** Links slide.

**On screen:**
- GitHub: https://github.com/3amwave/medication-companion
- Kaggle notebook: *(paste URL after publishing)*
- Live demo: https://medication-companion-dev.web.app
- Demo login: kaggle-demo@medication-companion.dev

**Script:**
> Full source code, a runnable Kaggle notebook, and a live demo are linked in the writeup. MIT licensed. Thank you.

---

## Pre-recording checklist

- [ ] Demo account works (run `scripts/test_prescription.py` against dev URL)
- [ ] Browser cache cleared or use incognito
- [ ] Hindi language selected before upload
- [ ] Smoke PNG ready on desktop for drag-and-drop
- [ ] Close unrelated tabs and notifications
- [ ] Test audio playback once before recording

## Post-recording

1. Upload to YouTube.
2. Paste URL into `docs/kaggle_submission/SUBMISSION.md` → Video URL field.
3. Attach to Kaggle Media Gallery.
