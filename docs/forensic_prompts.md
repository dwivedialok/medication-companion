# Forensic Specialist Mode — prompt templates

Copy-paste templates for evidence-driven debugging (Day 5). Feed raw artifacts as the
**primary input** — not vague symptom descriptions.

Referenced from [AGENTS.md](../AGENTS.md) "Adding a new feature" workflow.

---

## Template 1: Pipeline 500 / broker failure

Use when: auth broker or Agent Runtime returns 5xx, or `test_prescription.py` fails mid-pipeline.

```
You are debugging a Medication Companion pipeline failure. Use ONLY the evidence below.

## Environment
- ENVIRONMENT: <local|production>
- USE_LOCAL_RUNNER: <true|false>
- AGENT_RUNTIME_RESOURCE: <resource name or "local runner">

## Raw error
<paste full stack trace or HTTP response body>

## Request context
- Endpoint: <e.g. POST /prescription>
- gcs_uri: <gs://...> (no image bytes)
- target_language: <code>
- patient_id: <dev id or "Firebase UID redacted">

## Recent log lines (if any)
<paste google.cloud.logging or uvicorn output>

## Task
1. Identify which agent or service failed (broker vs A1–A5 vs TTS/GCS).
2. State the root cause with a code reference (file:line or module).
3. Propose the minimal fix — no refactors.
4. List one pytest command to verify the fix.

Constraints: patient_id from JWT only; never store images in memory; severity enum is fixed.
```

---

## Template 2: Judge score regression

Use when: LLM-as-Judge scores drop on eval run or a single dimension fails threshold.

```
You are debugging an LLM-as-Judge regression in Medication Companion.

## Eval row (JSON)
<paste failed row from eval dataset or BigQuery eval_log>

## Scores
- safety_score: <>
- clarity_score: <>
- intent_satisfaction_score: <> (if present)
- translation_accuracy_score: <> (if present)
- Expected threshold: <from eval_config.yaml>

## Agent outputs captured in eval
- Agent 4 summary: <paste>
- Agent 5 translated_text: <paste>
- overall_severity: <>

## Trajectory (if available)
<paste Cloud Trace span names or agent sequence>

## Task
1. Which dimension failed and why (cite rubric criterion).
2. Is this an agent instruction issue, tool data issue, or judge prompt issue?
3. Minimal change: agent instruction vs eval rubric vs test fixture.
4. pytest or eval command to re-verify.

Do not loosen safety rubric to pass eval — fix the agent or fixture.
```

---

## Template 3: Policy Server false positive

Use when: legitimate prescription output was replaced by the safe fallback (Step 3+).

```
You are debugging a Policy Server false positive in Medication Companion.

## Policy decision (JSON)
{
  "decision": "deny",
  "stage": "<image_intake|agent_output>",
  "violation_class": "<class>",
  "evidence": "<paste>"
}

## Blocked agent output (full text)
<paste Agent 4 or 5 output before sanitisation>

## Safety context
- image_classification: <>
- overall_severity: <>
- resolved_drugs: <list>

## Rubric excerpt
<paste relevant entry from backend/policy/rubric.yaml>

## Task
1. Explain why the semantic/structural gate flagged this (quote triggering phrase).
2. True positive or false positive? If false, which rubric clause is too broad?
3. Propose rubric or judge prompt tweak + regression test case in test_policy_server.py.
4. Confirm patient-facing fallback text still meets AGENTS.md disclaimer rule.

Never disable the policy gate — narrow the rubric or fix agent wording.
```

---

## Usage notes

- Attach specs: link relevant scenario from `specs/pipeline.feature` or `specs/safety_refusal.feature`
- For local repro: `make auth-broker` + `uv run python scripts/test_prescription.py <image>`
- For deployed repro: include engine id and commit SHA from Cloud Run / Agent Runtime env
