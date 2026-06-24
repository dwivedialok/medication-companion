# Medication Companion — Cross-Visit Prescription Safety for Patients in India

**Subtitle:** A five-agent Google ADK pipeline that reads prescriptions, resolves Indian brand names, checks drug interactions across doctor visits, and explains findings in regional languages with audio.

**Track:** Agents for Good

> **Disclaimer:** Medication Companion is an educational prototype, not a medical device. It is not a substitute for professional medical advice, diagnosis, or treatment. Every output directs the patient back to their doctor or pharmacist.

---

## The problem

In India, patients commonly receive prescriptions written in **brand names** (Ecosprin, Nise, Pantocid DSR) rather than generic chemical names. They often visit **multiple doctors** across time — a cardiologist, a general physician, a specialist — each unaware of what the others prescribed. A medicine that is reasonable in isolation can become dangerous in combination with something from a prior visit, if not correctly communicated to Doctor/Pharmacist. This can happen more with old and less educated people. 

Consider a patient who was prescribed **warfarin** after a first visit. At a second visit, a different doctor prescribes **aspirin** (brand: Ecosprin). Neither prescription looks alarming on its own. The bleeding risk appears only when **today's drugs meet the patient's medication history**. Language and literacy barriers make this worse: written English explanations are inaccessible to many patients, and pharmacists are not always available for consultation.

A single LLM chatbot cannot solve this safely. The task requires **vision** (reading handwritten prescriptions), **India-specific drug resolution** (brands, fixed-dose combinations, OCR noise), **long-term memory** (cross-visit reconciliation), **deterministic interaction checking** (grounded, not hallucinated), **policy guardrails** (no diagnosis or dosing advice), and **multilingual audio output**. That is why we built a multi-agent system.

---

## What Medication Companion does

A patient photographs their prescription using a Flutter progressive web app. The system:

Agent 1. **Reads** the image with Gemini Vision and rejects unreadable photos (Gate 1 confidence threshold 0.75)
Agent 2. **Resolves** each brand to its generic name; for fixed-dose combinations (FDC), decomposes combo brands into their active ingredients via `combo_splitter`
Agent 3. **Checks safety** — all drug pairs within the visit **and** new drugs against prior visits stored in memory
Agent 4. **Explains** findings in plain language, tone calibrated to severity (HIGH = urgent-but-calm)
Agent 5. **Localises** the explanation into Hindi, Tamil, Telugu, Bengali, or English (India) and generates **text-to-speech audio**

Every patient-facing string ends with: *"Please discuss this with your doctor or pharmacist before making any changes."*

---

## Architecture

```
┌────────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
│ Flutter PWA            │     │ Auth Broker            │     │ Pub/Sub                │     │ Prescription Worker    │
│ Firebase Hosting       │────►│ public · JWT verify    │────►│ prescription-jobs      │────►│ private · runs pipeline│
│ Upload · History · UI  │     │ 202 job · History APIs │     │ async queue            │     │ Agent Runtime A1→A5    │
└───────────┬────────────┘     └───────────┬────────────┘     └────────────────────────┘     └───────────┬────────────┘
            │                              │                                                              │
            │ signed PUT/GET               │ read/write jobs                                              │
            ▼                              ▼                                                              ▼
┌────────────────────────┐     ┌────────────────────────┐                                  ┌────────────────────────┐
│ GCS                    │     │ Firestore              │                                  │ Vertex AI Memory Bank  │
│ images · TTS MP3       │     │ jobs (status + result) │                                  │ BigQuery eval_log      │
└────────────────────────┘     └────────────────────────┘                                  └────────────────────────┘

```


The auth broker is the only public HTTP surface: JWT verify, `patient_id` from UID, `POST /prescription` → **202 + job_id** via Pub/Sub. A private worker runs the pipeline on Agent Runtime; job status and History live in Firestore. Five agents run in strict order via `SequentialAgent` in `backend/agent.py`:

| Agent | Responsibility | Key tool |
|-------|----------------|----------|
| 1 — Reader | Vision OCR, image classification, Gate 1 | — |
| 2 — Resolver | Brand → generic, FDC split, NEW/EXISTING tags | `drug_lookup`, `combo_splitter` |
| 3 — Safety | Current × current and current × prior interactions | `check_prescription_interactions` |
| 4 — Education | Drug cards, interaction cards, doctor questions | — |
| 5 — Localisation | Translation + GCP Text-to-Speech | `text_to_speech` |

**India drug index:** At build time, `scripts/build_drug_index.py` fuses Kaggle CSVs plus `india_brands.csv` into `drugs.db` (~54 MB). At runtime, `drug_lookup.py` resolves brands through six tiers (first hit wins): live `india_brands.csv` (~300 curated rows), SQLite exact match, FTS5 prefix, RapidFuzz fuzzy (≥80 score, OCR folding `0→o`, `1→l`, `5→s`, `8→b`), RxNav REST API (skipped when `ENVIRONMENT=local`), then **UNRESOLVED**. Agent 2 tags unresolved brands; it never guesses.

**Fixed-dose combinations (FDC):** Indian prescriptions frequently use combo brands — one trade name, multiple actives in a single tablet (e.g. **Pantocid DSR** = pantoprazole + domperidone; **Augmentin** = amoxicillin + clavulanate). Interaction checking operates on **generic chemical names**, not brand labels, so Agent 2 must expose what is inside each combo. The `combo_splitter` FunctionTool (`backend/tools/combo_splitter.py`) decomposes a known FDC into its components and doses, reading from `india_brands.csv` or the `brand_components` table in `drugs.db`. Agent 2 also calls `drug_lookup`, which returns a combined generic string (e.g. `pantoprazole+domperidone`) and often a `components` list for the same brand. Both tools feed a structured `ResolvedDrug` record — brand name, combined generic, component list, NEW/EXISTING/UNRESOLVED tag — that Agent 4 uses for plain-language drug cards. Agent 3's deterministic safety check pairs on the resolved `generic_name` field today; per-component expansion into separate interaction pairs is planned for the LanceDB resolver upgrade (`docs/drug_lookup_tool_v2.md`).

Each agent uses ADK `LlmAgent` with a Pydantic `output_schema` — structured JSON between agents, never free-form prose passed downstream. ADK callbacks handle cross-cutting concerns without bloating agent instructions: OCR allowlist filtering after Agent 1, memory preload before Agent 2, resolver-to-safety state sync before Agent 3, policy output gate + memory persistence + async LLM-as-Judge after Agent 5.

**Memory privacy:** Vertex AI Memory Bank stores only resolved generic names, visit timestamp, and severity summary — never prescription images, raw LLM output, or clinical notes (`specs/schemas/medication_history.yaml`). Semantic retrieval uses drug-name queries with a broad fallback so disjoint prior visits still surface relevant history.

**Policy gates:** A hybrid policy server runs on ADK callbacks — structural image intake (non-prescription, overlay injection on prescription photos) and semantic output checks (no diagnostic language, no dosing advice, no OTC substitution, no cross-patient data leaks). Specified in `specs/safety_refusal.feature` and enforced in `backend/policy/policy_server.py`.

---

## Agents for Good — why this matters

**Cross-visit safety:** Agent 3 compares today's prescription against the full medication history. A BDD scenario in `specs/pipeline.feature` tests warfarin in memory plus new aspirin → HIGH severity with `cross_visit` source. This is the core patient-safety value that single-visit tools miss.

**Accessibility:** Five Indian languages plus GCP Text-to-Speech serve patients who cannot read English. Severity-calibrated tone comes from `specs/schemas/language_map.yaml`.

**Responsible AI:** The system never diagnoses ("you have…"), never suggests dose changes, and never recommends OTC substitutes. A dedicated policy server (`backend/policy/policy_server.py`) enforces scope at the callback layer, not just in prompts.

**Grounded interactions:** All drug pairs are checked deterministically against SQLite (`interaction_lookup`) before the LLM formats the output. Agent 3 calls `check_prescription_interactions`, which builds every unique pair (within-visit and cross-visit), queries the interactions table, and returns severity tagged `HIGH`, `MODERATE`, `LOW`, `INFO`, or `NONE`. The education agent copies tool output faithfully — eval scores of 10/10 on `drug_safety_score` confirm no omitted or invented interactions on the smoke fixture.

**Privacy by design:** Memory stores generics only. Images upload to GCS via signed URLs scoped to the authenticated patient; they are processed by Agent 1's Gemini Vision call but never persisted to Memory Bank. `patient_id` always comes from the verified Firebase UID.

**Honest uncertainty:** Unresolved brands (e.g., `Xyzol999` in BDD tests) are surfaced to the patient with tag `UNRESOLVED` rather than hallucinated into fake generics — preventing false interaction warnings on invented drug names.

**Honest limitations:** This is a proof-of-concept, not clinically validated software. We do not integrate DrugBank or OpenFDA, provide dose advice, offer refill reminders, or build a doctor dashboard. Interaction data comes from a curated SQLite matrix plus LLM fallback at `INFO` severity when no database row exists. See `docs/out_of_scope.md` for the full boundary list — judges appreciate clear scope.

---

## Course alignment (Days 1–5)

**Day 1 — Agents & Vibe Coding:** The fundamental agentic insight is autonomous branching. Agent 1 (`agent1_reader.py`) evaluates OCR confidence per drug name and halts the pipeline with `Gate1Reject` if any name scores below 0.75 — not a post-hoc filter, but a decision that stops garbage from reaching the resolver. The multi-agent pipeline itself is the Day 1 argument: Agent 3's cross-visit check requires memory retrieval that no single LLM call can perform in one shot. The project was spec-written in natural language (`docs/medication_companion_technical_requirements.md`) and generated with Cursor using `.cursor/rules/medication-companion.mdc` as machine-readable governance — the vibe coding workflow at scale.

**Day 2 — Tools & Interoperability:** Agent 2 (`agent2_resolver.py`) registers `FunctionTool`s for `drug_lookup` (brand → generic, six-tier index) and `combo_splitter` (FDC → component list with doses). The agent autonomously decides when to call each tool — monotherapy brands need lookup only; combo brands such as Pantocid DSR trigger both lookup and split. Agent 3 calls `check_prescription_interactions`, returning structured severity the LLM must not override. Agent 5 calls `text_to_speech`, uploading MP3 to GCS and returning a 24-hour signed URL. We explored deploying Agent 5 as a separate A2A Cloud Run service (archived under `deploy/legacy_cloud_run/`) but ship in-process in the SequentialAgent for simpler deployment and fewer moving parts (`deployment_metadata.json`: `is_a2a: false`).

**Day 3 — Context Engineering & Memory:** Short-term session state (`VertexAiSessionService` / local `InMemorySessionService`) carries Agent 2's resolved drug list to Agent 3 without re-processing. Long-term memory (`VertexAiMemoryBankService`) stores each visit's generics so Agent 2 can tag drugs `NEW` or `EXISTING` and Agent 3 can run NEW-vs-EXISTING interaction scans. After a successful run, `persist_visit_to_memory` in the root `after_agent_callback` writes the visit. This memory layer is what makes cross-doctor safety possible — the architectural reason this had to be an agent system, not a chatbot.

**Day 4 — Agent Quality:** The hybrid policy server replaces legacy regex guardrails with structural + semantic gates on ADK callbacks. LLM-as-Judge (`backend/evaluation/llm_judge.py`) fires asynchronously via `asyncio.create_task` after the root callback — scoring `drug_safety_score` (interaction completeness, no diagnostic claims) and `patient_clarity_score` (plain language, mandatory consult redirect) to BigQuery `eval_log` without blocking the patient response. Forty-six unit and integration test files cover Gate 1 rejection, interaction severity, memory shape, policy allow/deny, TTS voice mapping, and auth broker JWT flow. Drug lookup quality is gated by `backend/evaluation/drug_lookup_eval.py` on curated brands and OCR-noise inputs.

**Day 5 — Spec-Driven Production:** Gherkin scenarios in `specs/pipeline.feature` and `specs/safety_refusal.feature` define expected behaviour before code. YAML schemas (`agent_boundaries.yaml`, `medication_history.yaml`, `evaluation_metrics.yaml`) are the contract between spec and implementation. The pipeline deploys to Vertex AI Agent Runtime via `agents-cli deploy`; the auth broker on Cloud Run is the only public HTTP entry point (Firebase Hosting rewrites). CI in `.github/workflows/staging.yaml` deploys Agent Runtime, auth broker, and Firebase Hosting on every push to main. Cloud Trace instruments each agent span; structured JSON logging replaces print statements per project conventions (`AGENTS.md`).

---

## Evaluation and demo

**Deterministic smoke fixture:** `data/sample/smoke_4drug_2interactions.png` lists Ecosprin (aspirin), Nise (nimesulide), Warf (warfarin), and Flagyl (metronidazole) — four curated Indian brands with **three known HIGH interactions** in `drugs.db`: aspirin+nimesulide, aspirin+warfarin, metronidazole+warfarin. Six within-visit pairs are checked (C(4,2)). Offline verification: `uv run python scripts/verify_smoke_fixture.py`. Cloud E2E against the dev PWA returns HTTP 200 with Hindi translation and a signed TTS audio URL in ~40 seconds.

**LLM-as-Judge:** On the smoke fixture, `drug_safety_score` = 10.0 and `patient_clarity_score` = 10.0 (June 2026 eval run in `artifacts/grade_results/`). The judge confirmed all tool-identified interactions were faithfully reproduced with no diagnostic language. Translation accuracy and tone calibration metrics are planned in `specs/schemas/evaluation_metrics.yaml` for future deploy regression tracking.

**Flutter frontend:** Login (Firebase email/password), home screen with five-language selector, upload with sync/async pipeline support, and result screen with severity banner, medication cards (NEW/EXISTING/UNRESOLVED tags), interaction cards, localized summary, audio player, doctor questions, and mandatory disclaimer.

### Try it yourself

| Channel | URL | Notes |
|---------|-----|-------|
| **GitHub (Project Link)** | https://github.com/3amwave/medication-companion | Full source, MIT license, local quick start |
| **Kaggle notebook** | *(paste URL after publishing — see `docs/kaggle_submission/publish_notebook.md`)* | Runs all 5 agents with `InMemorySessionService`; add `GEMINI_API_KEY` secret |
| **Live PWA** | https://medication-companion-dev.web.app | Demo account below |

**Demo credentials:**
```
Email:    kaggle-demo@medication-companion.dev
Password: KaggleDemo2026!MC
```
Upload `data/sample/smoke_4drug_2interactions.png`, select Hindi or Tamil, and play the audio on the result screen.

**Video walkthrough:** *(paste YouTube URL after recording — script in `docs/kaggle_submission/video_script.md`)*

---

## Future work

Post-capstone backlog (`docs/BACKLOG.md`): expand FDC handling so Agent 3 checks interactions per component generic (not only the combined `generic_name` string), LanceDB semantic resolver (`docs/drug_lookup_tool_v2.md`), bind GCS upload URIs to authenticated patients (security hardening before public launch), migrate `SequentialAgent` to the graph-based ADK `Workflow` API, integrate a clinical interaction database (DrugBank/OpenFDA), add Pub/Sub async prescription processing with Firestore job polling (partially wired in auth broker), and optional chat Q&A extension gated behind `FEATURE_QA_ENABLED` with the same policy server refusals.

---

## Closing

Medication Companion demonstrates that agent-based systems can address real patient-safety problems when architecture enforces boundaries: vision, tools, memory, policy, and localisation as separate agents with deterministic grounding. The cross-visit interaction check — today's prescription against every prior visit's generics — is only possible because Day 3 memory and Day 2 tools compose inside a governed Day 5 production pipeline. Built for the 2026 Kaggle 5-Day AI Agents Intensive with Google ADK, Gemini, and Vertex AI Agent Runtime.

**License:** MIT · **Author:** Alok Dwivedi · **Repository:** https://github.com/3amwave/medication-companion

---

## Media Gallery assets (attach in Kaggle editor)

| File | Use | Course day |
|------|-----|------------|
| `media/00_cover_image.png` | **Cover image** (required) | Demo |
| `media/06_agent_pipeline_flow.png` | **Agent 1→5 pipeline** (SequentialAgent flow) | Day 1 |
| `media/01_smoke_prescription.png` | Test prescription input | Demo |
| `media/05_result_screen_en.png` | English result + interactions | Day 3 |
| `media/04_cover_result_hi.png` | Hindi result + audio | Day 5 / accessibility |
| `media/eValCustomMetrics.jpg` | LLM-as-Judge eval (10/10 safety + clarity) | Day 4 |
| `media/architecture_diagram.md` | Full system diagram — export PNG via mermaid.live | Day 5 |
| YouTube video URL | Demo walkthrough (≤5 min) | All |

See `docs/kaggle_submission/media/README.md` for the full day-by-day image guide.
