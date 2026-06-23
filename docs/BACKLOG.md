# Product backlog (post-capstone)

Items here are **not required for capstone submission** but should be addressed
before a public production launch. See also `AGENTS.md` → Known follow-ups.

---

## Security & tenancy

### Bind GCS upload URI to authenticated patient

**Priority:** High (production) · **Status:** Open

**Problem:** `/prescription` does not verify that `gcs_uri` was issued to the
current JWT holder. `/upload-url` creates paths like
`prescriptions/{uuid}.jpg` (no `patient_id`), while `/upload-direct` already
uses `prescriptions/{patient_id}/{uuid}.jpg`. A user with a valid Firebase
token could analyze another patient's image if they obtain the `gs://` path
(e.g. leaked `gcs_uri`, network intercept, or shared link).

**Impact:** Cross-tenant prescription image exposure at analysis time. Memory
stays partitioned by JWT `patient_id`, but the image content itself can leak.

**Not needed for:** capstone demo / dev smoketest with `DEV_PATIENT_ID`.

**Needed for:** public launch, multi-tenant production, any real PHI handling.

**Implementation options (pick one or combine):**

1. **Path-based binding (simplest):** Change `/upload-url` to use
   `prescriptions/{patient_id}/{uuid}.ext` (match `/upload-direct`). On
   `/prescription`, reject `gcs_uri` unless the path segment after
   `prescriptions/` equals `request.state.patient_id`.

2. **Server-side registry:** When issuing upload URL, store
   `{patient_id, gcs_uri, issued_at, expires_at}` (Redis, Firestore, or
   in-memory with TTL for single-instance). `/prescription` must find a matching
   record for the caller.

3. **Opaque analysis token:** Return a short-lived `upload_id` or signed
   analysis token with `/upload-url`; client sends that instead of raw
   `gcs_uri` on `/prescription`.

**Also consider:**

- GCS lifecycle rule to delete `prescriptions/` objects after N days
- Audit log correlating `/upload-url` issuance with `/prescription` calls
- Test in `tests/unit/test_auth_broker.py`: Patient B cannot analyze Patient A's URI

**Files:** `backend/auth_broker/gcs.py`, `backend/auth_broker/main.py`

---

## Async processing & ambient agents

### Pub/Sub-backed prescription analysis (decouple HTTP from pipeline)

**Priority:** Medium (post-capstone) · **Status:** Open

**Problem:** Today `/prescription` is **synchronous**: the auth broker holds the HTTP
connection while Agent Runtime runs the full 5-agent pipeline (~20–40s). That
limits scalability, complicates timeouts (Hosting 60s cap), and does not support
ambient/background processing or retries independent of the client.

**Goal:** Keep the auth broker as the **only client-facing HTTP API** (Firebase JWT,
GCS upload URLs). After upload, **enqueue** analysis work on Pub/Sub and return
immediately; a separate worker invokes the same Agent Runtime pipeline and
persists/notifies results.

**Not needed for:** capstone demo — current sync path via auth broker + Agent
Runtime is sufficient.

**Needed for:** production scale, resilient retries, ambient agents (Day 4
follow-up), long-running jobs without blocking Flutter/Hosting.

**Proposed architecture:**

```
Flutter → auth broker (HTTP)
            ├─ POST /upload-url  (unchanged)
            ├─ POST /prescription → publish {job_id, patient_id, gcs_uri, language}
            │                      return 202 {job_id}  (not PrescriptionResult)
            └─ GET  /jobs/{job_id} → status + result when ready

Pub/Sub topic (e.g. prescription-jobs)
    → subscriber worker (Cloud Run / Cloud Function)
        → Agent Runtime streamQuery (same pipeline as agent_client.py today)
        → write job status + PrescriptionResult to job store

Client polls GET /jobs/{id} or listens via Firestore / FCM (push out of scope for v1)
```

**Implementation sketch:**

1. **Terraform:** Pub/Sub topic + subscription, dead-letter topic, worker Cloud Run
   service account (`roles/pubsub.subscriber`, `roles/aiplatform.user`), optional
   Firestore collection for job state.
2. **Auth broker:** New endpoints or evolve `/prescription` — publish message after
   JWT + `gcs_uri` validation; sync path can remain behind a flag during migration.
3. **Worker:** New module (e.g. `backend/workers/prescription_worker.py`) — pull
   message, call existing `run_prescription_pipeline`, update job store.
4. **Flutter:** Upload flow unchanged; after enqueue, poll `GET /jobs/{id}` or show
   “processing” UI until `status=done`.
5. **Observability:** Log `job_id` across broker → Pub/Sub → worker → Runtime;
   Cloud Trace correlation.

**Acceptance criteria:**

- Broker returns within ~1s of `/prescription` with `{job_id}`; no Agent Runtime
  call on the request thread.
- Worker successfully processes queued jobs with at-least-once semantics and
  idempotent job updates.
- Patient receives same `PrescriptionResult` shape as sync path when job completes.
- Failed jobs surface `status=failed` with a safe patient-facing message.
- Pub/Sub path is **separate** from the HTTP auth broker Makefile/deploy target
  (see `AGENTS.md` — do not conflate with `make local-auth-broker`).

**Also consider:**

- Bind `gcs_uri` to `patient_id` before enqueue (depends on upload-uri binding story above)
- Message schema versioning and poison-message handling (DLQ + alert)
- Keep sync `/prescription` as fallback until Flutter migrates to poll model

**Files (expected):** new worker module, `backend/auth_broker/main.py`,
`backend/auth_broker/agent_client.py`, Terraform Pub/Sub resources, Flutter job
polling UI, specs scenario in `specs/`.

---

## Infrastructure & deployment

### Terraform: BigQuery `medication_companion.eval_log` dataset

**Priority:** Medium (prod hygiene) · **Status:** Open

**Problem:** Async LLM-as-Judge scores from production prescription runs write to
`{project}.medication_companion.eval_log` via `backend/evaluation/llm_judge.py`.
Terraform today provisions `{project_name}_telemetry` (GenAI log sinks) only —
not the eval audit dataset. New environments require a manual
[`scripts/setup_eval_bigquery.sh`](../scripts/setup_eval_bigquery.sh) step
(documented in [`docs/deployment_runbook.md`](deployment_runbook.md) §1).

**Goal:** Add `google_bigquery_dataset` + `google_bigquery_table.eval_log` to
`deployment/terraform/single-project/` and mirror in `cicd/` for
staging/prod project IDs. Grant app SA / Reasoning Engine SA
`bigquery.dataEditor` on the dataset. Remove manual script from the critical
path (keep script as idempotent fallback).

**Acceptance criteria:**

- `make infra-apply` creates dataset + table in dev; cicd module creates them
  in staging/prod.
- Deployed Agent Runtime writes judge rows without 404 after first prescription.
- Runbook §1 step 6 marked "optional if Terraform applied".

**Files (expected):** `deployment/terraform/single-project/eval.tf` (new),
`deployment/terraform/cicd/eval.tf`, IAM in `iam.tf`, runbook update.

---

- **DONE** — Auth broker Cloud Run deploy in CI. Terraform owns the service
  skeleton ([`deployment/terraform/cicd/auth_broker.tf`](../deployment/terraform/cicd/auth_broker.tf));
  `staging.yaml` and `deploy-to-prod.yaml` push image revisions via
  [`deploy/auth_broker/deploy.sh`](../deploy/auth_broker/deploy.sh); Flutter is
  served from Firebase Hosting with rewrites to the broker. See
  [`docs/deployment_runbook.md`](deployment_runbook.md).

_(Add new infra items here as they arise.)_

---

## Drug data quality

### Interaction gap detection → human review → `drugs.db` promotion

**Priority:** Medium (data quality + eval consistency) · **Status:** Open

**Problem:** `interaction_lookup` is dataset-backed only (`data/drugs.db` ←
`medicine_data.csv`). When the safety tool returns `severity=NONE` for a pair,
the pipeline correctly emits no finding — but LLM-as-Judge (and clinicians) may
still expect well-known interactions (e.g. aspirin + warfarin) that are absent
from the table. Today there is no workflow to capture those gaps, review them,
and promote approved rows into the index.

**Goal:** Close the loop between production/eval traffic and the curated
interaction dataset without letting the LLM invent patient-facing findings.
Suspected gaps are **queued for human review**; only approved rows enter
`drugs.db` on rebuild.

**Suggested approach (two phases):**

#### Phase 1 — Detect and queue (non-blocking)

1. **Gap detector** (new module, e.g. `backend/evaluation/interaction_gap_detector.py`):
   After `check_prescription_interactions` runs, compare each pair where
   `source=none` against an LLM pharmacology check (or a secondary reference
   API — RxNorm, openFDA — if we add one). Emit a candidate only when the
   external signal is **HIGH or MODERATE** and confidence is above a threshold.
2. **Review queue** (Firestore collection or BigQuery table, e.g.
   `interaction_review_queue`): `{generic_a, generic_b, proposed_severity,
   mechanism, evidence, session_id, patient_id_hash, status=pending|approved|rejected,
   reviewer, reviewed_at}`.
   - Never write candidates directly to patient-facing output or `interactions`
     table.
   - Dedupe on canonical pair key; bump `occurrence_count` on repeats.
3. **Observability:** Log + optional nightly digest of pending candidates ranked
   by frequency and severity.

**Phase 1 acceptance criteria:**

- Pipeline behaviour unchanged for patients (tool output remains authoritative).
- Eval/smoke runs that hit known-missing pairs produce queue rows without
  failing the request path.
- Duplicate pair submissions collapse to one pending row.

#### Phase 2 — Review UI / CLI and index promotion

1. **Reviewer workflow:** Small internal tool (CLI script first, optional admin
   UI later) to list pending rows, approve/reject with reason, and export
   approved rows to `data/interaction_candidates.csv` (or append to
   `medicine_data.csv` with `source=human_reviewed`).
2. **Promotion pipeline:** Approved CSV rows flow through
   `scripts/build_drug_index.py` into `interactions` on the next rebuild;
   `data/drugs.db` is committed after review.
3. **Guardrails:** Require two fields on approve — `mechanism` (plain language)
   and `reference` (citation URL or dataset row). Rejected pairs get a
   `rejected_pairs` denylist so the detector does not re-queue them.

**Phase 2 acceptance criteria:**

- Approving aspirin + warfarin in the queue and rebuilding the index causes
  `interaction_lookup` to return `source=dataset` for that pair.
- Rejected pairs do not reappear in the queue for 90 days (configurable).
- Unit test: approved candidate → rebuild → lookup returns expected severity.

**Also consider (optional enhancements):**

- **Eval rubric alignment:** `tests/eval/eval_config.yaml` already instructs the
  judge to score against tool output only; keep that as the smoke gate and use
  the queue to grow coverage over time (do not re-introduce pharmacology
  penalties into the rubric).
- **Phase 0 (quick win):** Hand-add high-confidence pairs from eval failures
  (e.g. aspirin + warfarin) to the CSV and rebuild — unblocks smoke ≥8 without
  waiting for Phase 1.
- **Severity cap:** Detector may only propose `HIGH`/`MODERATE`; `LOW`/`INFO`
  stays human-only to limit queue noise.

**Files (expected):** `backend/evaluation/interaction_gap_detector.py`,
`backend/tools/interaction_lookup.py`, `scripts/build_drug_index.py`,
`data/interaction_candidates.csv` (new), Terraform for queue store, specs
scenario for “gap queued, not surfaced to patient”.

---

## Security & tenancy (continued)

### Audio explanation access — shorten TTL and bind to patient session

**Priority:** Medium (production hygiene) · **Status:** Open

**Problem:** TTS uploads MP3s to the shared uploads bucket
(`audio/{language}/{random}.mp3`) and returns a **V4 signed GET URL with 24h
expiry** (`backend/tools/tts.py`). The bucket is **private** (uniform bucket-level
access; no `allUsers` objectViewer on uploads), so objects are not publicly
listable — but **anyone who holds the signed URL can download the audio until it
expires**. The URL is returned inline in `PrescriptionResult.audio_url` to the
authenticated client; there is no `patient_id` in the object path and no
broker endpoint to re-issue a URL on demand.

**Current state (acceptable for capstone, tighten for launch):**

| Control | Status |
|---------|--------|
| Bucket public read | **No** — IAM restricted to app / Reasoning Engine SAs |
| Access model | Signed URL (capability URL) |
| TTL | **24 hours** (longer than ideal for PHI-adjacent content) |
| Path tenancy | **Not bound** — random blob name only |
| Re-sign on play | **Not implemented** — client uses URL from `/prescription` response |

**Goal:** Standard safe engineering for audio artifacts:

1. **Short TTL** — reduce signed URL lifetime to **~10 minutes** (configurable
   via `AUDIO_SIGNED_URL_TTL_SECONDS`).
2. **Session-bound re-sign** — auth broker endpoint
   `GET /sessions/{session_id}/audio-url` (Firebase JWT required) that verifies
   the session belongs to `patient_id`, then issues a fresh signed GET URL for
   the stored `gs://` path (broker stores or derives blob path from session
   metadata — not the long-lived URL).
3. **Path convention** — prefer `audio/{patient_id}/{session_id}.mp3` (or hash)
   for audit and lifecycle rules; align with upload-uri patient binding backlog
   item.
4. **Lifecycle** — GCS rule to delete `audio/` objects after N days (e.g. 7–30).
5. **Flutter** — on play or 403/expired URL, call re-sign endpoint instead of
   caching the URL for the session lifetime.

**Acceptance criteria:**

- Direct bucket URL without signature returns 403.
- Expired signed URL returns 403; re-sign endpoint returns new URL for owner only.
- Patient B cannot obtain Patient A's audio URL via re-sign API.
- TTL defaults to 10m in production; local stub unchanged.

**Files (expected):** `backend/tools/tts.py`, `backend/auth_broker/main.py`,
`backend/auth_broker/gcs.py`, `frontend/lib/services/api_service.dart`,
`frontend/lib/screens/result_screen.dart`, Terraform lifecycle on uploads bucket.
