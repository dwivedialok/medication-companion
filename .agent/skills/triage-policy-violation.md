# Skill: Triage a policy server violation

Runbook for diagnosing Policy Server deny events. Requires Step 3 implementation
(`backend/policy/policy_server.py`).

## When to use

- Patient sees generic fallback: "Please discuss this prescription with your doctor or pharmacist."
- Eval or red-team case fails with unexpected `deny`
- Cloud Trace span shows `policy_decision=deny`

## Evidence to collect

1. **Violation record** — `violation_class`, `stage` (image_intake | agent_output | qa_input), `evidence` snippet
2. **Agent trace** — which agent produced the blocked text (usually Agent 4 or 5)
3. **Session metadata** — hashed `patient_id`, `image_classification` if intake gate
4. **Timestamp + request id** — from auth broker logs or Cloud Trace

## Triage by violation_class

| Class | Likely cause | First check |
|-------|--------------|-------------|
| `non_prescription_image` | Wrong image uploaded | Agent 1 `image_classification` |
| `overlay_injection` | Adversarial text on image | Agent 1 classification + image review |
| `diagnostic_claim` | Agent 4/5 diagnostic phrasing | Semantic gate evidence string |
| `dosing_change` | Dose advice in output | Agent 4 summary or questions_for_doctor |
| `otc_alternative` | Swap/substitute suggestion | Agent 4 interaction_cards |
| `severity_downgrade` | HIGH framed as LOW/INFO | Agent 4 tone vs SafetyOutput |
| `cross_patient_leak` | Name from image metadata in output | Compare OCR fields to output text |

## Decision tree

```
deny at image_intake?
  yes → expected for adversarial eval cases; retest with valid prescription
  no  → deny at agent_output?
          yes → pull Agent 4/5 draft from trace; fix instruction or confirm true positive
          no  → qa_input gate (FEATURE_QA_ENABLED only)
```

## False positive remediation

1. Confirm rubric in [backend/policy/rubric.yaml](../../backend/policy/rubric.yaml) (Step 3)
2. Adjust semantic judge prompt — never disable the gate entirely
3. Add a regression test to `tests/unit/test_policy_server.py`
4. Re-run red-team subset: `uv run pytest tests/unit/test_policy_server.py -k deny`

## True positive (expected deny)

- Log for capstone demo / writeup screenshot
- Do not whitelist the violating phrase — fix upstream agent instruction instead

## Observability locations (after Step 4)

- Cloud Trace: span attribute `policy_decision`, `violation_class`
- BigQuery Agent Analytics: prompt-response log for semantic gate model
- BigQuery `eval_log`: judge scores if async eval fired

## Escalation

If deny rate spikes in production (>5% of prescriptions):

1. Sample 10 traces with `policy_decision=deny`
2. Classify false vs true positive ratio
3. If >50% false positives on one class, open issue with rubric + sample evidence
4. See [docs/forensic_prompts.md](../../docs/forensic_prompts.md) template "Policy Server false positive"
