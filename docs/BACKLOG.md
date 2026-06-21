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

- **DONE** — Auth broker Cloud Run deploy in CI. Terraform owns the service
  skeleton ([`deployment/terraform/cicd/auth_broker.tf`](../deployment/terraform/cicd/auth_broker.tf));
  `staging.yaml` and `deploy-to-prod.yaml` push image revisions via
  [`deploy/auth_broker/deploy.sh`](../deploy/auth_broker/deploy.sh); Flutter is
  served from Firebase Hosting with rewrites to the broker. See
  [`docs/deployment_runbook.md`](deployment_runbook.md).

_(Add new infra items here as they arise.)_
