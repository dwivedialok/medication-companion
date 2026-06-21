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

## Infrastructure & deployment

- **DONE** — Auth broker Cloud Run deploy in CI. Terraform owns the service
  skeleton ([`deployment/terraform/cicd/auth_broker.tf`](../deployment/terraform/cicd/auth_broker.tf));
  `staging.yaml` and `deploy-to-prod.yaml` push image revisions via
  [`deploy/auth_broker/deploy.sh`](../deploy/auth_broker/deploy.sh); Flutter is
  served from Firebase Hosting with rewrites to the broker. See
  [`docs/deployment_runbook.md`](deployment_runbook.md).

_(Add new infra items here as they arise.)_
